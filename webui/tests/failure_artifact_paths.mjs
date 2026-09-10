import {
  closeSync,
  constants as fsConstants,
  fstatSync,
  fchmodSync,
  openSync,
  readdirSync,
  rmdirSync,
  unlinkSync,
  writeSync,
} from "node:fs";
import { spawnSync } from "node:child_process";
import {
  basename,
  dirname,
  isAbsolute,
  relative,
  resolve,
  sep,
} from "node:path";
import { fileURLToPath } from "node:url";
import {
  rewriteValidatedDescriptorSync,
  sanitizeArtifactDescriptorSync,
} from "./failure_artifacts.mjs";

const DESCRIPTOR_DIRECTORY = process.platform === "darwin"
  ? "/dev/fd"
  : process.platform === "linux"
    ? "/proc/self/fd"
    : undefined;
const MAC_HELPER = fileURLToPath(new URL(
  "./failure_artifact_helper.py",
  import.meta.url,
));
const MAC_SANITIZER = fileURLToPath(new URL(
  "./failure_artifact_fd_sanitizer.mjs",
  import.meta.url,
));
const DIRECTORY_FLAGS =
  fsConstants.O_RDONLY |
  fsConstants.O_DIRECTORY |
  fsConstants.O_NOFOLLOW;
const FILE_FLAGS = fsConstants.O_RDWR | fsConstants.O_NOFOLLOW;
const MAX_OUTPUT_COMPONENTS = 128;
const MAX_TREE_DEPTH = 32;
const MAX_TREE_ENTRIES = 1024;

export class ArtifactPathError extends Error {
  constructor(message, options = {}) {
    super(message, options);
    this.cleanupFailed = options.cleanupFailed === true;
  }
}

export function openOutputRootSync(rootPath) {
  if (!DESCRIPTOR_DIRECTORY && process.platform !== "darwin") {
    throw new ArtifactPathError("descriptor-relative paths are unsupported");
  }
  const path = resolve(rootPath);
  const expected = prepareOutputRootSync(path);
  const descriptor = openSync(path, DIRECTORY_FLAGS);
  try {
    const exactStat = fstatSync(descriptor, { bigint: true });
    if (
      !exactStat.isDirectory() ||
      exactStat.dev.toString() !== expected.device ||
      exactStat.ino.toString() !== expected.inode
    ) {
      throw new ArtifactPathError("output root changed during acquisition");
    }
    const stat = fstatSync(descriptor);
    if (!stat.isDirectory()) {
      throw new ArtifactPathError("output root is not a directory");
    }
    return {
      path,
      descriptor,
      device: stat.dev,
      inode: stat.ino,
    };
  } catch (error) {
    closeSync(descriptor);
    throw error;
  }
}

export function sanitizeDirectoryContentsSync(root, sensitiveValues = []) {
  if (process.platform === "darwin") {
    return runMacHelperSync(
      root,
      "sanitize-tree",
      [],
      undefined,
      "redact",
      sensitiveValues,
    ).status === 0;
  }
  return sanitizeDirectoryDescriptorSync(
    root.descriptor,
    sensitiveValues,
    { entries: 0 },
    0,
  );
}

export function openArtifactAtRootSync(root, artifactPath) {
  const components = relativeComponents(root.path, artifactPath);
  if (!components.length) {
    throw new ArtifactPathError("artifact path is the output root");
  }
  if (process.platform === "darwin") {
    throw new ArtifactPathError(
      "macOS artifact descriptors must remain in the helper boundary",
    );
  }

  let parentDescriptor = root.descriptor;
  const ownedParentDescriptors = [];
  const finalName = components[components.length - 1];
  try {
    for (const component of components.slice(0, -1)) {
      const nextDescriptor = openSync(
        descriptorChildPath(parentDescriptor, component),
        DIRECTORY_FLAGS,
      );
      ownedParentDescriptors.push(nextDescriptor);
      parentDescriptor = nextDescriptor;
    }

    let descriptor;
    try {
      descriptor = openSync(
        descriptorChildPath(parentDescriptor, finalName),
        FILE_FLAGS,
      );
      if (!fstatSync(descriptor).isFile()) {
        closeSync(descriptor);
        descriptor = undefined;
        throw new Error("artifact is not a regular file");
      }
    } catch (error) {
      if (descriptor !== undefined) {
        try {
          closeSync(descriptor);
        } catch {
          // The descriptor may already be closed after a failed fstat.
        }
        descriptor = undefined;
      }
      let cleanupFailed = false;
      try {
        unlinkSync(descriptorChildPath(parentDescriptor, finalName));
      } catch (cleanupError) {
        cleanupFailed = true;
        error.cause = cleanupError;
      }
      throw new ArtifactPathError(error.message, {
        cause: error,
        cleanupFailed,
      });
    }

    return {
      descriptor,
      close: () => {
        closeSync(descriptor);
        closeDescriptors(ownedParentDescriptors);
      },
    };
  } catch (error) {
    closeDescriptors(ownedParentDescriptors);
    throw error;
  }
}

export function createArtifactAtRootSync(root, name, mode = 0o600) {
  if (
    typeof name !== "string" ||
    !name.length ||
    name.includes("/") ||
    name.includes("\\") ||
    name === "." ||
    name === ".."
  ) {
    throw new ArtifactPathError("invalid generated artifact name");
  }
  if (process.platform === "darwin") {
    throw new ArtifactPathError(
      "macOS artifact descriptors must remain in the helper boundary",
    );
  }
  let descriptor;
  try {
    descriptor = openSync(
      descriptorChildPath(root.descriptor, name),
      FILE_FLAGS | fsConstants.O_CREAT | fsConstants.O_EXCL,
      mode,
    );
    if (!fstatSync(descriptor).isFile()) {
      closeSync(descriptor);
      descriptor = undefined;
      throw new Error("generated artifact is not a regular file");
    }
    return descriptor;
  } catch (error) {
    if (descriptor !== undefined) closeSync(descriptor);
    throw error;
  }
}

export function writeArtifactAtRootSync(root, name, contents) {
  validateSingleComponent(name, "invalid generated artifact name");
  if (process.platform !== "darwin") {
    const descriptor = createArtifactAtRootSync(root, name);
    try {
      let offset = 0;
      const data = Buffer.from(contents);
      while (offset < data.length) {
        const written = writeSync(
          descriptor,
          data,
          offset,
          data.length - offset,
          offset,
        );
        if (written <= 0) throw new Error("artifact write made no progress");
        offset += written;
      }
    } finally {
      closeSync(descriptor);
    }
    return;
  }
  const result = runMacHelperSync(
    root,
    "create",
    [name],
    Buffer.from(contents),
  );
  if (result.status !== 0) {
    throw new ArtifactPathError("generated artifact could not be created", {
      cleanupFailed: result.status === undefined || result.status === 11,
      cause: result.error,
    });
  }
}

export function processArtifactAtRootSync(
  root,
  artifactPath,
  kind,
  sensitiveValues = [],
) {
  const components = relativeComponents(root.path, artifactPath);
  if (process.platform !== "darwin") {
    throw new ArtifactPathError("descriptor helper is only required on macOS");
  }
  const result = runMacHelperSync(
    root,
    "sanitize",
    components,
    undefined,
    kind,
    sensitiveValues,
  );
  if (result.status === 0) return { retained: true };
  if (result.status === 10) return { retained: false };
  throw new ArtifactPathError("artifact could not be sanitized safely", {
    cleanupFailed: true,
    cause: result.error,
  });
}

export function descriptorChildPath(descriptor, name) {
  if (!DESCRIPTOR_DIRECTORY || process.platform === "darwin") {
    throw new ArtifactPathError("descriptor-relative paths are unsupported");
  }
  return `${DESCRIPTOR_DIRECTORY}/${descriptor}/${name}`;
}

export function removeArtifactAtRootSync(root, name) {
  if (process.platform === "darwin") {
    validateSingleComponent(name, "invalid artifact name");
    const result = runMacHelperSync(root, "unlink", [name]);
    if (result.status !== 0) {
      throw new ArtifactPathError("artifact could not be removed", {
        cleanupFailed: true,
        cause: result.error,
      });
    }
    return;
  }
  unlinkSync(descriptorChildPath(root.descriptor, name));
}

export function removeDirectoryContentsSync(root) {
  if (process.platform === "darwin") {
    return runMacHelperSync(root, "cleanup").status === 0;
  }
  const rootDescriptor = typeof root === "number" ? root : root.descriptor;
  let complete = true;
  try {
    // The root descriptor is owned by the reporter; make the cleanup boundary
    // writable without consulting its pathname again.
    fchmodSync(rootDescriptor, 0o700);
  } catch {
    complete = false;
  }

  let names;
  try {
    names = readdirSync(`${DESCRIPTOR_DIRECTORY}/${rootDescriptor}`);
  } catch {
    return false;
  }
  for (const name of names) {
    if (!removeEntrySync(rootDescriptor, name)) complete = false;
  }
  return complete;
}

function removeEntrySync(parentDescriptor, name) {
  const path = descriptorChildPath(parentDescriptor, name);
  let childDescriptor;
  try {
    childDescriptor = openSync(path, DIRECTORY_FLAGS);
  } catch {
    try {
      unlinkSync(path);
      return true;
    } catch {
      return false;
    }
  }

  let complete = removeDirectoryContentsSync(childDescriptor);
  closeSync(childDescriptor);
  try {
    rmdirSync(path);
  } catch {
    try {
      unlinkSync(path);
    } catch {
      complete = false;
    }
  }
  return complete;
}

function relativeComponents(rootPath, artifactPath) {
  if (typeof artifactPath !== "string" || !artifactPath.length) {
    throw new ArtifactPathError("artifact path is missing");
  }
  const candidate = resolve(artifactPath);
  const fromRoot = relative(rootPath, candidate);
  if (
    !fromRoot ||
    isAbsolute(fromRoot) ||
    fromRoot === ".." ||
    fromRoot.startsWith(`..${sep}`)
  ) {
    throw new ArtifactPathError("artifact path is outside its output root");
  }
  const components = fromRoot.split(sep);
  if (components.some((component) => !component || component === "." || component === "..")) {
    throw new ArtifactPathError("artifact path contains unsafe components");
  }
  return components;
}

function validateSingleComponent(name, message) {
  if (
    typeof name !== "string" ||
    !name.length ||
    name.includes("/") ||
    name.includes("\\") ||
    name === "." ||
    name === ".."
  ) {
    throw new ArtifactPathError(message);
  }
}

function prepareOutputRootSync(rootPath) {
  const components = [];
  let ancestor = rootPath;
  let rootDescriptor;
  try {
    while (rootDescriptor === undefined) {
      try {
        rootDescriptor = openSync(ancestor, DIRECTORY_FLAGS);
      } catch {
        const parent = dirname(ancestor);
        if (parent === ancestor) {
          throw new ArtifactPathError("output root could not be prepared");
        }
        components.unshift(basename(ancestor));
        ancestor = parent;
      }
    }
    if (!components.length) {
      const stat = fstatSync(rootDescriptor, { bigint: true });
      return {
        device: stat.dev.toString(),
        inode: stat.ino.toString(),
      };
    }
    if (components.length > MAX_OUTPUT_COMPONENTS) {
      throw new ArtifactPathError("output root has too many components");
    }
    const result = spawnSync(
      process.env.SIMULATOR_PYTHON || process.env.PYTHON || "python3",
      [
        MAC_HELPER,
        "--operation",
        "prepare-root",
        "--components",
        JSON.stringify(components),
      ],
      {
        encoding: "utf8",
        stdio: ["ignore", "pipe", "ignore", rootDescriptor],
      },
    );
    if (result.status !== 0) {
      throw new ArtifactPathError("output root could not be prepared");
    }
    const metadata = JSON.parse(result.stdout);
    if (
      typeof metadata?.device !== "string" ||
      typeof metadata?.inode !== "string"
    ) {
      throw new ArtifactPathError("output root identity is invalid");
    }
    return metadata;
  } catch (error) {
    if (error instanceof ArtifactPathError) throw error;
    throw new ArtifactPathError("output root could not be prepared", {
      cause: error,
    });
  } finally {
    if (rootDescriptor !== undefined) closeSync(rootDescriptor);
  }
}

function sanitizeDirectoryDescriptorSync(
  descriptor,
  sensitiveValues,
  state,
  depth,
) {
  if (depth > MAX_TREE_DEPTH) return false;
  let names;
  try {
    names = readdirSync(`${DESCRIPTOR_DIRECTORY}/${descriptor}`);
  } catch {
    return false;
  }
  let complete = true;
  for (const name of names) {
    state.entries += 1;
    if (state.entries > MAX_TREE_ENTRIES) return false;
    if (!sanitizeDirectoryEntrySync(
      descriptor,
      name,
      sensitiveValues,
      state,
      depth,
    )) {
      complete = false;
    }
  }
  return complete;
}

function sanitizeDirectoryEntrySync(
  parentDescriptor,
  name,
  sensitiveValues,
  state,
  depth,
) {
  const path = descriptorChildPath(parentDescriptor, name);
  let directoryDescriptor;
  try {
    directoryDescriptor = openSync(path, DIRECTORY_FLAGS);
  } catch {
    return sanitizeFileEntrySync(parentDescriptor, name, sensitiveValues);
  }
  try {
    return sanitizeDirectoryDescriptorSync(
      directoryDescriptor,
      sensitiveValues,
      state,
      depth + 1,
    );
  } finally {
    closeSync(directoryDescriptor);
  }
}

function sanitizeFileEntrySync(parentDescriptor, name, sensitiveValues) {
  const path = descriptorChildPath(parentDescriptor, name);
  let descriptor;
  try {
    descriptor = openSync(path, FILE_FLAGS);
    if (!fstatSync(descriptor).isFile()) {
      throw new ArtifactPathError("artifact is not a regular file");
    }
  } catch {
    if (descriptor !== undefined) closeSync(descriptor);
    try {
      unlinkSync(path);
      return true;
    } catch {
      return false;
    }
  }

  try {
    const lowerName = name.toLowerCase();
    const kind = lowerName.endsWith(".zip")
      ? "trace"
      : lowerName.endsWith(".png")
        ? "screenshot"
        : "redact";
    try {
      sanitizeArtifactDescriptorSync(descriptor, kind, sensitiveValues);
    } catch {
      rewriteValidatedDescriptorSync(descriptor, Buffer.from("[REDACTED]\n"));
    }
    return true;
  } catch {
    return false;
  } finally {
    closeSync(descriptor);
  }
}

function runMacHelperSync(
  root,
  operation,
  components = [],
  input,
  kind = "redact",
  sensitiveValues = [],
) {
  const stdio = [
    input === undefined ? "ignore" : "pipe",
    "ignore",
    "ignore",
    root.descriptor,
  ];
  const result = spawnSync(
    process.env.SIMULATOR_PYTHON || process.env.PYTHON || "python3",
    [
      MAC_HELPER,
      "--operation",
      operation,
      "--components",
      JSON.stringify(components),
      "--node",
      process.execPath,
      "--sanitizer",
      MAC_SANITIZER,
    ],
    {
      env: {
        ...process.env,
        FAILURE_ARTIFACT_KIND: kind,
        FAILURE_ARTIFACT_SENSITIVE_VALUES: JSON.stringify(sensitiveValues),
      },
      input,
      stdio,
    },
  );
  return {
    status: result.status,
    error: result.error,
  };
}

function closeDescriptors(descriptors) {
  for (const descriptor of descriptors.reverse()) {
    try {
      closeSync(descriptor);
    } catch {
      // The descriptor is already closed.
    }
  }
}
