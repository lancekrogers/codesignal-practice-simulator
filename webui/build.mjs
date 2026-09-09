import { createHash } from "node:crypto";
import {
  open as openFile,
  mkdir,
  mkdtemp,
  lstat,
  readFile,
  realpath,
  readdir,
  rename,
  rm,
} from "node:fs/promises";
import { existsSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import {
  join,
  basename,
  dirname,
  relative,
  resolve,
  sep,
} from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL(".", import.meta.url));
const RECOVER_ONLY = process.argv.includes("--recover-only");
const PUBLICATION_WAIT_SECONDS = 10;
const PUBLICATION_POLL_MILLISECONDS = 20;
const STALE_LOCK_SECONDS = 30;
const RECLAIMER_STALE_SECONDS = 30;
const REQUIRED_STABLE_ASSETS = new Set([
  "ASSET_PROVENANCE.txt",
  "NOTICE.txt",
  "app.js",
  "favicon.svg",
  "index.html",
  "manifest.json",
  "styles.css",
]);
const HASHED_ASSET_PATTERNS = [
  /^app-[A-Za-z0-9_-]+\.js$/u,
  /^app-[A-Za-z0-9_-]+\.css$/u,
  /^styles-[A-Za-z0-9_-]+\.css$/u,
  /^editor\.worker-[A-Za-z0-9_-]+\.js$/u,
  /^language\.worker-[A-Za-z0-9_-]+\.js$/u,
  /^[A-Za-z0-9_-]+-[A-Za-z0-9_-]+\.ttf$/u,
];
const SAFE_ASSET_NAME = /^[A-Za-z0-9._-]+$/u;
const REQUIRED_RUNTIME_NOTICE_MAPPING = {
  entry_points: ["monaco-editor"],
  packages: {
    dompurify: [
      { source: "LICENSE", snapshot: "dompurify.Apache-2.0.txt" },
      { source: "LICENSE-MPL", snapshot: "dompurify.MPL-2.0.txt" },
    ],
    marked: [{ source: "LICENSE.md", snapshot: "marked.MIT.txt" }],
    "monaco-editor": [
      { source: "LICENSE", snapshot: "monaco-editor.MIT.txt" },
      {
        source: "ThirdPartyNotices.txt",
        snapshot: "monaco-editor.ThirdPartyNotices.txt",
      },
    ],
  },
};
const packageJson = JSON.parse(
  readFileSync(join(root, "package.json"), "utf8"),
);
const packageLock = JSON.parse(
  readFileSync(join(root, "package-lock.json"), "utf8"),
);
const runtimeNoticeSpec = JSON.parse(
  readFileSync(join(root, "LICENSES", "runtime-notices.json"), "utf8"),
);
const staticRoot = process.env.ASSET_OUTPUT_DIR
  ? resolve(process.env.ASSET_OUTPUT_DIR)
  : join(
      root,
      "..",
      "src",
      "codesignal_practice_simulator",
      "web",
      "static",
    );

if (RECOVER_ONLY) {
  await recoverOnly();
} else {
  const output = await bundle();
  const files = collectFiles(output.outputFiles);
  const app = requiredFile(files, "app-", ".js");
  const styles = requiredFile(files, "styles-", ".css");
  requiredFile(files, "editor.worker-", ".js");
  requiredFile(files, "language.worker-", ".js");
  const cssNames = [...files.keys()]
    .filter((name) => name.endsWith(".css"))
    .sort();
  const favicon = Buffer.from(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">' +
      '<rect width="32" height="32" rx="6" fill="#17202b"/>' +
      '<path d="M8 8h16v4H12v4h9v4h-9v4H8z" fill="#9cc7ff"/>' +
      "</svg>\n",
  );
  const index = Buffer.from(indexHtml(app.name, cssNames));
  const notices = runtimeNotices();
  const notice = Buffer.from(notices.text);
  const provenance = Buffer.from(
    provenanceText(files, [
      ["index.html", index],
      ["NOTICE.txt", notice],
      ["favicon.svg", favicon],
    ], notices),
  );

  const entries = new Map([
    ...[...files.values()].map((file) => [file.name, file.contents]),
    ["index.html", index],
    ["NOTICE.txt", notice],
    ["ASSET_PROVENANCE.txt", provenance],
    ["favicon.svg", favicon],
    ["app.js", app.contents],
    ["styles.css", styles.contents],
  ]);
  const manifest = createManifest(entries);
  entries.set("manifest.json", Buffer.from(`${JSON.stringify(manifest, null, 2)}\n`));
  await publish(entries, manifest);
}

async function recoverOnly() {
  const paths = await publicationPaths();
  const lock = await acquirePublicationLock(paths.lock);
  try {
    await recoverPublication(paths);
  } finally {
    await lock.release();
  }
}

function bundle() {
  return import("esbuild").then(({ build }) => build({
    absWorkingDir: root,
    bundle: true,
    entryPoints: {
      app: "src/app.ts",
      "editor.worker": "src/editor.worker.ts",
      "language.worker": "src/language.worker.ts",
      styles: "src/styles.css",
    },
    entryNames: "[name]-[hash]",
    outdir: join(root, ".tmp", "bundle"),
    write: false,
    format: "esm",
    platform: "browser",
    target: "es2022",
    minify: true,
    legalComments: "none",
    sourcemap: false,
    charset: "utf8",
    loader: { ".ts": "ts", ".css": "css", ".ttf": "file" },
    assetNames: "[name]-[hash]",
  }));
}

function runtimeNotices() {
  assertRuntimeNoticeSpec();
  const packages = runtimePackageClosure();
  const sections = [];
  const records = [];
  for (const name of packages) {
    const packageRecord = packageLock.packages?.[`node_modules/${name}`];
    const packageRoot = join(root, "node_modules", ...name.split("/"));
    const packageNotices = runtimeNoticeSpec.packages?.[name];
    if (!packageNotices) {
      throw new Error(`bundled runtime package has no notice mapping: ${name}`);
    }
    for (const noticeRecord of packageNotices) {
      const installedPath = join(packageRoot, noticeRecord.source);
      const snapshotPath = join(root, "LICENSES", noticeRecord.snapshot);
      const installed = readFileSync(installedPath);
      const snapshot = readFileSync(snapshotPath);
      if (!installed.equals(snapshot)) {
        throw new Error(
          `notice snapshot does not exactly match ${name}/${noticeRecord.source}`,
        );
      }
      records.push({
        package: name,
        version: packageRecord.version,
        integrity: packageRecord.integrity,
        source: noticeRecord.source,
        snapshot: noticeRecord.snapshot,
        sha256: digest(snapshot),
      });
      sections.push(
        `===== ${name}@${packageRecord.version} :: ${noticeRecord.source} =====\n` +
          snapshot.toString("utf8").replace(/\s+$/u, "") +
          "\n",
      );
    }
  }
  return {
    records,
    text:
      "Codesignal practice simulator bundled runtime third-party notices\n" +
      "The sections below are exact notice/license text from the locked npm packages.\n" +
      "Build and test tooling notices are not part of this runtime boundary.\n\n" +
      sections.join("\n"),
  };
}

function runtimePackageClosure() {
  assertRuntimeNoticeSpec();
  const entryPoints = runtimeNoticeSpec.entry_points;
  if (!Array.isArray(entryPoints) || entryPoints.length === 0) {
    throw new Error("runtime notice entry points are missing");
  }
  const discovered = new Set();
  const visit = (name) => {
    if (discovered.has(name)) return;
    const record = packageLock.packages?.[`node_modules/${name}`];
    if (!record) {
      throw new Error(`runtime package is missing from package-lock.json: ${name}`);
    }
    discovered.add(name);
    for (const dependency of Object.keys(record.dependencies || {}).sort()) {
      visit(dependency);
    }
  };
  for (const name of entryPoints) visit(name);
  return [...discovered].sort();
}

function assertRuntimeNoticeSpec() {
  if (
    JSON.stringify(runtimeNoticeSpec) !==
    JSON.stringify(REQUIRED_RUNTIME_NOTICE_MAPPING)
  ) {
    throw new Error("runtime-notices.json does not match the locked runtime mapping");
  }
}

function collectFiles(outputFiles) {
  return new Map(
    outputFiles.map((file) => {
      const name = basename(file.path);
      const contents = Buffer.from(file.contents);
      return [name, { name, contents: normalizeGeneratedText(name, contents) }];
    }),
  );
}

function normalizeGeneratedText(name, contents) {
  if (!name.endsWith(".js")) return contents;
  return Buffer.from(contents.toString("utf8").replace(/[ \t]+$/gm, ""));
}

function requiredFile(files, prefix, extension) {
  const match = [...files.values()].find(
    (file) => file.name.startsWith(prefix) && file.name.endsWith(extension),
  );
  if (!match) throw new Error(`esbuild did not emit ${prefix}*${extension}`);
  return match;
}

function indexHtml(appName, stylesNames) {
  const styles = stylesNames
    .map((name) => `    <link rel="stylesheet" href="/${name}">`)
    .join("\n");
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Practice Simulator</title>
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">
${styles}
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/${appName}"></script>
  </body>
</html>
`;
}

function provenanceText(files, generated, notices) {
  const lines = [
    "Codesignal practice simulator browser assets",
    "Generated by webui/build.mjs.",
    "Runtime dependencies are bundled same-origin assets; Node is not needed at runtime.",
    "Direct editor input: monaco-editor 0.56.0.",
    "Build tool: esbuild 0.28.2.",
    "",
    "Bundled runtime notice sources:",
  ];
  for (const record of notices.records) {
    lines.push(
      `- ${record.package}@${record.version} ${record.source} ` +
        `(${record.snapshot}): sha256:${record.sha256}; ${record.integrity}`,
    );
  }
  lines.push("", "Generated files:");
  for (const file of [...files.values(), ...generated]) {
    lines.push(`- ${file[0] || file.name}: sha256:${digest(file[1] || file.contents)}`);
  }
  return `${lines.join("\n")}\n`;
}

/*
 * Keep packageJson read above as an explicit assertion that the runtime entry
 * remains a declared input even though its transitive closure is lockfile
 * driven.
 */
if (!packageJson.devDependencies?.["monaco-editor"]) {
  throw new Error("monaco-editor must remain a declared browser build input");
}

function createManifest(entries) {
  const manifest = {};
  for (const name of [...entries.keys()].sort()) {
    const contents = entries.get(name);
    manifest[name] = {
      media_type: mediaType(name),
      cache_control: hashed(name)
        ? "public, max-age=31536000, immutable"
        : "no-store",
      sha256: digest(contents),
      size: contents.length,
    };
  }
  manifest["manifest.json"] = {
    media_type: "application/json; charset=utf-8",
    cache_control: "no-store",
  };
  return manifest;
}

async function publish(entries, manifest) {
  const paths = await publicationPaths();
  let stage;
  let transactionStarted = false;
  const lock = await acquirePublicationLock(paths.lock);
  try {
    await recoverPublication(paths);
    await assertSafeRoot(paths.live, "live");
    stage = await mkdtemp(join(paths.parent, `${paths.prefix}-`));
    const packageInitializer = existsSync(join(paths.live, "__init__.py"))
      ? join(paths.live, "__init__.py")
      : join(
          root,
          "..",
          "src",
          "codesignal_practice_simulator",
          "web",
          "static",
          "__init__.py",
        );
    if (existsSync(packageInitializer)) {
      await writeDurableFile(
        join(stage, "__init__.py"),
        await readFile(packageInitializer),
      );
    }
    for (const [name, contents] of entries) {
      await writeDurableFile(join(stage, name), contents);
    }
    await writeDurableFile(
      join(stage, "manifest.json"),
      `${JSON.stringify(manifest, null, 2)}\n`,
    );
    await assertCompleteTree(stage);
    await syncDirectory(stage);

    await checkpoint("lock-acquired");
    await checkpoint("after-durable-stage");
    await writeTransaction(paths.marker, {
      backup: paths.backup,
      stage,
      phase: "prepared",
    });
    transactionStarted = true;
    await checkpoint("after-marker-prepared");
    await holdLock();
    await removeSafePath(paths.backup, "backup");
    const liveState = await assertSafeRoot(paths.live, "live");
    if (liveState.exists) await rename(paths.live, paths.backup);
    await writeTransaction(paths.marker, {
      backup: paths.backup,
      stage,
      phase: "old-moved",
    });
    await checkpoint("after-old-moved");
    await holdLock();
    await checkpoint("before-live-rename");
    await assertCompleteTree(stage);
    await rename(stage, paths.live);
    await checkpoint("after-live-rename");
    await writeTransaction(paths.marker, {
      backup: paths.backup,
      stage,
      phase: "new-published",
    });
    await removeSafePath(paths.backup, "backup");
    await removeSafePath(paths.marker, "marker");
    await syncDirectory(paths.parent);
  } finally {
    await lock.release();
    if (stage && !transactionStarted) {
      await removeSafePath(stage, "stage");
    }
  }
}

async function publicationPaths() {
  const requestedLive = resolve(staticRoot);
  const bases = await trustedOutputBases();
  const validated = await validateOutputRoot(requestedLive, bases);
  await ensureSafeDirectory(validated.parent, validated.base);
  const parent = validated.parent;
  const live = validated.live;
  const name = basename(live);
  return {
    parent,
    live,
    backup: join(parent, `.${name}.previous`),
    marker: join(parent, `.${name}.publish.json`),
    lock: join(parent, `.${name}.publish.lock`),
    prefix: `.${name}.stage`,
  };
}

async function trustedOutputBases() {
  const lexicalBases = [resolve(root, ".."), resolve(tmpdir())];
  const bases = [];
  for (const lexical of lexicalBases) {
    const state = await lstatState(lexical);
    if (!state.exists || !state.safe || !state.isDirectory) {
      throw new Error("trusted asset publication base is unavailable");
    }
    const canonical = await realpath(lexical);
    if (!bases.some((base) => base.canonical === canonical)) {
      bases.push({ lexical, canonical });
      if (canonical !== lexical) {
        bases.push({ lexical: canonical, canonical });
      }
    }
  }
  return bases;
}

async function validateOutputRoot(requested, bases) {
  for (const base of bases) {
    const relativeOutput = relative(base.lexical, requested);
    if (relativeOutput === "" || isOutsidePath(relativeOutput)) continue;
    const components = relativeOutput.split(sep).filter(Boolean);
    let lexicalCurrent = base.lexical;
    let canonicalCurrent = base.canonical;
    for (let index = 0; index < components.length; index += 1) {
      const component = components[index];
      lexicalCurrent = join(lexicalCurrent, component);
      canonicalCurrent = join(canonicalCurrent, component);
      if (!isPathWithin(base.canonical, canonicalCurrent)) {
        throw new Error("asset publication output escapes a trusted base");
      }
      const state = await lstatState(lexicalCurrent);
      if (!state.exists) {
        return {
          base,
          parent: join(base.canonical, ...components.slice(0, -1)),
          live: join(base.canonical, ...components),
        };
      }
      if (!state.safe) {
        throw new Error("asset publication output has a symlink ancestor");
      }
      if (index < components.length - 1 && !state.isDirectory) {
        throw new Error("asset publication output ancestor is not a directory");
      }
      const actual = await realpath(lexicalCurrent);
      if (!isPathWithin(base.canonical, actual)) {
        throw new Error("asset publication output has a canonical escape");
      }
      canonicalCurrent = actual;
    }
    const state = await lstatState(lexicalCurrent);
    if (state.exists && (!state.safe || !state.isDirectory)) {
      throw new Error("asset publication output root is unsafe");
    }
    return {
      base,
      parent: join(base.canonical, ...components.slice(0, -1)),
      live: join(base.canonical, ...components),
    };
  }
  throw new Error("asset publication output must be under a trusted base");
}

async function ensureSafeDirectory(directory, base) {
  const relativeDirectory = relative(base.canonical, directory);
  if (relativeDirectory === "" || isOutsidePath(relativeDirectory)) {
    throw new Error("asset publication parent escapes a trusted base");
  }
  let current = base.canonical;
  for (const component of relativeDirectory.split(sep).filter(Boolean)) {
    current = join(current, component);
    const state = await lstatState(current);
    if (!state.exists) {
      await mkdir(current);
    }
    const after = await lstatState(current);
    if (!after.exists || !after.safe || !after.isDirectory) {
      throw new Error("asset publication directory became unsafe");
    }
  }
}

function isPathWithin(parent, candidate) {
  const relativePath = relative(parent, candidate);
  return relativePath === "" || !isOutsidePath(relativePath);
}

function isOutsidePath(relativePath) {
  return relativePath === ".."
    || relativePath.startsWith(`..${sep}`)
    || relativePath.startsWith(sep)
    || /^[A-Za-z]:[\\/]/u.test(relativePath);
}

async function recoverPublication(paths) {
  const markerState = await lstatState(paths.marker);
  if (!markerState.exists) {
    await recoverWithoutMarker(paths);
    return;
  }
  if (!markerState.safe || !markerState.isFile) {
    throw new Error("asset publication marker is not a regular file");
  }
  let transaction;
  try {
    transaction = JSON.parse(await readFile(paths.marker, "utf8"));
  } catch {
    await recoverMalformedTransaction(paths);
    return;
  }
  if (!validTransaction(paths, transaction)) {
    await recoverMalformedTransaction(paths);
    return;
  }
  const candidates = await generationCandidates(paths, transaction.stage);
  const selected = candidates.live
    ? paths.live
    : candidates.stage
      ? transaction.stage
      : candidates.backup
        ? paths.backup
        : null;
  if (selected === null) {
    throw new Error("asset publication transaction cannot be recovered");
  }
  if (selected !== paths.live) {
    await removeSafePath(paths.live, "live");
    await rename(selected, paths.live);
  }
  await removeSafePath(paths.backup, "backup");
  await removeSafePath(transaction.stage, "stage");
  await removeSafePath(paths.marker, "marker");
  await syncDirectory(paths.parent);
}

async function recoverMalformedTransaction(paths) {
  const candidates = await generationCandidates(paths);
  if (!candidates.live && candidates.backup) {
    await removeSafePath(paths.live, "live");
    await rename(paths.backup, paths.live);
  } else if (!candidates.live && !candidates.backup) {
    throw new Error("malformed asset publication transaction cannot be recovered");
  }
  for (const stage of await knownStageDirectories(paths)) {
    await isCompleteTree(stage);
  }
  await removeSafePath(paths.backup, "backup");
  for (const stage of await knownStageDirectories(paths)) {
    await removeSafePath(stage, "stage");
  }
  await removeSafePath(paths.marker, "marker");
  await syncDirectory(paths.parent);
}

function validTransaction(paths, transaction) {
  return (
    transaction &&
    typeof transaction === "object" &&
    transaction.backup === paths.backup &&
    typeof transaction.stage === "string" &&
    safeStagePath(paths, transaction.stage) &&
    transaction.phase &&
    ["prepared", "old-moved", "new-published"].includes(transaction.phase)
  );
}

async function knownStageDirectories(paths) {
  let names;
  try {
    names = await readdir(paths.parent);
  } catch {
    return [];
  }
  const stages = [];
  const pattern = stagePattern(paths);
  for (const name of names) {
    if (!pattern.test(name)) continue;
    const candidate = join(paths.parent, name);
    try {
      const state = await lstatState(candidate);
      if (state.safe && state.isDirectory) stages.push(candidate);
    } catch {
      // Another recovery pass may have removed it.
    }
  }
  return stages;
}

async function assertCompleteTree(directory) {
  if (!(await isCompleteTree(directory))) {
    throw new Error(`staged asset tree is incomplete: ${directory}`);
  }
}

async function isCompleteTree(directory) {
  let manifest;
  try {
    const rootState = await lstatState(directory);
    if (!rootState.safe || !rootState.isDirectory) return false;
    manifest = JSON.parse(
      await readFile(join(directory, "manifest.json"), "utf8"),
    );
  } catch {
    return false;
  }
  if (!manifest || typeof manifest !== "object" || Array.isArray(manifest)) {
    return false;
  }
  const declared = new Set(Object.keys(manifest));
  if (!declared.has("manifest.json")) return false;
  if (!completeAssetNameContract(declared)) return false;
  const actual = new Set();
  const visit = async (current, prefix = "") => {
    let entries;
    try {
      entries = await readdir(current, { withFileTypes: true });
    } catch {
      return false;
    }
    for (const entry of entries) {
      const relative = prefix ? `${prefix}/${entry.name}` : entry.name;
      if (entry.isSymbolicLink()) return false;
      if (entry.isDirectory()) {
        if (entry.name === "__pycache__") continue;
        if (!(await visit(join(current, entry.name), relative))) return false;
      } else if (entry.isFile()) {
        actual.add(relative);
      } else {
        return false;
      }
    }
    return true;
  };
  if (!(await visit(directory))) return false;
  for (const name of declared) {
    if (!safeAssetName(name)) return false;
    const record = manifest[name];
    if (!record || typeof record !== "object" || Array.isArray(record)) return false;
    const path = join(directory, name);
    if (!actual.has(name)) return false;
    if (name === "manifest.json") {
      if (
        Object.keys(record).sort().join(",") !== "cache_control,media_type"
        || record.media_type !== "application/json; charset=utf-8"
        || record.cache_control !== "no-store"
      ) {
        return false;
      }
      continue;
    }
    if (
      Object.keys(record).sort().join(",") !==
      "cache_control,media_type,sha256,size"
    ) {
      return false;
    }
    const body = await readFile(path);
    if (
      record.media_type !== mediaType(name) ||
      record.cache_control !== (hashed(name)
        ? "public, max-age=31536000, immutable"
        : "no-store") ||
      typeof record.sha256 !== "string" ||
      !/^[0-9a-f]{64}$/u.test(record.sha256) ||
      !Number.isInteger(record.size) ||
      record.size < 0 ||
      record.size !== body.length ||
      record.sha256 !== digest(body)
    ) {
      return false;
    }
  }
  for (const name of actual) {
    if (!declared.has(name) && name !== "__init__.py") return false;
  }
  return actual.has("manifest.json");
}

function completeAssetNameContract(names) {
  for (const name of names) {
    if (!safeAssetName(name)) return false;
  }
  for (const name of REQUIRED_STABLE_ASSETS) {
    if (!names.has(name)) return false;
  }
  for (const pattern of HASHED_ASSET_PATTERNS) {
    if ([...names].filter((name) => pattern.test(name)).length !== 1) {
      return false;
    }
  }
  const expected = new Set([
    ...REQUIRED_STABLE_ASSETS,
    ...HASHED_ASSET_PATTERNS.flatMap((pattern) => (
      [...names].filter((name) => pattern.test(name))
    )),
  ]);
  return (
    names.size === expected.size
    && [...names].every((name) => expected.has(name))
  );
}

async function recoverWithoutMarker(paths) {
  const candidates = await generationCandidates(paths);
  const stageCandidates = await knownStageDirectories(paths);
  const usableStages = [];
  for (const stage of stageCandidates) {
    if (await isCompleteTree(stage)) usableStages.push(stage);
  }
  if (candidates.live) {
    await removeSafePath(paths.backup, "backup");
    for (const stage of stageCandidates) {
      await removeSafePath(stage, "stage");
    }
    return;
  }
  if (candidates.backup) {
    await removeSafePath(paths.live, "live");
    await rename(paths.backup, paths.live);
    for (const stage of stageCandidates) {
      await removeSafePath(stage, "stage");
    }
    await syncDirectory(paths.parent);
    return;
  }
  if (usableStages.length === 1) {
    await removeSafePath(paths.live, "live");
    await rename(usableStages[0], paths.live);
    await syncDirectory(paths.parent);
    return;
  }
  if (candidates.any || usableStages.length > 1) {
    throw new Error("asset publication has no valid generation");
  }
}

async function generationCandidates(paths, transactionStage = null) {
  const stage = transactionStage
    ? await isCompleteTree(transactionStage)
    : false;
  const live = await isCompleteTree(paths.live);
  const backup = await isCompleteTree(paths.backup);
  const liveState = await lstatState(paths.live);
  const backupState = await lstatState(paths.backup);
  const stageState = transactionStage
    ? await lstatState(transactionStage)
    : { exists: false, safe: true, isDirectory: false };
  return {
    live,
    backup,
    stage,
    any: liveState.exists || backupState.exists || stageState.exists,
  };
}

function safeStagePath(paths, candidate) {
  if (typeof candidate !== "string") return false;
  const resolved = resolve(candidate);
  return (
    candidate === resolved &&
    !candidate.split(/[\\/]/u).includes("..") &&
    dirname(resolved) === paths.parent &&
    stagePattern(paths).test(basename(resolved)) &&
    resolved !== paths.live &&
    resolved !== paths.backup &&
    resolved !== paths.marker
  );
}

function stagePattern(paths) {
  return new RegExp(
    `^\\.${escapeRegExp(basename(paths.live))}\\.stage-[A-Za-z0-9_-]+$`,
    "u",
  );
}

function safeAssetName(name) {
  return (
    typeof name === "string" &&
    name.length > 0 &&
    SAFE_ASSET_NAME.test(name) &&
    name !== "." &&
    name !== ".." &&
    !name.includes("/") &&
    !name.includes("\\")
  );
}

async function lstatState(path) {
  try {
    const state = await lstat(path);
    return {
      exists: true,
      safe: !state.isSymbolicLink(),
      isDirectory: state.isDirectory(),
      isFile: state.isFile(),
    };
  } catch (error) {
    if (error.code === "ENOENT") {
      return { exists: false, safe: true, isDirectory: false, isFile: false };
    }
    throw error;
  }
}

async function assertSafeRoot(path, label) {
  const state = await lstatState(path);
  if (state.exists && (!state.safe || !state.isDirectory)) {
    throw new Error(`asset publication ${label} root is unsafe`);
  }
  return state;
}

async function removeSafePath(path, label) {
  const state = await lstatState(path);
  if (!state.exists) return;
  if (!state.safe) {
    throw new Error(`asset publication ${label} path is unsafe`);
  }
  await rm(path, { recursive: state.isDirectory, force: true });
}

async function writeDurableFile(path, contents) {
  const handle = await openFile(path, "w");
  try {
    await handle.writeFile(contents);
    await handle.sync();
  } finally {
    await handle.close();
  }
}

async function writeTransaction(path, value) {
  await writeAtomic(path, `${JSON.stringify(value)}\n`);
}

async function writeAtomic(path, contents) {
  const temporary = `${path}.${process.pid}.${randomToken()}.tmp`;
  try {
    const handle = await openFile(temporary, "w");
    try {
      await handle.writeFile(contents, "utf8");
      await handle.sync();
    } finally {
      await handle.close();
    }
    await rename(temporary, path);
    await syncDirectory(dirname(path));
  } finally {
    await rm(temporary, { force: true });
  }
}

async function syncDirectory(directory) {
  let handle;
  try {
    handle = await openFile(directory, "r");
  } catch (error) {
    if (isUnsupportedWindowsDirectorySyncError(error)) return;
    throw error;
  }
  try {
    await handle.sync();
  } catch (error) {
    if (!isUnsupportedWindowsDirectorySyncError(error)) throw error;
  } finally {
    await handle.close();
  }
}

function isUnsupportedWindowsDirectorySyncError(error) {
  // Windows does not support flushing directory handles. The resulting
  // EPERM/EINVAL/ENOSYS codes are documented unsupported-operation errors;
  // every other open or sync failure remains fatal. Windows therefore has
  // atomic rename but not the POSIX post-rename power-loss guarantee.
  return process.platform === "win32"
    && ["EPERM", "EINVAL", "ENOSYS"].includes(error?.code);
}

async function acquirePublicationLock(path) {
  const reclaimerPath = `${path}.reclaimer`;
  const owner = {
    version: 1,
    kind: "build",
    pid: process.pid,
    created_at: Date.now(),
    token: randomToken(),
  };
  const configuredWait = Number(process.env.ASSET_PUBLISH_WAIT_SECONDS);
  const waitSeconds = Number.isFinite(configuredWait) && configuredWait >= 0
    ? configuredWait
    : PUBLICATION_WAIT_SECONDS;
  const deadline = Date.now() + waitSeconds * 1000;
  while (true) {
    await recoverStaleReclaimer(reclaimerPath);
    if ((await lstatState(reclaimerPath)).exists) {
      if (Date.now() >= deadline) {
        throw new Error("browser asset publication lock did not become available");
      }
      await delay(PUBLICATION_POLL_MILLISECONDS);
      continue;
    }
    try {
      const handle = await openFile(path, "wx");
      try {
        await handle.writeFile(`${JSON.stringify(owner)}\n`, "utf8");
        await handle.sync();
      } finally {
        await handle.close();
      }
      return {
        release: async () => {
          await removeOwnedPath(path, owner.token);
        },
      };
    } catch (error) {
      if (error.code !== "EEXIST") throw error;
      const current = await lockSnapshot(path);
      if (await staleLock(path, current?.owner)) {
        const elected = await electReclaimer(reclaimerPath);
        if (elected) {
          const acquired = await reclaimAndAcquire(
            path,
            reclaimerPath,
            elected,
            owner,
          );
          if (acquired) {
            return {
              release: async () => {
                await removeOwnedPath(path, owner.token);
              },
            };
          }
        }
      }
      if (Date.now() >= deadline) {
        throw new Error("browser asset publication lock did not become available");
      }
      await delay(PUBLICATION_POLL_MILLISECONDS);
    }
  }
}

async function electReclaimer(path) {
  const owner = {
    version: 1,
    kind: "reclaimer",
    pid: process.pid,
    created_at: Date.now(),
    token: randomToken(),
  };
  try {
    const handle = await openFile(path, "wx");
    try {
      await handle.writeFile(`${JSON.stringify(owner)}\n`, "utf8");
      await handle.sync();
    } finally {
      await handle.close();
    }
    return owner;
  } catch (error) {
    if (error.code === "EEXIST") return null;
    throw error;
  }
}

async function reclaimAndAcquire(path, reclaimerPath, reclaimer, owner) {
  try {
    const election = await readLockOwner(reclaimerPath);
    if (election?.token !== reclaimer.token) return false;
    const observed = await lockSnapshot(path);
    if (observed && !(await staleLock(path, observed.owner))) return false;
    const current = await lockSnapshot(path);
    if (observed && !sameLockSnapshot(observed, current)) return false;
    if (
      observed?.owner?.token
      && current?.owner?.token !== observed.owner.token
    ) {
      return false;
    }
    if (current) await rm(path, { force: true });
    try {
      const handle = await openFile(path, "wx");
      try {
        await handle.writeFile(`${JSON.stringify(owner)}\n`, "utf8");
        await handle.sync();
      } finally {
        await handle.close();
      }
    } catch (error) {
      if (error.code !== "EEXIST") throw error;
      return false;
    }
    return true;
  } finally {
    await removeOwnedPath(reclaimerPath, reclaimer.token);
  }
}

async function recoverStaleReclaimer(path) {
  const current = await lockSnapshot(path);
  if (!current || !(await staleReclaimer(path, current.owner))) return;
  if (current.owner?.token) {
    await removeOwnedPath(path, current.owner.token);
  } else {
    const replacement = await lockSnapshot(path);
    if (sameLockSnapshot(current, replacement)) {
      await rm(path, { force: true });
    }
  }
}

async function staleReclaimer(path, owner) {
  if (Number.isInteger(owner?.pid) && owner.pid > 0) {
    return !processIsAlive(owner.pid);
  }
  try {
    return Date.now() - (await lstat(path)).mtimeMs >= RECLAIMER_STALE_SECONDS * 1000;
  } catch {
    return false;
  }
}

async function removeOwnedPath(path, token) {
  const current = await lockSnapshot(path);
  if (current?.owner?.token !== token) return;
  const replacement = await lockSnapshot(path);
  if (!sameLockSnapshot(current, replacement)) return;
  await rm(path, { force: true });
}

async function lockSnapshot(path) {
  let state;
  try {
    state = await lstat(path);
  } catch (error) {
    if (error.code === "ENOENT") return null;
    throw error;
  }
  return {
    owner: await readLockOwner(path),
    dev: state.dev,
    ino: state.ino,
    mtimeMs: state.mtimeMs,
    size: state.size,
  };
}

function sameLockSnapshot(first, second) {
  return Boolean(
    first
    && second
    && first.dev === second.dev
    && first.ino === second.ino
    && first.mtimeMs === second.mtimeMs
    && first.size === second.size,
  );
}

async function readLockOwner(path) {
  try {
    const value = JSON.parse(await readFile(path, "utf8"));
    return value && typeof value === "object" ? value : null;
  } catch {
    return null;
  }
}

async function staleLock(path, owner) {
  if (Number.isInteger(owner?.pid) && owner.pid > 0) {
    return !processIsAlive(owner.pid);
  }
  let age = 0;
  try {
    age = Date.now() - (await lstat(path)).mtimeMs;
  } catch {
    return false;
  }
  return age >= STALE_LOCK_SECONDS * 1000;
}

function processIsAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return error.code === "EPERM";
  }
}

function delay(milliseconds) {
  return new Promise((resolvePromise) => setTimeout(resolvePromise, milliseconds));
}

async function holdLock() {
  const milliseconds = Number(process.env.ASSET_PUBLISH_HOLD_LOCK_MS || 0);
  if (Number.isFinite(milliseconds) && milliseconds > 0) {
    await new Promise((resolvePromise) => setTimeout(resolvePromise, milliseconds));
  }
}

async function checkpoint(name) {
  if (process.env.ASSET_PUBLISH_CRASH_AT === name) {
    process.exit(91);
  }
}

function randomToken() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

function mediaType(name) {
  if (name.endsWith(".html")) return "text/html; charset=utf-8";
  if (name.endsWith(".js")) return "text/javascript; charset=utf-8";
  if (name.endsWith(".css")) return "text/css; charset=utf-8";
  if (name.endsWith(".json")) return "application/json; charset=utf-8";
  if (name.endsWith(".svg")) return "image/svg+xml";
  if (name.endsWith(".ttf")) return "font/ttf";
  return "text/plain; charset=utf-8";
}

function hashed(name) {
  return /^(app|styles|editor\.worker|language\.worker)-[A-Za-z0-9_-]+\.(js|css)$/.test(name)
    || /^[A-Za-z0-9_-]+-[A-Za-z0-9_-]+\.ttf$/.test(name);
}

function digest(contents) {
  return createHash("sha256").update(contents).digest("hex");
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/gu, "\\$&");
}
