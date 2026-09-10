import {
  closeSync,
  fstatSync,
  readSync,
  writeSync,
} from "node:fs";
import { isAbsolute, join, relative, resolve } from "node:path";
import {
  createArtifactAtRootSync,
  openArtifactAtRootSync,
  openOutputRootSync,
  processArtifactAtRootSync,
  removeArtifactAtRootSync,
  removeDirectoryContentsSync,
  sanitizeDirectoryContentsSync,
  writeArtifactAtRootSync,
} from "./failure_artifact_paths.mjs";
import {
  MAX_TRACE_ARCHIVE_BYTES,
  sanitizeErrorContext,
  sanitizeFailureScreenshot,
  sanitizeTraceArchiveBuffer,
  sanitizeTextArtifact,
  rewriteValidatedDescriptorSync,
} from "./failure_artifacts.mjs";

const TEXT_ATTACHMENT = /\.(?:json|log|txt|xml|html|js|css|mjs|py|md|yaml|yml)$/iu;
const TRACE_ATTACHMENT = /\.zip$/iu;
const TEXT_ATTACHMENT_NAMES = new Set([
  "error-context",
  "stdout",
  "stderr",
]);
const FAILURE_SCREENSHOT = "sanitized-failure-screenshot";
const GENERIC_FAILURE_MESSAGE = "Test failed; inspect sanitized artifacts.";
const CLEANUP_FAILURE_MESSAGE =
  "Failure artifact cleanup failed; residual artifacts may remain.";
export const OWNERSHIP_FAILURE_MESSAGE =
  "Failure artifact output ownership could not be acquired.";
const MAX_SCREENSHOT_BYTES = 32 * 1024 * 1024;
const SAFE_ERROR_NAMES = new Set([
  "AssertionError",
  "Error",
  "EvalError",
  "RangeError",
  "ReferenceError",
  "SyntaxError",
  "TimeoutError",
  "TypeError",
  "URIError",
]);

export function terminateOnOutputOwnershipFailure(
  message = OWNERSHIP_FAILURE_MESSAGE,
) {
  try {
    writeSync(2, `${message}\n`);
  } catch {
    // Termination remains fail-closed if the inherited diagnostic stream fails.
  }
  process.exitCode = 1;
  process.exit(1);
}

export default class FailureArtifactsReporter {
  constructor({ terminate = terminateOnOutputOwnershipFailure } = {}) {
    this.terminate = terminate;
  }

  onBegin(config) {
    const outputDirs = [
      config?.outputDir,
      ...(config?.projects || []).map((project) => project.outputDir),
    ].filter((outputDir) => typeof outputDir === "string" && outputDir.length);
    const outputPaths = [...new Set(outputDirs.map((outputDir) => resolve(outputDir)))];
    this.outputRoots = [];
    try {
      for (const path of outputPaths) {
        this.outputRoots.push({
          ...openOutputRootSync(path),
          tainted: false,
        });
      }
    } catch {
      closeOutputRoots(this.outputRoots);
      this.outputRoots = [];
      this.terminate(OWNERSHIP_FAILURE_MESSAGE);
      const error = new Error(OWNERSHIP_FAILURE_MESSAGE);
      error.stack = `${error.name}: ${error.message}`;
      throw error;
    }
    this.attachmentSerial = 0;
  }

  onTestEnd(_test, result) {
    const outputRoots = this.outputRoots || [];
    const sensitiveValues = [
      process.env.HARNESS_FAILURE_PROBE_TOKEN,
    ].filter(Boolean);
    result.stdout = sanitizeResultStream(result.stdout, sensitiveValues);
    result.stderr = sanitizeResultStream(result.stderr, sensitiveValues);
    const failed = ["failed", "timedOut", "interrupted"].includes(result.status);
    if (failed) {
      const sanitizedErrors = Array.isArray(result.errors)
        ? result.errors.map(sanitizeTestError)
        : [];
      if (result.error) {
        result.error = sanitizedErrors[0] || sanitizeTestError(result.error);
      } else if (sanitizedErrors.length) {
        result.error = sanitizedErrors[0];
      }
      result.errors = sanitizedErrors;
    }

    const retained = [];
    for (const attachment of result.attachments || []) {
      const root = attachment.path
        ? findOutputRoot(attachment.path, outputRoots)
        : undefined;
      if (attachment.path && (!root || root.descriptor === undefined)) {
        delete attachment.body;
        continue;
      }
      if (attachment.path && process.platform === "darwin") {
        if (processMacPathAttachment(
          attachment,
          root,
          failed,
          sensitiveValues,
          this.attachmentSerial++,
        )) {
          retained.push(attachment);
        } else {
          delete attachment.body;
        }
        continue;
      }
      let artifact;
      try {
        if (attachment.path) {
          artifact = openArtifactAtRootSync(root, attachment.path);
        }
        if (failed && isFailureScreenshot(attachment)) {
          sanitizeFailureScreenshotAttachment(
            attachment,
            artifact?.descriptor,
            root,
            this.attachmentSerial++,
          );
          retained.push(attachment);
        } else if (failed && isTraceAttachment(attachment)) {
          sanitizeTraceAttachment(
            attachment,
            sensitiveValues,
            artifact?.descriptor,
          );
          retained.push(attachment);
        } else if (failed && isTextAttachment(attachment)) {
          sanitizeTextAttachment(
            attachment,
            sensitiveValues,
            artifact?.descriptor,
          );
          retained.push(attachment);
        }
      } catch (error) {
        if (root && error?.cleanupFailed) root.tainted = true;
        // A failed or unsupported sanitizer must never leave a raw artifact behind.
      } finally {
        if (!retained.includes(attachment) && artifact !== undefined) {
          try {
            rewriteDescriptor(artifact.descriptor, Buffer.from("[REDACTED]\n"));
          } catch {
            if (root) root.tainted = true;
            // The descriptor is the only safe target; omit the attachment if it fails.
          }
        }
        if (artifact !== undefined) {
          try {
            artifact.close();
          } catch {
            if (root) root.tainted = true;
          }
        }
      }
      if (!retained.includes(attachment)) {
        delete attachment.body;
      }
    }
    result.attachments.splice(0, result.attachments.length, ...retained);
  }

  onEnd() {
    let cleanupFailed = false;
    const sensitiveValues = [
      process.env.HARNESS_FAILURE_PROBE_TOKEN,
    ].filter(Boolean);
    for (const root of this.outputRoots || []) {
      if (root.descriptor === undefined) {
        cleanupFailed = true;
        continue;
      }
      try {
        if (!sanitizeDirectoryContentsSync(root, sensitiveValues)) {
          root.tainted = true;
        }
        if (root.tainted && !removeDirectoryContentsSync(root)) {
          cleanupFailed = true;
        }
      } catch {
        cleanupFailed = true;
      } finally {
        try {
          closeSync(root.descriptor);
        } catch {
          // The root descriptor is already closed.
        }
        root.descriptor = undefined;
      }
    }
    if (cleanupFailed) {
      process.stdout.write(`${CLEANUP_FAILURE_MESSAGE}\n`);
      return { status: "failed" };
    }
  }
}

function closeOutputRoots(roots) {
  for (const root of roots) {
    try {
      closeSync(root.descriptor);
    } catch {
      // The root descriptor is already closed.
    }
    root.descriptor = undefined;
  }
}

function sanitizeTestError(error) {
  const safeError = {
    message: GENERIC_FAILURE_MESSAGE,
    name: SAFE_ERROR_NAMES.has(error?.name) ? error.name : "Error",
  };
  const location = sanitizeErrorLocation(error?.location);
  if (location) safeError.location = location;
  return safeError;
}

function sanitizeErrorLocation(location) {
  if (!location || typeof location !== "object") return undefined;
  const safeLocation = {};
  for (const key of ["line", "column"]) {
    if (Number.isInteger(location[key]) && location[key] > 0) {
      safeLocation[key] = location[key];
    }
  }
  return Object.keys(safeLocation).length ? safeLocation : undefined;
}

function isFailureScreenshot(attachment) {
  return attachment.name === FAILURE_SCREENSHOT &&
    attachment.contentType === "image/png" &&
    (typeof attachment.path === "string" || attachment.body !== undefined);
}

function processMacPathAttachment(
  attachment,
  outputRoot,
  failed,
  sensitiveValues,
  serial,
) {
  const kind = failed
    ? isFailureScreenshot(attachment)
      ? "screenshot"
      : isTraceAttachment(attachment)
        ? "trace"
        : isTextAttachment(attachment)
          ? "text"
          : "redact"
    : "redact";
  const retainable = failed && kind !== "redact";
  try {
    const outcome = processArtifactAtRootSync(
      outputRoot,
      attachment.path,
      kind,
      sensitiveValues,
    );
    if (!retainable || !outcome.retained) return false;
    if (attachment.body !== undefined) {
      if (kind === "screenshot") {
        sanitizeFailureScreenshotAttachment(
          attachment,
          undefined,
          undefined,
          serial,
        );
      } else if (kind === "trace") {
        sanitizeTraceAttachment(attachment, sensitiveValues, undefined);
      } else {
        sanitizeTextAttachment(attachment, sensitiveValues, undefined);
      }
    }
    return true;
  } catch (error) {
    if (error?.cleanupFailed) outputRoot.tainted = true;
    return false;
  }
}

function sanitizeFailureScreenshotAttachment(
  attachment,
  descriptor,
  outputRoot,
  serial,
) {
  const original = descriptor === undefined
    ? toBuffer(attachment.body)
    : readDescriptorBounded(descriptor, MAX_SCREENSHOT_BYTES);
  const sanitized = sanitizeFailureScreenshot(original);
  if (attachment.body !== undefined) {
    attachment.body = preserveBodyType(attachment.body, sanitized);
    if (outputRoot && descriptor === undefined) {
      materializeScreenshotBody(attachment, sanitized, outputRoot, serial);
    }
  }
  if (descriptor !== undefined) {
    rewriteDescriptor(descriptor, sanitized);
  }
}

function materializeScreenshotBody(attachment, sanitized, outputRoot, serial) {
  const name = `.sanitized-failure-screenshot-${process.pid}-${serial}.png`;
  if (process.platform === "darwin") {
    writeArtifactAtRootSync(outputRoot, name, sanitized);
    attachment.path = join(outputRoot.path, name);
    delete attachment.body;
    return;
  }
  const descriptor = createArtifactAtRootSync(outputRoot, name);
  try {
    rewriteDescriptor(descriptor, sanitized);
  } catch (error) {
    try {
      removeArtifactAtRootSync(outputRoot, name);
    } catch (cleanupError) {
      outputRoot.tainted = true;
      error.cause = cleanupError;
    }
    throw error;
  } finally {
    closeSync(descriptor);
  }
  attachment.path = join(outputRoot.path, name);
  delete attachment.body;
}

function isTraceAttachment(attachment) {
  return attachment.name === "trace" ||
    (typeof attachment.path === "string" && TRACE_ATTACHMENT.test(attachment.path));
}

function isTextAttachment(attachment) {
  return TEXT_ATTACHMENT_NAMES.has(attachment.name) ||
    (typeof attachment.path === "string" && TEXT_ATTACHMENT.test(attachment.path));
}

function sanitizeTraceAttachment(attachment, sensitiveValues, descriptor) {
  if (attachment.body !== undefined) {
    const original = toBuffer(attachment.body);
    const sanitized = sanitizeTraceArchiveBuffer(original, sensitiveValues).archive;
    attachment.body = preserveBodyType(attachment.body, sanitized);
  }
  if (descriptor !== undefined) {
    const sanitized = sanitizeTraceArchiveBuffer(
      readDescriptorBounded(descriptor, MAX_TRACE_ARCHIVE_BYTES),
      sensitiveValues,
    ).archive;
    rewriteDescriptor(descriptor, sanitized);
  }
}

function sanitizeTextAttachment(attachment, sensitiveValues, descriptor) {
  if (attachment.body !== undefined) {
    const text = toText(attachment.body);
    const sanitized = attachment.name === "error-context"
      ? sanitizeErrorContext(text, sensitiveValues)
      : sanitizeTextArtifact(text, sensitiveValues);
    attachment.body = preserveBodyType(attachment.body, Buffer.from(sanitized, "utf8"));
  }
  if (descriptor !== undefined) {
    rewriteDescriptor(descriptor, Buffer.from("[REDACTED]\n"));
  }
}

function toBuffer(body) {
  if (Buffer.isBuffer(body)) return body;
  if (body instanceof Uint8Array) return Buffer.from(body);
  if (typeof body === "string") return Buffer.from(body, "binary");
  throw new TypeError("unsupported inline attachment body");
}

function toText(body) {
  if (typeof body === "string") return body;
  if (Buffer.isBuffer(body) || body instanceof Uint8Array) {
    return Buffer.from(body).toString("utf8");
  }
  throw new TypeError("unsupported inline attachment body");
}

function preserveBodyType(original, sanitized) {
  return typeof original === "string" ? sanitized.toString("utf8") : sanitized;
}

function findOutputRoot(artifactPath, outputRoots) {
  if (typeof artifactPath !== "string" || !artifactPath.length) return undefined;
  const candidate = resolve(artifactPath);
  return [...outputRoots]
    .filter((root) => {
      const fromRoot = relative(root.path, candidate);
      return fromRoot &&
        !isAbsolute(fromRoot) &&
        fromRoot !== ".." &&
        !fromRoot.startsWith("../");
    })
    .sort((left, right) => right.path.length - left.path.length)[0];
}

function readDescriptorBounded(descriptor, maximumBytes) {
  const stat = fstatSync(descriptor);
  if (!stat.isFile()) throw new Error("artifact is not a regular file");
  if (
    !Number.isSafeInteger(stat.size) ||
    stat.size < 0 ||
    stat.size > maximumBytes
  ) {
    throw new Error("artifact exceeds its read limit");
  }
  const contents = Buffer.alloc(stat.size);
  let offset = 0;
  while (offset < contents.length) {
    const bytesRead = readSync(
      descriptor,
      contents,
      offset,
      contents.length - offset,
      offset,
    );
    if (bytesRead <= 0) throw new Error("artifact read made no progress");
    offset += bytesRead;
  }
  return contents;
}

function rewriteDescriptor(descriptor, contents) {
  rewriteValidatedDescriptorSync(descriptor, contents);
}

function sanitizeResultStream(stream, sensitiveValues) {
  if (stream === undefined || stream === null) return stream;
  if (Array.isArray(stream)) {
    return stream.map((chunk) => sanitizeResultStreamChunk(chunk, sensitiveValues));
  }
  return sanitizeResultStreamChunk(stream, sensitiveValues);
}

function sanitizeResultStreamChunk(chunk, sensitiveValues) {
  if (
    typeof chunk !== "string" &&
    !Buffer.isBuffer(chunk) &&
    !(chunk instanceof Uint8Array)
  ) {
    return "[REDACTED]\n";
  }
  const replacement = sanitizeTextArtifact(
    toText(chunk),
    sensitiveValues,
  );
  if (typeof chunk === "string") return replacement;
  if (Buffer.isBuffer(chunk)) return Buffer.from(replacement, "utf8");
  if (chunk instanceof Uint8Array) {
    return new Uint8Array(Buffer.from(replacement, "utf8"));
  }
  return replacement;
}
