import {
  closeSync,
  constants as fsConstants,
  fstatSync,
  ftruncateSync,
  lstatSync,
  openSync,
  readSync,
  writeSync,
} from "node:fs";
import { lstat, open as openAsync } from "node:fs/promises";
import { deflateRawSync, deflateSync, inflateRawSync } from "node:zlib";

const ZIP_LOCAL_FILE = 0x04034b50;
const ZIP_CENTRAL_FILE = 0x02014b50;
const ZIP_END = 0x06054b50;
const ZIP_DATA_DESCRIPTOR = 0x08074b50;
const ZIP_METHOD_STORE = 0;
const ZIP_METHOD_DEFLATE = 8;
const ZIP_UTF8_FLAG = 0x0800;
const ZIP_DATA_DESCRIPTOR_FLAG = 0x0008;
const ZIP_END_SIZE = 22;
const ZIP_VERSION = 20;
export const MAX_TRACE_ARCHIVE_BYTES = 32 * 1024 * 1024;
export const MAX_TRACE_ENTRY_COUNT = 256;
export const MAX_TRACE_COMPRESSED_BYTES = 16 * 1024 * 1024;
export const MAX_TRACE_UNCOMPRESSED_BYTES = 64 * 1024 * 1024;
export const MAX_TRACE_ENTRY_BYTES = 16 * 1024 * 1024;
const PNG_SIGNATURE = Buffer.from([
  0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a,
]);
export const MAX_FAILURE_SCREENSHOT_WIDTH = 8192;
export const MAX_FAILURE_SCREENSHOT_HEIGHT = 8192;
export const MAX_FAILURE_SCREENSHOT_PIXELS = 16 * 1024 * 1024;
export const MAX_FAILURE_ARTIFACT_BYTES = 32 * 1024 * 1024;

const TRACE_FILE_STEMS = "(?:trace|test|\\d+-trace|trace-\\d+)";
const TRACE_ENTRIES = new RegExp(
  `^${TRACE_FILE_STEMS}\\.trace$`,
  "u",
);
const TRACE_NETWORK_ENTRIES = new RegExp(
  `^${TRACE_FILE_STEMS}\\.network$`,
  "u",
);
const TRACE_STACK_ENTRIES = new RegExp(
  `^${TRACE_FILE_STEMS}\\.stacks$`,
  "u",
);
const SOURCE_ENTRIES =
  /^src\/[a-f0-9]{40}\.[A-Za-z0-9][A-Za-z0-9._+-]*$/u;
const ATTACHMENT_ENTRIES = /^attachments\/[a-f0-9]{40}$/u;
const SCREENCAST_ENTRIES =
  /^screencast\/page@[a-f0-9]{32}-\d+\.jpeg$/u;
const SCREENSHOT_ENTRIES =
  /^screenshots\/(?:call@[A-Za-z0-9._-]+|[A-Za-z0-9._-]+)-(?:before|action|after)\.png$/u;
const ARIA_ENTRIES =
  /^aria\/(?:call@[A-Za-z0-9._-]+|[A-Za-z0-9._-]+)-(?:before|action|after)\.json$/u;
const RESOURCE_ENTRIES =
  /^resources\/[a-f0-9]{40}(?:\.[A-Za-z0-9][A-Za-z0-9._+-]*)?$/u;
const REMOVED_TRACE_EVENTS = new Set([
  "aria-snapshot",
  "screencast-frame",
  "screenshot",
  "video",
]);
const SAFE_TRACE_STRING_KEYS = new Set([
  "type",
  "callId",
  "class",
  "method",
  "apiName",
  "pageId",
  "frameId",
  "parentId",
  "beforeSnapshot",
  "afterSnapshot",
]);
const SAFE_TRACE_IDENTIFIER = /^(?:call|frame|page|snapshot)@[A-Za-z0-9._-]{1,128}$/u;
const SAFE_TRACE_MEMBER = /^[A-Za-z_][A-Za-z0-9_.-]{0,127}$/u;
const SAFE_TRACE_STRING_GRAMMARS = new Map([
  ["callId", SAFE_TRACE_IDENTIFIER],
  ["pageId", SAFE_TRACE_IDENTIFIER],
  ["frameId", SAFE_TRACE_IDENTIFIER],
  ["parentId", SAFE_TRACE_IDENTIFIER],
  ["beforeSnapshot", SAFE_TRACE_IDENTIFIER],
  ["afterSnapshot", SAFE_TRACE_IDENTIFIER],
  ["class", SAFE_TRACE_MEMBER],
  ["method", SAFE_TRACE_MEMBER],
  ["apiName", SAFE_TRACE_MEMBER],
  ["type", SAFE_TRACE_MEMBER],
]);
const SAFE_TRACE_NUMBER_KEYS = new Set([
  "startTime",
  "endTime",
  "wallTime",
  "duration",
]);
export async function sanitizeTraceArchive(tracePath, sensitiveValues = []) {
  const fileHandle = await openValidatedFileHandle(tracePath);
  try {
    const original = await readValidatedFileHandle(fileHandle);
    const sanitized = sanitizeTraceArchiveBuffer(original, sensitiveValues);
    await rewriteValidatedFileHandle(fileHandle, sanitized.archive);
    return { removedEntries: sanitized.removedEntries };
  } finally {
    await fileHandle.close();
  }
}

export function sanitizeTraceArchiveSync(tracePath, sensitiveValues = []) {
  const descriptor = openValidatedFileDescriptorSync(tracePath);
  try {
    const sanitized = sanitizeTraceArchiveDescriptorSync(
      descriptor,
      sensitiveValues,
    );
    return { removedEntries: sanitized.removedEntries };
  } finally {
    closeSync(descriptor);
  }
}

export function sanitizeTraceArchiveDescriptorSync(
  descriptor,
  sensitiveValues = [],
) {
  const original = readValidatedDescriptorSync(descriptor);
  const sanitized = sanitizeTraceArchiveBuffer(original, sensitiveValues);
  rewriteValidatedDescriptorSync(descriptor, sanitized.archive);
  return sanitized;
}

export function sanitizeArtifactDescriptorSync(
  descriptor,
  kind,
  sensitiveValues = [],
) {
  const stat = fstatSync(descriptor);
  if (!stat.isFile()) throw new Error("artifact is not a regular file");
  if (
    !Number.isSafeInteger(stat.size) ||
    stat.size < 0 ||
    stat.size > MAX_FAILURE_ARTIFACT_BYTES
  ) {
    throw new Error("artifact exceeds its read limit");
  }
  if (kind === "trace") {
    const sanitized = sanitizeTraceArchiveBuffer(
      readValidatedDescriptorSync(descriptor),
      sensitiveValues,
    );
    rewriteValidatedDescriptorSync(descriptor, sanitized.archive);
    return sanitized;
  }
  if (kind === "screenshot") {
    const sanitized = sanitizeFailureScreenshot(
      readCappedDescriptorSync(descriptor, MAX_FAILURE_ARTIFACT_BYTES),
    );
    rewriteValidatedDescriptorSync(descriptor, sanitized);
    return sanitized;
  }
  rewriteValidatedDescriptorSync(descriptor, Buffer.from("[REDACTED]\n"));
  return undefined;
}

async function openValidatedFileHandle(path) {
  const initialStat = await lstat(path);
  if (!initialStat.isFile() || initialStat.isSymbolicLink()) {
    throw new Error("artifact is not a regular file");
  }
  const noFollow = fsConstants.O_NOFOLLOW;
  if (!Number.isInteger(noFollow)) {
    throw new Error("platform does not support O_NOFOLLOW");
  }
  const fileHandle = await openAsync(path, fsConstants.O_RDWR | noFollow);
  try {
    const descriptorStat = await fileHandle.stat();
    if (
      !descriptorStat.isFile() ||
      descriptorStat.dev !== initialStat.dev ||
      descriptorStat.ino !== initialStat.ino
    ) {
      throw new Error("artifact changed during validation");
    }
    return fileHandle;
  } catch (error) {
    await fileHandle.close();
    throw error;
  }
}

export function openValidatedFileDescriptorSync(path) {
  const initialStat = lstatSync(path);
  if (!initialStat.isFile() || initialStat.isSymbolicLink()) {
    throw new Error("artifact is not a regular file");
  }
  const noFollow = fsConstants.O_NOFOLLOW;
  if (!Number.isInteger(noFollow)) {
    throw new Error("platform does not support O_NOFOLLOW");
  }
  const descriptor = openSync(path, fsConstants.O_RDWR | noFollow);
  try {
    const descriptorStat = fstatSync(descriptor);
    if (
      !descriptorStat.isFile() ||
      descriptorStat.dev !== initialStat.dev ||
      descriptorStat.ino !== initialStat.ino
    ) {
      throw new Error("artifact changed during validation");
    }
    return descriptor;
  } catch (error) {
    closeSync(descriptor);
    throw error;
  }
}

export function readValidatedDescriptorSync(descriptor) {
  const stat = fstatSync(descriptor);
  return readCappedDescriptorSync(descriptor, stat);
}

async function readValidatedFileHandle(fileHandle) {
  const stat = await fileHandle.stat();
  return readCappedFileHandle(fileHandle, stat);
}

function readCappedDescriptorSync(
  descriptor,
  stat,
  maximum = MAX_TRACE_ARCHIVE_BYTES,
) {
  if (typeof stat === "number") {
    maximum = stat;
    stat = fstatSync(descriptor);
  }
  if (!stat.isFile()) throw new Error("artifact is not a regular file");
  if (maximum === MAX_TRACE_ARCHIVE_BYTES) {
    assertTraceArchiveFileSize(stat);
  } else if (
    !Number.isSafeInteger(stat.size) ||
    stat.size < 0 ||
    stat.size > maximum
  ) {
    throw new Error("artifact exceeds its read limit");
  }
  const capacity = Math.min(stat.size + 1, maximum + 1);
  const contents = Buffer.alloc(capacity);
  let bytesRead = 0;
  while (bytesRead < contents.length) {
    const count = readSync(
      descriptor,
      contents,
      bytesRead,
      contents.length - bytesRead,
      bytesRead,
    );
    if (count === 0) break;
    bytesRead += count;
  }
  const finalStat = fstatSync(descriptor);
  if (
    !finalStat.isFile() ||
    finalStat.size !== stat.size ||
    bytesRead !== finalStat.size ||
    bytesRead > maximum
  ) {
    throw new Error("artifact changed during read");
  }
  return contents.subarray(0, bytesRead);
}

async function readCappedFileHandle(fileHandle, stat) {
  assertTraceArchiveFileSize(stat);
  const capacity = Math.min(stat.size + 1, MAX_TRACE_ARCHIVE_BYTES + 1);
  const contents = Buffer.alloc(capacity);
  let bytesRead = 0;
  while (bytesRead < contents.length) {
    const result = await fileHandle.read(
      contents,
      bytesRead,
      contents.length - bytesRead,
      bytesRead,
    );
    if (result.bytesRead === 0) break;
    bytesRead += result.bytesRead;
  }
  const finalStat = await fileHandle.stat();
  if (
    !finalStat.isFile() ||
    finalStat.size !== stat.size ||
    bytesRead !== finalStat.size ||
    bytesRead > MAX_TRACE_ARCHIVE_BYTES
  ) {
    throw new Error("artifact changed during read");
  }
  return contents.subarray(0, bytesRead);
}

function assertTraceArchiveFileSize(stat) {
  if (!stat.isFile()) throw new Error("artifact is not a regular file");
  if (stat.size > MAX_TRACE_ARCHIVE_BYTES) {
    throw new Error(
      `trace archive exceeds maximum size of ${MAX_TRACE_ARCHIVE_BYTES} bytes`,
    );
  }
}

async function rewriteValidatedFileHandle(fileHandle, contents) {
  const stat = await fileHandle.stat();
  if (!stat.isFile()) throw new Error("artifact is not a regular file");
  const data = Buffer.from(contents);
  await fileHandle.truncate(0);
  let offset = 0;
  while (offset < data.length) {
    const { bytesWritten } = await fileHandle.write(
      data,
      offset,
      data.length - offset,
      offset,
    );
    if (bytesWritten <= 0) throw new Error("artifact rewrite made no progress");
    offset += bytesWritten;
  }
}

export function rewriteValidatedDescriptorSync(descriptor, contents) {
  const stat = fstatSync(descriptor);
  if (!stat.isFile()) throw new Error("artifact is not a regular file");
  const data = Buffer.from(contents);
  ftruncateSync(descriptor, 0);
  let offset = 0;
  while (offset < data.length) {
    const written = writeSync(
      descriptor,
      data,
      offset,
      data.length - offset,
      offset,
    );
    if (written <= 0) throw new Error("artifact rewrite made no progress");
    offset += written;
  }
}

export function sanitizeTraceArchiveBuffer(archive, sensitiveValues = []) {
  const entries = readZipEntries(archive);
  const traceEntries = entries.filter(({ name }) => TRACE_ENTRIES.test(name));
  if (!traceEntries.length) {
    throw new Error("trace archive did not contain a trace timeline");
  }
  const kept = traceEntries.map(({ name, data }) => ({
    name,
    data: Buffer.from(
      sanitizeTraceText(data.toString("utf8"), sensitiveValues),
      "utf8",
    ),
  }));
  return {
    archive: writeZipEntries(kept),
    removedEntries: entries.length - kept.length,
  };
}

export function sanitizeTraceText(text, sensitiveValues = []) {
  const lines = String(text).split(/\r?\n/u);
  const sanitized = [];
  for (const line of lines) {
    if (!line) continue;
    try {
      const event = JSON.parse(line);
      if (REMOVED_TRACE_EVENTS.has(event.type)) continue;
      sanitized.push(JSON.stringify(sanitizeTraceEvent(event, sensitiveValues)));
    } catch (error) {
      throw new Error("trace timeline contained malformed JSON", { cause: error });
    }
  }
  return sanitized.join("\n") + (sanitized.length ? "\n" : "");
}

export function redactSensitiveText(
  value,
  sensitiveValues = [],
  { truncate = true } = {},
) {
  let text = String(value);
  for (const sensitive of sensitiveValues) {
    if (sensitive) text = text.split(String(sensitive)).join("[REDACTED]");
  }
  text = text
    .replace(
      /([#?&](?:access_token|authorization|capability|credential|password|secret|token)=)[^&#\s"'`]+/giu,
      "$1[REDACTED]",
    )
    .replace(
      /\b(?:bearer|token|secret|password|capability|credential|authorization)\b\s*[:=]\s*[A-Za-z0-9._~+/=-]+/giu,
      (match) => `${match.slice(0, match.search(/[:=]/u) + 1)}[REDACTED]`,
    )
    .replace(
      /\b(?:browser-fixture(?:-token)?|simulator-token)[-_][A-Za-z0-9._~+/=-]+/giu,
      "[REDACTED]",
    )
    .replace(
      /\b(?:BROWSER_HARNESS|SYNTHETIC)_[A-Z0-9_]+\b/gu,
      "[REDACTED]",
    )
    .replace(/\bFETCH_ONLY\b/gu, "[REDACTED]")
    .replace(
      /(?:file:\/\/)?\/(?:Users\/|private\/var\/|var\/folders\/|private\/tmp\/|tmp\/)[^\s"'`]+/gu,
      "[PATH_REDACTED]",
    );
  return truncate && text.length > 512 ? `${text.slice(0, 512)}…` : text;
}

export function sanitizeTextArtifact(_text, _sensitiveValues = []) {
  return "[REDACTED]\n";
}

export function sanitizeFailureScreenshot(png) {
  const { width, height } = readPngDimensions(png);
  const rowSize = width * 4 + 1;
  const scanlines = Buffer.alloc(rowSize * height);
  for (let y = 0; y < height; y += 1) {
    const rowOffset = y * rowSize;
    scanlines[rowOffset] = 0;
    for (let x = 0; x < width; x += 1) {
      scanlines[rowOffset + 1 + x * 4 + 3] = 0xff;
    }
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8;
  ihdr[9] = 6;
  return Buffer.concat([
    PNG_SIGNATURE,
    makePngChunk(Buffer.from("IHDR", "ascii"), ihdr),
    makePngChunk(Buffer.from("IDAT", "ascii"), deflateSync(scanlines)),
    makePngChunk(Buffer.from("IEND", "ascii"), Buffer.alloc(0)),
  ]);
}

export function readPngDimensions(png) {
  if (!Buffer.isBuffer(png) || !png.subarray(0, 8).equals(PNG_SIGNATURE)) {
    throw new Error("not a PNG");
  }
  let offset = PNG_SIGNATURE.length;
  let sawHeader = false;
  let sawData = false;
  let sawEnd = false;
  let width;
  let height;
  while (offset < png.length) {
    if (offset + 12 > png.length) throw new Error("truncated PNG chunk");
    const length = png.readUInt32BE(offset);
    const dataEnd = offset + 12 + length;
    if (dataEnd > png.length) throw new Error("truncated PNG data");
    const type = png.subarray(offset + 4, offset + 8);
    const data = png.subarray(offset + 8, offset + 8 + length);
    if (crc32(Buffer.concat([type, data])) !== png.readUInt32BE(offset + 8 + length)) {
      throw new Error("PNG chunk failed CRC validation");
    }
    const typeName = type.toString("ascii");
    if (!/^[A-Za-z]{4}$/u.test(typeName)) {
      throw new Error("PNG chunk has an invalid type");
    }
    if (!sawHeader) {
      if (typeName !== "IHDR" || length !== 13) {
        throw new Error("PNG has an invalid header");
      }
      width = png.readUInt32BE(offset + 8);
      height = png.readUInt32BE(offset + 12);
      const bitDepth = data[8];
      const colorType = data[9];
      const validBitDepths = {
        0: [1, 2, 4, 8, 16],
        2: [8, 16],
        3: [1, 2, 4, 8],
        4: [8, 16],
        6: [8, 16],
      };
      if (
        width === 0 ||
        height === 0 ||
        width > MAX_FAILURE_SCREENSHOT_WIDTH ||
        height > MAX_FAILURE_SCREENSHOT_HEIGHT ||
        width * height > MAX_FAILURE_SCREENSHOT_PIXELS ||
        !validBitDepths[colorType]?.includes(bitDepth) ||
        data[10] !== 0 ||
        data[11] !== 0 ||
        ![0, 1].includes(data[12])
      ) {
        throw new Error("PNG dimensions or format are out of bounds");
      }
      sawHeader = true;
    } else if (typeName === "IDAT") {
      sawData = true;
    } else if (typeName === "IEND") {
      if (length !== 0 || dataEnd !== png.length) {
        throw new Error("invalid PNG end");
      }
      sawEnd = true;
      break;
    }
    offset = dataEnd;
  }
  if (!sawHeader || !sawData || !sawEnd) {
    throw new Error("PNG is incomplete");
  }
  return { width, height };
}

export function sanitizeErrorContext(text, sensitiveValues = []) {
  const safeLines = [];
  let inPageSnapshot = false;
  for (const line of String(text).split(/\r?\n/u)) {
    if (line.trim() === "## Page snapshot") {
      inPageSnapshot = true;
      safeLines.push("## Page snapshot\n[REDACTED]");
      continue;
    }
    if (inPageSnapshot && /^#+\s+/u.test(line)) {
      inPageSnapshot = false;
    }
    if (inPageSnapshot || !line.trim()) continue;
    if (line.trim() === "# Failure") {
      safeLines.push("# Failure");
    } else if (/^\s*error:/iu.test(line)) {
      safeLines.push("Error: [REDACTED]");
    } else if (/^\s*at\s+/u.test(line)) {
      safeLines.push("    at [REDACTED]");
    } else {
      safeLines.push("[REDACTED]");
    }
  }
  return safeLines.join("\n") + (safeLines.length ? "\n" : "");
}

function sanitizeTraceEvent(value, sensitiveValues) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("trace timeline contained an unsupported event");
  }
  if (typeof value.type !== "string" || value.type.length === 0) {
    throw new Error("trace timeline contained an unsupported event type");
  }
  const result = {};
  for (const [key, childValue] of Object.entries(value)) {
    if (
      SAFE_TRACE_STRING_KEYS.has(key) &&
      typeof childValue === "string" &&
      SAFE_TRACE_STRING_GRAMMARS.get(key)?.test(childValue)
    ) {
      result[key] = redactSensitiveText(childValue, sensitiveValues);
    } else if (SAFE_TRACE_NUMBER_KEYS.has(key) &&
               typeof childValue === "number" &&
               Number.isFinite(childValue)) {
      result[key] = childValue;
    } else if (key === "error" && childValue) {
      result[key] = "[REDACTED]";
    }
  }
  return result;
}

function readZipEntries(archive) {
  if (!Buffer.isBuffer(archive)) {
    throw new Error("trace archive must be a buffer");
  }
  if (archive.length > MAX_TRACE_ARCHIVE_BYTES) {
    throw new Error(
      `trace archive exceeds maximum size of ${MAX_TRACE_ARCHIVE_BYTES} bytes`,
    );
  }
  if (archive.length < ZIP_END_SIZE) {
    throw new Error("trace archive is too small");
  }
  const endOffset = archive.lastIndexOf(Buffer.from([0x50, 0x4b, 0x05, 0x06]));
  if (endOffset < 0 || endOffset + ZIP_END_SIZE > archive.length) {
    throw new Error("trace archive has no end record");
  }
  const commentLength = archive.readUInt16LE(endOffset + 20);
  if (commentLength !== 0 || endOffset + ZIP_END_SIZE !== archive.length) {
    throw new Error("trace archive has trailing data");
  }
  const diskNumber = archive.readUInt16LE(endOffset + 4);
  const directoryDisk = archive.readUInt16LE(endOffset + 6);
  const diskEntryCount = archive.readUInt16LE(endOffset + 8);
  const entryCount = archive.readUInt16LE(endOffset + 10);
  const directorySize = archive.readUInt32LE(endOffset + 12);
  const directoryOffset = archive.readUInt32LE(endOffset + 16);
  if (
    diskNumber !== 0 ||
    directoryDisk !== 0 ||
    diskEntryCount !== entryCount ||
    entryCount === 0 ||
    diskEntryCount === 0xffff ||
    entryCount === 0xffff ||
    directorySize === 0xffffffff ||
    directoryOffset === 0xffffffff
  ) {
    throw new Error("trace archive uses unsupported ZIP disks or ZIP64");
  }
  if (entryCount > MAX_TRACE_ENTRY_COUNT) {
    throw new Error(
      `trace archive exceeds maximum entry count of ${MAX_TRACE_ENTRY_COUNT}`,
    );
  }
  if (
    directoryOffset > endOffset ||
    directorySize > endOffset ||
    directoryOffset + directorySize !== endOffset
  ) {
    throw new Error("trace archive has an invalid central directory range");
  }

  let centralOffset = directoryOffset;
  let localOffset = 0;
  let compressedSizeTotal = 0;
  let uncompressedSizeTotal = 0;
  const records = [];
  const names = new Set();
  for (let index = 0; index < entryCount; index += 1) {
    requireBytes(archive, centralOffset, 46);
    if (archive.readUInt32LE(centralOffset) !== ZIP_CENTRAL_FILE) {
      throw new Error("trace archive has an invalid central directory");
    }
    const madeBy = archive.readUInt16LE(centralOffset + 4);
    const versionNeeded = archive.readUInt16LE(centralOffset + 6);
    const flags = archive.readUInt16LE(centralOffset + 8);
    const method = archive.readUInt16LE(centralOffset + 10);
    const modifiedTime = archive.readUInt16LE(centralOffset + 12);
    const modifiedDate = archive.readUInt16LE(centralOffset + 14);
    const crc = archive.readUInt32LE(centralOffset + 16);
    const compressedSize = archive.readUInt32LE(centralOffset + 20);
    const uncompressedSize = archive.readUInt32LE(centralOffset + 24);
    const nameLength = archive.readUInt16LE(centralOffset + 28);
    const extraLength = archive.readUInt16LE(centralOffset + 30);
    const entryCommentLength = archive.readUInt16LE(centralOffset + 32);
    const entryDisk = archive.readUInt16LE(centralOffset + 34);
    const internalAttributes = archive.readUInt16LE(centralOffset + 36);
    const externalAttributes = archive.readUInt32LE(centralOffset + 38);
    const entryLocalOffset = archive.readUInt32LE(centralOffset + 42);
    const centralEnd =
      centralOffset + 46 + nameLength + extraLength + entryCommentLength;
    requireBytes(archive, centralOffset, centralEnd - centralOffset);
    const centralName = archive.subarray(
      centralOffset + 46,
      centralOffset + 46 + nameLength,
    );
    const centralExtra = archive.subarray(
      centralOffset + 46 + nameLength,
      centralOffset + 46 + nameLength + extraLength,
    );
    if (
      versionNeeded !== ZIP_VERSION ||
      !isSupportedZipFlags(flags) ||
      !isSupportedZipMethod(method) ||
      entryCommentLength !== 0 ||
      entryDisk !== 0 ||
      internalAttributes !== 0 ||
      !isSupportedCentralMetadata(madeBy, externalAttributes) ||
      entryLocalOffset !== localOffset ||
      uncompressedSize > MAX_TRACE_ENTRY_BYTES ||
      compressedSize > MAX_TRACE_ENTRY_BYTES
    ) {
      throw new Error("trace archive has an unsupported entry schema");
    }
    compressedSizeTotal += compressedSize;
    uncompressedSizeTotal += uncompressedSize;
    if (compressedSizeTotal > MAX_TRACE_COMPRESSED_BYTES) {
      throw new Error(
        `trace archive exceeds maximum compressed size of ${MAX_TRACE_COMPRESSED_BYTES} bytes`,
      );
    }
    if (uncompressedSizeTotal > MAX_TRACE_UNCOMPRESSED_BYTES) {
      throw new Error(
        `trace archive exceeds maximum uncompressed size of ${MAX_TRACE_UNCOMPRESSED_BYTES} bytes`,
      );
    }
    if (!isSupportedCentralExtra(centralExtra)) {
      throw new Error("trace archive has an unsupported central extra field");
    }
    const name = decodeZipName(centralName, flags);
    if (!isAllowedTraceEntry(name) || names.has(name)) {
      throw new Error("trace archive has an unexpected entry");
    }
    names.add(name);

    requireBytes(archive, entryLocalOffset, 30);
    if (archive.readUInt32LE(entryLocalOffset) !== ZIP_LOCAL_FILE) {
      throw new Error("trace archive has an invalid local file");
    }
    const localVersionNeeded = archive.readUInt16LE(entryLocalOffset + 4);
    const localFlags = archive.readUInt16LE(entryLocalOffset + 6);
    const localMethod = archive.readUInt16LE(entryLocalOffset + 8);
    const localModifiedTime = archive.readUInt16LE(entryLocalOffset + 10);
    const localModifiedDate = archive.readUInt16LE(entryLocalOffset + 12);
    const localCrc = archive.readUInt32LE(entryLocalOffset + 14);
    const localCompressedSize = archive.readUInt32LE(entryLocalOffset + 18);
    const localUncompressedSize = archive.readUInt32LE(entryLocalOffset + 22);
    const localNameLength = archive.readUInt16LE(entryLocalOffset + 26);
    const localExtraLength = archive.readUInt16LE(entryLocalOffset + 28);
    const localEnd = entryLocalOffset + 30 + localNameLength + localExtraLength;
    requireBytes(archive, entryLocalOffset, localEnd - entryLocalOffset);
    const localName = archive.subarray(
      entryLocalOffset + 30,
      entryLocalOffset + 30 + localNameLength,
    );
    const localExtra = archive.subarray(
      entryLocalOffset + 30 + localNameLength,
      localEnd,
    );
    if (
      localVersionNeeded !== versionNeeded ||
      localFlags !== flags ||
      localMethod !== method ||
      localModifiedTime !== modifiedTime ||
      localModifiedDate !== modifiedDate ||
      !localName.equals(centralName) ||
      localExtraLength !== 0 ||
      localExtra.length !== 0
    ) {
      throw new Error("trace archive local and central records differ");
    }
    const usesDataDescriptor = (flags & ZIP_DATA_DESCRIPTOR_FLAG) !== 0;
    if (
      usesDataDescriptor
        ? localCrc !== 0 ||
          localCompressedSize !== 0 ||
          localUncompressedSize !== 0
        : localCrc !== crc ||
          localCompressedSize !== compressedSize ||
          localUncompressedSize !== uncompressedSize
    ) {
      throw new Error("trace archive local and central records differ");
    }
    const dataStart = localEnd;
    const dataEnd = dataStart + compressedSize;
    if (
      dataStart < localOffset ||
      dataEnd < dataStart ||
      dataEnd > directoryOffset
    ) {
      throw new Error("trace archive has an invalid data range");
    }
    let nextOffset = dataEnd;
    if (usesDataDescriptor) {
      requireBytes(archive, dataEnd, 16);
      if (
        archive.readUInt32LE(dataEnd) !== ZIP_DATA_DESCRIPTOR ||
        archive.readUInt32LE(dataEnd + 4) !== crc ||
        archive.readUInt32LE(dataEnd + 8) !== compressedSize ||
        archive.readUInt32LE(dataEnd + 12) !== uncompressedSize
      ) {
        throw new Error("trace archive has an invalid data descriptor");
      }
      nextOffset += 16;
    }
    records.push({
      name,
      method,
      crc,
      compressedSize,
      uncompressedSize,
      dataStart,
      dataEnd,
    });
    localOffset = nextOffset;
    centralOffset = centralEnd;
  }
  if (centralOffset !== endOffset || localOffset !== directoryOffset) {
    throw new Error("trace archive has inconsistent offsets");
  }

  return records.map((record) => {
    const compressed = archive.subarray(record.dataStart, record.dataEnd);
    let data;
    try {
      if (record.method === ZIP_METHOD_STORE) {
        if (record.compressedSize !== record.uncompressedSize) {
          throw new Error("stored entry sizes differ");
        }
        data = compressed;
      } else {
        const inflated = inflateRawSync(compressed, {
          info: true,
          maxOutputLength: Math.max(1, record.uncompressedSize),
        });
        if (inflated.engine.bytesWritten !== record.compressedSize) {
          throw new Error("deflated entry has trailing data");
        }
        data = inflated.buffer;
      }
    } catch (error) {
      throw new Error("trace archive entry failed decompression", { cause: error });
    }
    if (
      data.length !== record.uncompressedSize ||
      crc32(data) !== record.crc
    ) {
      throw new Error("trace archive entry failed integrity validation");
    }
    return { name: record.name, data };
  });
}

function requireBytes(buffer, offset, length) {
  if (
    !Number.isSafeInteger(offset) ||
    !Number.isSafeInteger(length) ||
    offset < 0 ||
    length < 0 ||
    offset + length > buffer.length
  ) {
    throw new Error("trace archive has a truncated record");
  }
}

function isSupportedZipFlags(flags) {
  return flags === 0 ||
    flags === ZIP_UTF8_FLAG ||
    flags === (ZIP_UTF8_FLAG | ZIP_DATA_DESCRIPTOR_FLAG);
}

function decodeZipName(bytes, flags) {
  if (bytes.includes(0)) throw new Error("trace archive has an invalid entry name");
  try {
    const name = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    if ((flags & ZIP_UTF8_FLAG) === 0 && /[^\x00-\x7f]/u.test(name)) {
      throw new Error("non-UTF-8 ZIP names require the UTF-8 flag");
    }
    return name;
  } catch (error) {
    throw new Error("trace archive has an invalid entry name", { cause: error });
  }
}

function isAllowedTraceEntry(name) {
  return TRACE_ENTRIES.test(name) ||
    TRACE_NETWORK_ENTRIES.test(name) ||
    TRACE_STACK_ENTRIES.test(name) ||
    SOURCE_ENTRIES.test(name) ||
    ATTACHMENT_ENTRIES.test(name) ||
    SCREENCAST_ENTRIES.test(name) ||
    SCREENSHOT_ENTRIES.test(name) ||
    ARIA_ENTRIES.test(name) ||
    RESOURCE_ENTRIES.test(name);
}

function isSupportedZipMethod(method) {
  return method === ZIP_METHOD_STORE || method === ZIP_METHOD_DEFLATE;
}

function isSupportedCentralMetadata(madeBy, externalAttributes) {
  const creatorSystem = madeBy >>> 8;
  const creatorVersion = madeBy & 0xff;
  if (
    creatorSystem === 0 &&
    creatorVersion === ZIP_VERSION &&
    externalAttributes === 0
  ) {
    return true;
  }
  if (
    creatorSystem === 3 &&
    creatorVersion === ZIP_VERSION &&
    externalAttributes === 0x01800000
  ) {
    return true;
  }
  if (creatorSystem !== 3 || creatorVersion !== 63) return false;
  const unixMode = externalAttributes >>> 16;
  const dosAttributes = externalAttributes & 0xffff;
  return dosAttributes === 0 &&
    (unixMode & 0xf000) === 0x8000 &&
    (unixMode & 0x0fff) <= 0o777;
}

function isSupportedCentralExtra(extra) {
  if (extra.length === 0) return true;
  return extra.length === 9 &&
    extra.readUInt16LE(0) === 0x5455 &&
    extra.readUInt16LE(2) === 5 &&
    extra[4] === 0x03;
}

function writeZipEntries(entries) {
  const localParts = [];
  const centralParts = [];
  let offset = 0;
  for (const entry of entries) {
    const name = Buffer.from(entry.name, "utf8");
    const compressed = deflateRawSync(entry.data);
    const crc = crc32(entry.data);
    const local = Buffer.alloc(30 + name.length);
    local.writeUInt32LE(ZIP_LOCAL_FILE, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt16LE(0, 6);
    local.writeUInt16LE(ZIP_METHOD_DEFLATE, 8);
    local.writeUInt16LE(0, 10);
    local.writeUInt16LE(0, 12);
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(compressed.length, 18);
    local.writeUInt32LE(entry.data.length, 22);
    local.writeUInt16LE(name.length, 26);
    local.writeUInt16LE(0, 28);
    name.copy(local, 30);
    localParts.push(local, compressed);

    const central = Buffer.alloc(46 + name.length);
    central.writeUInt32LE(ZIP_CENTRAL_FILE, 0);
    central.writeUInt16LE(20, 4);
    central.writeUInt16LE(20, 6);
    central.writeUInt16LE(0, 8);
    central.writeUInt16LE(ZIP_METHOD_DEFLATE, 10);
    central.writeUInt16LE(0, 12);
    central.writeUInt16LE(0, 14);
    central.writeUInt32LE(crc, 16);
    central.writeUInt32LE(compressed.length, 20);
    central.writeUInt32LE(entry.data.length, 24);
    central.writeUInt16LE(name.length, 28);
    central.writeUInt16LE(0, 30);
    central.writeUInt16LE(0, 32);
    central.writeUInt16LE(0, 34);
    central.writeUInt16LE(0, 36);
    central.writeUInt32LE(0, 38);
    central.writeUInt32LE(offset, 42);
    name.copy(central, 46);
    centralParts.push(central);
    offset += local.length + compressed.length;
  }
  const central = Buffer.concat(centralParts);
  const local = Buffer.concat(localParts);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(ZIP_END, 0);
  end.writeUInt16LE(0, 4);
  end.writeUInt16LE(0, 6);
  end.writeUInt16LE(entries.length, 8);
  end.writeUInt16LE(entries.length, 10);
  end.writeUInt32LE(central.length, 12);
  end.writeUInt32LE(local.length, 16);
  return Buffer.concat([local, central, end]);
}

function makePngChunk(type, data) {
  const chunk = Buffer.alloc(12 + data.length);
  chunk.writeUInt32BE(data.length, 0);
  type.copy(chunk, 4);
  data.copy(chunk, 8);
  chunk.writeUInt32BE(crc32(Buffer.concat([type, data])), 8 + data.length);
  return chunk;
}

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) {
      crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
    }
  }
  return (crc ^ 0xffffffff) >>> 0;
}
