import { expect, test } from "@playwright/test";
import {
  chmod,
  mkdtemp,
  mkdir,
  open as openFile,
  readFile,
  readdir,
  rm,
  symlink,
  writeFile,
} from "node:fs/promises";
import { closeSync, fstatSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { deflateRawSync } from "node:zlib";
import FailureArtifactsReporter, {
  OWNERSHIP_FAILURE_MESSAGE,
} from "./failure_artifacts_reporter.mjs";
import {
  MAX_TRACE_ARCHIVE_BYTES,
  MAX_TRACE_ENTRY_BYTES,
  MAX_TRACE_UNCOMPRESSED_BYTES,
  redactSensitiveText,
  openValidatedFileDescriptorSync,
  readValidatedDescriptorSync,
  rewriteValidatedDescriptorSync,
  sanitizeErrorContext,
  sanitizeFailureScreenshot,
  sanitizeTraceArchiveBuffer,
  sanitizeTraceArchive,
  sanitizeTraceArchiveSync,
  sanitizeTraceText,
  readPngDimensions,
} from "./failure_artifacts.mjs";

test("redacts trace content while retaining the action timeline", () => {
  const trace = [
    {
      type: "before",
      callId: "call-1",
      class: "Page",
      method: "locator",
      params: {
        url: "http://127.0.0.1:1234/#token=browser-fixture-secret",
        text: "candidate source sentinel",
        selector: "SELECTOR_SENTINEL",
        prompt: "PROMPT_SENTINEL",
        reference: "REFERENCE_SENTINEL",
        postDataJSON: "POST_DATA_SENTINEL",
        metadata: { arbitrary: "METADATA_SENTINEL" },
        plain: "FETCH_ONLY",
      },
    },
    {
      type: "screenshot",
      callId: "call-1",
      file: "screenshots/call-1-after.png",
    },
    {
      type: "after",
      callId: "call-1",
      error: { message: "prompt sentinel", stack: "/tmp/private.js:1" },
    },
  ].map((event) => JSON.stringify(event)).join("\n");

  const safe = sanitizeTraceText(trace);

  expect(safe).toContain('"type":"before"');
  expect(safe).toContain('"type":"after"');
  expect(safe).not.toContain("candidate source sentinel");
  expect(safe).not.toContain("prompt sentinel");
  for (const forbidden of [
    "SELECTOR_SENTINEL",
    "PROMPT_SENTINEL",
    "REFERENCE_SENTINEL",
    "POST_DATA_SENTINEL",
    "METADATA_SENTINEL",
    "FETCH_ONLY",
  ]) {
    expect(safe).not.toContain(forbidden);
  }
  expect(safe).not.toContain('"selector"');
  expect(safe).not.toContain('"prompt"');
  expect(safe).not.toContain('"reference"');
  expect(safe).not.toContain('"postDataJSON"');
  expect(safe).not.toContain('"metadata"');
  expect(safe).not.toContain("browser-fixture-secret");
  expect(safe).not.toContain("/tmp/private.js");
  expect(safe).not.toContain("screenshot");
  expect(redactSensitiveText("/Users/private/source.py")).toBe("[PATH_REDACTED]");
  const safeContext = sanitizeErrorContext(
    "# Failure\nError: prompt and source content\n" +
      "## Page snapshot\nSYNTHETIC_CANDIDATE_SOURCE_SENTINEL\n",
  );
  expect(safeContext).toContain("Error: [REDACTED]");
  expect(safeContext).not.toContain("SYNTHETIC_CANDIDATE_SOURCE_SENTINEL");
});

test("rewrites a trace archive while retaining only its action timeline", async () => {
  const root = await mkdtemp(join(tmpdir(), "failure-artifacts-unit-"));
  const archivePath = join(root, "trace.zip");
  try {
    const createArchive = spawnSync("python3", [
      "-c",
      `
import json
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1], "w", zipfile.ZIP_DEFLATED) as archive:
    archive.writestr("trace.trace", "\\n".join([
        json.dumps({"type": "before", "params": {"content": "candidate sentinel"}}),
        json.dumps({"type": "after", "error": {"message": "failure sentinel"}}),
    ]))
`,
      archivePath,
    ], { encoding: "utf8" });
    if (createArchive.status !== 0) throw new Error(createArchive.stderr);

    sanitizeTraceArchiveSync(archivePath);
    const inspection = spawnSync("python3", [
      "-c",
      `
import json
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1]) as archive:
    print(json.dumps({
        "names": archive.namelist(),
        "trace": archive.read("trace.trace").decode(),
    }))
`,
      archivePath,
    ], { encoding: "utf8" });
    if (inspection.status !== 0) throw new Error(inspection.stderr);
    const result = JSON.parse(inspection.stdout);
    expect(result.names).toEqual(["trace.trace"]);
    expect(result.trace).toContain('"type":"before"');
    expect(result.trace).toContain("[REDACTED]");
    expect(result.trace).not.toContain("candidate sentinel");
    expect(result.trace).not.toContain("failure sentinel");
  } finally {
    await rm(root, { recursive: true, force: true });
  }
  expect(await readFile(archivePath).catch(() => undefined)).toBeUndefined();
});

test("sanitizer synchronously precedes observers with rewritten failures", async () => {
  const root = await mkdtemp(join(tmpdir(), "failure-artifacts-order-"));
  const tracePath = join(root, "trace.zip");
  const sentinel = "ORDERING_RAW_TRACE_SENTINEL";
  try {
    const createArchive = spawnSync("python3", [
      "-c",
      `
import json
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1], "w", zipfile.ZIP_DEFLATED) as archive:
    archive.writestr("trace.trace", json.dumps({
        "type": "before",
        "callId": "ordering-call",
        "params": {"raw": sys.argv[2]},
    }))
`,
      tracePath,
      sentinel,
    ], { encoding: "utf8" });
    if (createArchive.status !== 0) throw new Error(createArchive.stderr);

    const result = {
      status: "failed",
      errors: [{
        name: "CandidateError",
        message: "ORDERING_RAW_ERROR_SENTINEL",
      }, {
        name: "Error",
        message: "ORDERING_SECOND_ERROR_SENTINEL",
      }],
      error: {
        name: "CandidateError",
        message: "ORDERING_RAW_RESULT_ERROR_SENTINEL",
      },
      attachments: [{
        name: "trace",
        contentType: "application/zip",
        path: tracePath,
      }, {
        name: "stdout",
        contentType: "text/plain",
        body: "ORDERING_RAW_ATTACHMENT_SENTINEL",
      }],
    };
    const observations = [];
    const observer = {
      onTestEnd(_test, observedResult) {
        const inspection = spawnSync("python3", [
          "-c",
          `
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1]) as archive:
    print(archive.read("trace.trace").decode())
`,
          tracePath,
        ], { encoding: "utf8" });
        observations.push({
          error: observedResult.error,
          errors: observedResult.errors,
          attachmentNames: observedResult.attachments.map(({ name }) => name),
          stdout: observedResult.attachments.find(
              ({ name }) => name == "stdout"
          ).body,
          traceStatus: inspection.status,
          traceText: inspection.stdout,
        });
      },
    };

    const returned = runReporter(result, root);
    expect(returned).toBeUndefined();
    observer.onTestEnd({}, result);

    expect(observations).toHaveLength(1);
    expect(observations[0].error).toBe(observations[0].errors[0]);
    expect(observations[0].errors).toEqual([{
      name: "Error",
      message: "Test failed; inspect sanitized artifacts.",
    }, {
      name: "Error",
      message: "Test failed; inspect sanitized artifacts.",
    }]);
    expect(observations[0].attachmentNames).toEqual(["trace", "stdout"]);
    expect(observations[0].stdout).toBe("[REDACTED]\n");
    expect(observations[0].traceStatus).toBe(0);
    expect(observations[0].traceText).toContain('"type":"before"');
    expect(observations[0].traceText).not.toContain(sentinel);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("accepts Playwright trace families and emits only sanitized timelines", async () => {
  const root = await mkdtemp(join(tmpdir(), "failure-artifacts-playwright-"));
  const archivePath = join(root, "trace.zip");
  const traceName = "trace.trace";
  const callId = "call@123";
  try {
    const archive = createPlaywrightArchive([
      {
        name: traceName,
        data: Buffer.from(
          [
            JSON.stringify({
              type: "before",
              callId,
              startTime: 123.45,
              class: "Page",
              method: "goto",
              parentId: "call@99",
              params: {
                url: "https://example.test",
                prompt: "PROMPT_SHOULD_NOT_SURVIVE",
                source: "/Users/private/source.js",
              },
            }),
            JSON.stringify({
              type: "input",
              callId,
              point: { x: 1, y: 2 },
              box: { x: 0, y: 0, width: 10, height: 10 },
            }),
            JSON.stringify({
              type: "after",
              callId,
              endTime: 124.56,
            }),
            "",
          ].join("\n"),
        ),
      },
      { name: "trace.network", data: Buffer.from("{}\n") },
      { name: "trace.stacks", data: Buffer.from("[]") },
      {
        name: `resources/${"a".repeat(40)}`,
        data: Buffer.from("resource"),
      },
      {
        name: `src/${"b".repeat(40)}.ts`,
        data: Buffer.from("source"),
      },
      {
        name: `attachments/${"c".repeat(40)}`,
        data: Buffer.from("attachment"),
      },
      {
        name: `screencast/page@${"d".repeat(32)}-123.jpeg`,
        data: Buffer.from("screencast"),
      },
      {
        name: `screenshots/${callId}-before.png`,
        data: Buffer.from("screenshot"),
      },
      {
        name: `aria/${callId}-after.json`,
        data: Buffer.from("{}"),
      },
    ]);
    await writeFile(archivePath, archive);

    const sanitized = sanitizeTraceArchiveBuffer(archive);
    await writeFile(archivePath, sanitized.archive);
    const inspection = spawnSync("python3", [
      "-c",
      `
import json
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1]) as archive:
    print(json.dumps({
        "names": archive.namelist(),
        "trace": archive.read(sys.argv[2]).decode(),
    }))
`,
      archivePath,
      traceName,
    ], { encoding: "utf8" });
    if (inspection.status !== 0) throw new Error(inspection.stderr);
    const result = JSON.parse(inspection.stdout);
    expect(result.names).toEqual([traceName]);
    expect(result.trace).toContain('"type":"before"');
    expect(result.trace).toContain(`"callId":"${callId}"`);
    expect(result.trace).toContain('"parentId":"call@99"');
    expect(result.trace).not.toContain("PROMPT_SHOULD_NOT_SURVIVE");
    expect(result.trace).not.toContain("/Users/private/source.js");
    expect(sanitized.removedEntries).toBe(8);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

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

function createPlaywrightArchive(entries) {
  const localParts = [];
  const centralParts = [];
  const centralExtra = Buffer.from([
    0x55, 0x54, 0x05, 0x00, 0x03, 0x00, 0x00, 0x00, 0x00,
  ]);
  let offset = 0;

  for (const entry of entries) {
    const name = Buffer.from(entry.name, "utf8");
    const data = Buffer.from(entry.data);
    const compressed = deflateRawSync(data);
    const crc = crc32(data);
    const local = Buffer.alloc(30 + name.length);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt16LE(0x0808, 6);
    local.writeUInt16LE(8, 8);
    local.writeUInt32LE(0, 14);
    local.writeUInt32LE(0, 18);
    local.writeUInt32LE(0, 22);
    local.writeUInt16LE(name.length, 26);
    name.copy(local, 30);
    const descriptor = Buffer.alloc(16);
    descriptor.writeUInt32LE(0x08074b50, 0);
    descriptor.writeUInt32LE(crc, 4);
    descriptor.writeUInt32LE(compressed.length, 8);
    descriptor.writeUInt32LE(data.length, 12);
    localParts.push(local, compressed, descriptor);

    const central = Buffer.alloc(46 + name.length + centralExtra.length);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE(0x033f, 4);
    central.writeUInt16LE(20, 6);
    central.writeUInt16LE(0x0808, 8);
    central.writeUInt16LE(8, 10);
    central.writeUInt32LE(crc, 16);
    central.writeUInt32LE(compressed.length, 20);
    central.writeUInt32LE(data.length, 24);
    central.writeUInt16LE(name.length, 28);
    central.writeUInt16LE(centralExtra.length, 30);
    central.writeUInt32LE(0x81a40000, 38);
    central.writeUInt32LE(offset, 42);
    name.copy(central, 46);
    centralExtra.copy(central, 46 + name.length);
    centralParts.push(central);
    offset += local.length + compressed.length + descriptor.length;
  }

  const local = Buffer.concat(localParts);
  const central = Buffer.concat(centralParts);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(entries.length, 8);
  end.writeUInt16LE(entries.length, 10);
  end.writeUInt32LE(central.length, 12);
  end.writeUInt32LE(local.length, 16);
  return Buffer.concat([local, central, end]);
}

test("sanitizes inline text and trace bodies and drops unsupported attachments", async () => {
  const root = await mkdtemp(join(tmpdir(), "failure-artifacts-inline-"));
  const tracePath = join(root, "trace.zip");
  const unsupportedPath = join(root, "raw.bin");
  try {
    const createArchive = spawnSync("python3", [
      "-c",
      `
import json
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1], "w", zipfile.ZIP_DEFLATED) as archive:
    archive.writestr("trace.trace", json.dumps({
        "type": "before",
        "callId": "call-inline",
        "params": {"prompt": "SYNTHETIC_PROMPT_CONTENT_SENTINEL"},
    }))
`,
      tracePath,
    ], { encoding: "utf8" });
    if (createArchive.status !== 0) throw new Error(createArchive.stderr);
    await writeFile(unsupportedPath, "RAW_ATTACHMENT_SENTINEL", "utf8");

    const result = {
      status: "failed",
      attachments: [
        {
          name: "stdout",
          contentType: "text/plain",
          body: JSON.stringify({ prompt: "SYNTHETIC_PROMPT_CONTENT_SENTINEL" }),
        },
        {
          name: "trace",
          contentType: "application/zip",
          body: await readFile(tracePath),
        },
        {
          name: "raw-binary",
          contentType: "application/octet-stream",
          body: Buffer.from("RAW_INLINE_SENTINEL"),
          path: unsupportedPath,
        },
      ],
    };
    runReporter(result, root);

    expect(result.attachments).toHaveLength(2);
    expect(result.attachments[0].body.toString()).toBe("[REDACTED]\n");
    const sanitizedTracePath = join(root, "sanitized-trace.zip");
    await writeFile(sanitizedTracePath, result.attachments[1].body);
    const inspection = spawnSync("python3", [
      "-c",
      `
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1]) as archive:
    print(archive.read("trace.trace").decode())
`,
      sanitizedTracePath,
    ], { encoding: "utf8" });
    expect(inspection.status).toBe(0);
    expect(inspection.stdout).toContain('"type":"before"');
    expect(inspection.stdout).not.toContain("SYNTHETIC_PROMPT_CONTENT_SENTINEL");
    expect(await readFile(unsupportedPath, "utf8")).toBe("[REDACTED]\n");
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("fails closed for arbitrary errors and generic text artifacts", async () => {
  const root = await mkdtemp(join(tmpdir(), "failure-artifacts-closed-"));
  const stderrPath = join(root, "stderr");
  const resultPath = join(root, "result.json");
  const textPath = join(root, "notes.txt");
  const candidateText = "candidate private prompt source plaintext should not survive";
  try {
    await writeFile(stderrPath, candidateText, "utf8");
    await writeFile(resultPath, JSON.stringify({ unknownKey: candidateText }), "utf8");
    await writeFile(textPath, candidateText, "utf8");
    const result = {
      status: "failed",
      errors: [{
        name: "CandidateError",
        message: candidateText,
        value: candidateText,
        snippet: candidateText,
        expected: candidateText,
        actual: candidateText,
        stack: `CandidateError: ${candidateText}\n    at /Users/private/source.py:1:2`,
        location: {
          file: `/Users/private/${candidateText}.py`,
          line: 17,
          column: 3,
        },
      }],
      attachments: [
        {
          name: "stdout",
          contentType: "text/plain",
          body: candidateText,
        },
        {
          name: "stderr",
          contentType: "text/plain",
          path: stderrPath,
        },
        {
          name: "result.json",
          contentType: "application/json",
          path: resultPath,
        },
        {
          name: "notes.txt",
          contentType: "text/plain",
          path: textPath,
        },
        {
          name: "unknown",
          contentType: "text/plain",
          body: candidateText,
        },
      ],
    };

    runReporter(result, root);

    expect(result.errors).toEqual([{
      message: "Test failed; inspect sanitized artifacts.",
      name: "Error",
      location: { line: 17, column: 3 },
    }]);
    expect(JSON.stringify(result)).not.toContain(candidateText);
    expect(result.attachments).toHaveLength(4);
    expect(result.attachments[0].body).toBe("[REDACTED]\n");
    expect(await readFile(stderrPath, "utf8")).toBe("[REDACTED]\n");
    expect(await readFile(resultPath, "utf8")).toBe("[REDACTED]\n");
    expect(await readFile(textPath, "utf8")).toBe("[REDACTED]\n");
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("redacts malformed trace attachments instead of retaining raw data", async () => {
  const root = await mkdtemp(join(tmpdir(), "failure-artifacts-malformed-"));
  const tracePath = join(root, "trace.zip");
  try {
    await writeFile(tracePath, "MALFORMED_TRACE_SENTINEL", "utf8");
    const result = {
      status: "failed",
      attachments: [{
        name: "trace",
        contentType: "application/zip",
        path: tracePath,
      }],
    };
    runReporter(result, root);
    expect(result.attachments).toEqual([]);
    expect(await readFile(tracePath, "utf8")).toBe("[REDACTED]\n");
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("replaces every failure output stream representation before observers", () => {
  const sentinels = [
    "STREAM_PROMPT_SENTINEL",
    "STREAM_SOURCE_SENTINEL",
    "STREAM_TOKEN_SENTINEL",
    "/home/runner/private/source.py",
    "relative/source.py",
  ];
  const result = {
    status: "failed",
    stdout: [
      `prompt ${sentinels[0]}`,
      Buffer.from(`source ${sentinels[1]}`),
      new Uint8Array(Buffer.from(`token ${sentinels[2]}`)),
      { arbitrary: sentinels.join(" ") },
    ],
    stderr: Buffer.from(`path ${sentinels[3]} ${sentinels[4]}`),
    errors: [],
    attachments: [],
  };

  runReporter(result);

  expect(result.stdout).toHaveLength(4);
  expect(result.stdout[0]).toBe("[REDACTED]\n");
  expect(Buffer.isBuffer(result.stdout[1])).toBe(true);
  expect(result.stdout[2]).toBeInstanceOf(Uint8Array);
  expect(result.stdout[3]).toBe("[REDACTED]\n");
  expect(result.stderr.toString()).toBe("[REDACTED]\n");
  for (const sentinel of sentinels) {
    expect(JSON.stringify(result)).not.toContain(sentinel);
  }
});

test("sanitizes an in-memory failure screenshot without a pathname", () => {
  const png = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
    "base64",
  );
  const result = {
    status: "failed",
    attachments: [{
      name: "sanitized-failure-screenshot",
      contentType: "image/png",
      body: png,
    }],
  };

  runReporter(result);

  expect(result.attachments).toHaveLength(1);
  expect(result.attachments[0].path).toBeUndefined();
  expect(result.attachments[0].body).toEqual(sanitizeFailureScreenshot(png));
});

test("drops an attachment when its inline screenshot sanitizer fails", () => {
  const result = {
    status: "failed",
    attachments: [{
      name: "sanitized-failure-screenshot",
      contentType: "image/png",
      body: Buffer.from("not a png"),
    }],
  };

  runReporter(result);

  expect(result.attachments).toEqual([]);
});

test("sanitizes output streams before observers even for non-failure results", () => {
  const result = {
    status: "passed",
    stdout: [{ text: "PASSED_PROMPT_SENTINEL" }],
    stderr: ["PASSED_SOURCE_SENTINEL"],
    attachments: [],
  };
  const observed = [];
  const observer = {
    onTestEnd(_test, observedResult) {
      observed.push({
        stdout: observedResult.stdout,
        stderr: observedResult.stderr,
      });
    },
  };

  runReporter(result);
  observer.onTestEnd({}, result);

  expect(observed).toEqual([{
    stdout: ["[REDACTED]\n"],
    stderr: ["[REDACTED]\n"],
  }]);
  expect(JSON.stringify(observed)).not.toContain("PASSED_PROMPT_SENTINEL");
  expect(JSON.stringify(observed)).not.toContain("PASSED_SOURCE_SENTINEL");
});

test("replaces arbitrary forged PNGs and former-secret markers", async () => {
  const root = await mkdtemp(join(tmpdir(), "failure-artifacts-screenshot-"));
  const screenshotPath = join(root, "sanitized-failure-screenshot.png");
  const png = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
    "base64",
  );
  const formerSecret = Buffer.from(
    "codesignal-practice-simulator-sanitized-failure-screenshot-v1",
  );
  const forged = insertPngChunk(png, "cSig", formerSecret);
  try {
    await writeFile(screenshotPath, forged);
    const result = {
      status: "failed",
      attachments: [{
        name: "sanitized-failure-screenshot",
        contentType: "image/png",
        path: screenshotPath,
      }],
    };

    runReporter(result, root);

    expect(result.attachments).toHaveLength(1);
    const sanitized = await readFile(screenshotPath);
    expect(readPngDimensions(sanitized)).toEqual(readPngDimensions(forged));
    expect(sanitized).toEqual(sanitizeFailureScreenshot(forged));
    expect(sanitized.includes(formerSecret)).toBe(false);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("acquires and sanitizes a brand-new output root", async () => {
  const parent = await mkdtemp(join(tmpdir(), "failure-artifacts-first-run-"));
  const outputRoot = join(parent, "new", "playwright-output");
  const originalPath = join(outputRoot, "synthetic.txt");
  const reporter = new FailureArtifactsReporter();
  try {
    reporter.onBegin({ outputDir: outputRoot, projects: [] });
    expect(reporter.outputRoots).toHaveLength(1);
    expect(fstatSync(reporter.outputRoots[0].descriptor).isDirectory()).toBe(true);

    await writeFile(originalPath, "FIRST_RUN_RAW_SENTINEL", "utf8");
    expect(reporter.onEnd({})).toBeUndefined();
    expect(await readFile(originalPath, "utf8")).toBe("[REDACTED]\n");
  } finally {
    await rm(parent, { recursive: true, force: true });
  }
});

test("fails safely instead of acquiring an output root through a symlink", async () => {
  const parent = await mkdtemp(join(tmpdir(), "failure-artifacts-symlink-root-"));
  const outside = await mkdtemp(join(tmpdir(), "failure-artifacts-symlink-outside-"));
  const ownedOutputRoot = join(parent, "owned", "playwright-output");
  try {
    await symlink(outside, join(parent, "linked"));
    const terminationMessages = [];
    const reporter = new FailureArtifactsReporter({
      terminate: (message) => terminationMessages.push(message),
    });
    expect(() => reporter.onBegin({
      outputDir: ownedOutputRoot,
      projects: [{ outputDir: join(parent, "linked", "playwright-output") }],
    })).toThrow(OWNERSHIP_FAILURE_MESSAGE);
    expect(terminationMessages).toEqual([OWNERSHIP_FAILURE_MESSAGE]);
    expect(reporter.outputRoots).toEqual([]);
    expect(await readdir(ownedOutputRoot)).toEqual([]);
    expect(await readdir(outside)).toEqual([]);
  } finally {
    await rm(parent, { recursive: true, force: true });
    await rm(outside, { recursive: true, force: true });
  }
});

test("drops out-of-root artifact paths without mutating them", async () => {
  const outputRoot = await mkdtemp(join(tmpdir(), "failure-artifacts-root-"));
  const outsideRoot = await mkdtemp(join(tmpdir(), "failure-artifacts-outside-"));
  const screenshotPath = join(outsideRoot, "screenshot.png");
  const original = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
    "base64",
  );
  try {
    await writeFile(screenshotPath, original);
    const result = {
      status: "failed",
      attachments: [{
        name: "sanitized-failure-screenshot",
        contentType: "image/png",
        path: screenshotPath,
      }],
    };

    runReporter(result, outputRoot);

    expect(result.attachments).toEqual([]);
    expect(await readFile(screenshotPath)).toEqual(original);
  } finally {
    await rm(outputRoot, { recursive: true, force: true });
    await rm(outsideRoot, { recursive: true, force: true });
  }
});

test("drops symlinked artifact paths without mutating the target", async () => {
  const outputRoot = await mkdtemp(join(tmpdir(), "failure-artifacts-root-"));
  const outsideRoot = await mkdtemp(join(tmpdir(), "failure-artifacts-outside-"));
  const targetPath = join(outsideRoot, "screenshot.png");
  const symlinkPath = join(outputRoot, "screenshot.png");
  const original = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
    "base64",
  );
  try {
    await writeFile(targetPath, original);
    await symlink(targetPath, symlinkPath);
    const result = {
      status: "failed",
      attachments: [{
        name: "sanitized-failure-screenshot",
        contentType: "image/png",
        path: symlinkPath,
      }],
    };

    runReporter(result, outputRoot);

    expect(result.attachments).toEqual([]);
    expect(await readFile(targetPath)).toEqual(original);
    expect(await readFile(symlinkPath).catch(() => undefined)).toBeUndefined();
  } finally {
    await rm(outputRoot, { recursive: true, force: true });
    await rm(outsideRoot, { recursive: true, force: true });
  }
});

test("does not reopen a parent directory after it is swapped", async () => {
  const outputRoot = await mkdtemp(join(tmpdir(), "failure-artifacts-parent-"));
  const outsideRoot = await mkdtemp(join(tmpdir(), "failure-artifacts-parent-outside-"));
  const parentPath = join(outputRoot, "nested");
  const artifactPath = join(parentPath, "artifact.txt");
  const outsidePath = join(outsideRoot, "artifact.txt");
  try {
    await mkdir(parentPath);
    await writeFile(artifactPath, "PARENT_SWAP_RAW_SENTINEL", "utf8");
    await writeFile(outsidePath, "OUTSIDE_PARENT_RAW_SENTINEL", "utf8");
    const reporter = new FailureArtifactsReporter();
    reporter.onBegin({ outputDir: outputRoot, projects: [] });

    await rm(parentPath, { recursive: true });
    await symlink(outsideRoot, parentPath);
    const result = {
      status: "failed",
      attachments: [{
        name: "stdout",
        contentType: "text/plain",
        path: artifactPath,
      }],
    };

    reporter.onTestEnd({}, result);
    reporter.onEnd({});

    expect(result.attachments).toEqual([]);
    expect(await readFile(outsidePath, "utf8")).toBe(
      "OUTSIDE_PARENT_RAW_SENTINEL",
    );
  } finally {
    await rm(outputRoot, { recursive: true, force: true });
    await rm(outsideRoot, { recursive: true, force: true });
  }
});

test("unlinks a final artifact when permission prevents opening it", async () => {
  const outputRoot = await mkdtemp(join(tmpdir(), "failure-artifacts-permission-"));
  const artifactPath = join(outputRoot, "artifact.txt");
  try {
    await writeFile(artifactPath, "PERMISSION_RAW_SENTINEL", "utf8");
    await chmod(artifactPath, 0o000);
    const result = {
      status: "failed",
      attachments: [{
        name: "stdout",
        contentType: "text/plain",
        path: artifactPath,
      }],
    };

    runReporter(result, outputRoot);

    expect(result.attachments).toEqual([]);
    expect(await readFile(artifactPath).catch(() => undefined)).toBeUndefined();
  } finally {
    await rm(outputRoot, { recursive: true, force: true });
  }
});

test("cleans a tainted output root onEnd and leaves no raw leftovers", async () => {
  const outputRoot = await mkdtemp(join(tmpdir(), "failure-artifacts-tainted-"));
  const artifactPath = join(outputRoot, "artifact.txt");
  let reporter;
  try {
    await writeFile(artifactPath, "TAINTED_RAW_SENTINEL", "utf8");
    await chmod(artifactPath, 0o000);
    reporter = new FailureArtifactsReporter();
    reporter.onBegin({ outputDir: outputRoot, projects: [] });
    await chmod(outputRoot, 0o500);

    const result = {
      status: "failed",
      attachments: [{
        name: "stdout",
        contentType: "text/plain",
        path: artifactPath,
      }],
    };
    reporter.onTestEnd({}, result);
    reporter.onEnd({});

    expect(result.attachments).toEqual([]);
    expect(await readdir(outputRoot)).toEqual([]);
  } finally {
    await chmod(outputRoot, 0o700).catch(() => {});
    await rm(outputRoot, { recursive: true, force: true });
  }
});

test("fails safely and closes roots when tainted cleanup cannot complete", async () => {
  const outputRoot = await mkdtemp(join(tmpdir(), "failure-artifacts-cleanup-"));
  const projectOutputRoot = await mkdtemp(
    join(tmpdir(), "failure-artifacts-cleanup-project-"),
  );
  const rawArtifact = join(outputRoot, "raw-artifact.txt");
  let reporter;
  let outputDescriptor;
  let projectDescriptor;
  try {
    await writeFile(rawArtifact, "RAW_CLEANUP_FAILURE_SENTINEL", "utf8");
    reporter = new FailureArtifactsReporter();
    reporter.onBegin({
      outputDir: outputRoot,
      projects: [{ outputDir: projectOutputRoot }],
    });
    const [output, project] = reporter.outputRoots;
    outputDescriptor = output.descriptor;
    projectDescriptor = project.descriptor;
    output.tainted = true;
    closeSync(outputDescriptor);

    const originalWrite = process.stdout.write;
    let diagnostic = "";
    let cleanupResult;
    try {
      process.stdout.write = (chunk) => {
        diagnostic += String(chunk);
        return true;
      };
      cleanupResult = reporter.onEnd({});
    } finally {
      process.stdout.write = originalWrite;
    }

    expect(cleanupResult).toEqual({ status: "failed" });
    expect(diagnostic).toBe(
      "Failure artifact cleanup failed; residual artifacts may remain.\n",
    );
    expect(diagnostic).not.toContain("RAW_CLEANUP_FAILURE_SENTINEL");
    expect(diagnostic).not.toContain(outputRoot);
    expect(reporter.outputRoots.map((root) => root.descriptor)).toEqual([
      undefined,
      undefined,
    ]);
    expect(() => closeSync(projectDescriptor)).toThrow();
    expect(await readFile(rawArtifact, "utf8")).toBe("RAW_CLEANUP_FAILURE_SENTINEL");
  } finally {
    await rm(outputRoot, { recursive: true, force: true });
    await rm(projectOutputRoot, { recursive: true, force: true });
  }
});

test("rewrites the validated inode even if its pathname is swapped", async () => {
  const outputRoot = await mkdtemp(join(tmpdir(), "failure-artifacts-swap-"));
  const outsideRoot = await mkdtemp(join(tmpdir(), "failure-artifacts-swap-outside-"));
  const artifactPath = join(outputRoot, "artifact.txt");
  const outsidePath = join(outsideRoot, "outside.txt");
  let descriptor;
  try {
    await writeFile(artifactPath, "ORIGINAL_RAW_SENTINEL", "utf8");
    await writeFile(outsidePath, "OUTSIDE_RAW_SENTINEL", "utf8");
    descriptor = openValidatedFileDescriptorSync(artifactPath);
    await rm(artifactPath);
    await symlink(outsidePath, artifactPath);

    rewriteValidatedDescriptorSync(descriptor, Buffer.from("[REDACTED]\n"));

    expect(readValidatedDescriptorSync(descriptor).toString("utf8")).toBe("[REDACTED]\n");
    expect(await readFile(outsidePath, "utf8")).toBe("OUTSIDE_RAW_SENTINEL");
    expect(await readFile(artifactPath, "utf8")).toBe("OUTSIDE_RAW_SENTINEL");
  } finally {
    if (descriptor !== undefined) closeSync(descriptor);
    await rm(outputRoot, { recursive: true, force: true });
    await rm(outsideRoot, { recursive: true, force: true });
  }
});

test("wholesale-replaces error headings and absolute or relative stacks", () => {
  const sentinels = [
    "ERROR_CONTEXT_PROMPT_SENTINEL",
    "ERROR_CONTEXT_SOURCE_SENTINEL",
    "ERROR_CONTEXT_TOKEN_SENTINEL",
    "/home/runner/project/source.py",
    "relative/source.py",
  ];
  const safe = sanitizeErrorContext([
    "# Failure",
    `Error: ${sentinels[0]}`,
    `    at /home/runner/project/source.py:12:4`,
    `    at ${sentinels[3]}:20:1`,
    `## ${sentinels[1]} ${sentinels[2]}`,
    "## Page snapshot",
    sentinels[1],
  ].join("\n"));

  expect(safe).toContain("# Failure");
  expect(safe).toContain("Error: [REDACTED]");
  expect(safe).toContain("    at [REDACTED]");
  expect(safe).not.toContain("ERROR_CONTEXT_PROMPT_SENTINEL");
  for (const sentinel of sentinels.slice(1)) {
    expect(safe).not.toContain(sentinel);
  }
});

function runReporter(result, outputRoot) {
  const reporter = new FailureArtifactsReporter();
  reporter.onBegin({
    outputDir: outputRoot,
    projects: [],
  });
  return reporter.onTestEnd({}, result);
}

function insertPngChunk(png, typeName, data) {
  let offset = 8;
  while (offset < png.length) {
    const length = png.readUInt32BE(offset);
    const type = png.subarray(offset + 4, offset + 8).toString("ascii");
    if (type === "IEND") {
      const chunkType = Buffer.from(typeName, "ascii");
      return Buffer.concat([
        png.subarray(0, offset),
        makePngChunk(chunkType, data),
        png.subarray(offset),
      ]);
    }
    offset += 12 + length;
  }
  throw new Error("PNG has no end chunk");
}

function makePngChunk(type, data) {
  const chunk = Buffer.alloc(12 + data.length);
  chunk.writeUInt32BE(data.length, 0);
  type.copy(chunk, 4);
  data.copy(chunk, 8);
  chunk.writeUInt32BE(
    crc32(Buffer.concat([type, data])),
    8 + data.length,
  );
  return chunk;
}

test("rejects adversarial trace ZIP metadata before rewriting", async () => {
  const root = await mkdtemp(join(tmpdir(), "failure-artifacts-zip-"));
  const archivePath = join(root, "trace.zip");
  try {
    const createArchive = spawnSync("python3", [
      "-c",
      `
import json
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1], "w", zipfile.ZIP_DEFLATED) as archive:
    archive.writestr("trace.trace", json.dumps({"type": "before"}))
`,
      archivePath,
    ], { encoding: "utf8" });
    if (createArchive.status !== 0) throw new Error(createArchive.stderr);

    const original = await readFile(archivePath);
    const centralOffset = original.lastIndexOf(Buffer.from([0x50, 0x4b, 0x01, 0x02]));
    const endOffset = original.lastIndexOf(Buffer.from([0x50, 0x4b, 0x05, 0x06]));
    const malformed = [
      ["crc", (archive) => {
        const crc = archive.readUInt32LE(14) ^ 1;
        archive.writeUInt32LE(crc, 14);
        archive.writeUInt32LE(crc, centralOffset + 16);
      }],
      ["encryption", (archive) => {
        archive.writeUInt16LE(1, 6);
        archive.writeUInt16LE(1, centralOffset + 8);
      }],
      ["data descriptor", (archive) => {
        archive.writeUInt16LE(8, 6);
        archive.writeUInt16LE(8, centralOffset + 8);
      }],
      ["compression", (archive) => {
        archive.writeUInt16LE(99, 8);
        archive.writeUInt16LE(99, centralOffset + 10);
      }],
      ["compressed size", (archive) => {
        archive.writeUInt32LE(0xffffffff, 18);
        archive.writeUInt32LE(0xffffffff, centralOffset + 20);
      }],
      ["uncompressed size", (archive) => {
        archive.writeUInt32LE(999, 22);
        archive.writeUInt32LE(999, centralOffset + 24);
      }],
      ["local offset", (archive) => {
        archive.writeUInt32LE(1, centralOffset + 42);
      }],
      ["local name", (archive) => {
        archive[30] ^= 1;
      }],
      ["local flags", (archive) => {
        archive.writeUInt16LE(0x800, 6);
      }],
      ["local method", (archive) => {
        archive.writeUInt16LE(0, 8);
      }],
      ["local size", (archive) => {
        archive.writeUInt32LE(archive.readUInt32LE(18) + 1, 18);
      }],
      ["local extra", (archive) => {
        archive.writeUInt16LE(1, 28);
      }],
      ["central name", (archive) => {
        archive[centralOffset + 46] ^= 1;
      }],
      ["local and central time", (archive) => {
        archive.writeUInt16LE(
          archive.readUInt16LE(centralOffset + 12) ^ 1,
          centralOffset + 12,
        );
      }],
      ["central creator", (archive) => {
        archive.writeUInt16LE(0, centralOffset + 4);
      }],
      ["central attributes", (archive) => {
        archive.writeUInt32LE(1, centralOffset + 38);
      }],
      ["central extra", (archive) => {
        archive.writeUInt16LE(1, centralOffset + 30);
      }],
      ["central comment", (archive) => {
        archive.writeUInt16LE(1, centralOffset + 32);
      }],
      ["directory size", (archive) => {
        archive.writeUInt32LE(archive.readUInt32LE(endOffset + 12) + 1, endOffset + 12);
      }],
      ["directory offset", (archive) => {
        archive.writeUInt32LE(archive.readUInt32LE(endOffset + 16) + 1, endOffset + 16);
      }],
      ["entry count", (archive) => {
        archive.writeUInt16LE(2, endOffset + 10);
      }],
      ["multi-disk", (archive) => {
        archive.writeUInt16LE(1, endOffset + 4);
      }],
      ["ZIP64", (archive) => {
        archive.writeUInt16LE(0xffff, endOffset + 10);
      }],
      ["trailing data", (archive) => {
        return Buffer.concat([archive, Buffer.from([0])]);
      }],
    ].map(([name, mutate]) => {
      const archive = Buffer.from(original);
      return [name, mutate(archive) || archive];
    });
    for (const [name, archive] of malformed) {
      await writeFile(archivePath, archive);
      expect(() => sanitizeTraceArchiveSync(archivePath), name).toThrow();
      expect(await readFile(archivePath)).toEqual(archive);
    }

    await writeFile(archivePath, original);
    const archiveWithDuplicate = spawnSync("python3", [
      "-c",
      `
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1], "a", zipfile.ZIP_DEFLATED) as archive:
    archive.writestr("trace.trace", '{"type": "after"}')
`,
      archivePath,
    ], { encoding: "utf8" });
    if (archiveWithDuplicate.status !== 0) {
      throw new Error(archiveWithDuplicate.stderr);
    }
    expect(() => sanitizeTraceArchiveSync(archivePath)).toThrow();
    await writeFile(archivePath, original);

    const result = {
      status: "failed",
      attachments: [{
        name: "trace",
        contentType: "application/zip",
        path: archivePath,
      }],
    };
    const archiveWithUnexpectedEntry = spawnSync("python3", [
      "-c",
      `
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1], "a", zipfile.ZIP_DEFLATED) as archive:
    archive.writestr("unexpected.txt", "UNEXPECTED_TRACE_ENTRY_SENTINEL")
`,
      archivePath,
    ], { encoding: "utf8" });
    if (archiveWithUnexpectedEntry.status !== 0) {
      throw new Error(archiveWithUnexpectedEntry.stderr);
    }
    runReporter(result, root);
    expect(result.attachments).toEqual([]);
    expect(await readFile(archivePath, "utf8")).toBe("[REDACTED]\n");
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("rejects malformed Playwright data descriptors and archive boundaries", () => {
  const name = "trace.trace";
  const data = Buffer.from(`${JSON.stringify({ type: "before" })}\n`);
  const archive = createPlaywrightArchive([{ name, data }]);
  const compressedSize = deflateRawSync(data).length;
  const descriptorOffset = 30 + Buffer.byteLength(name) + compressedSize;
  const centralOffset = descriptorOffset + 16;
  const endOffset = centralOffset + 46 + Buffer.byteLength(name) + 9;
  const malformed = [
    ["descriptor CRC", (copy) => {
      copy.writeUInt32LE(copy.readUInt32LE(descriptorOffset + 4) ^ 1, descriptorOffset + 4);
    }],
    ["descriptor size", (copy) => {
      copy.writeUInt32LE(copy.readUInt32LE(descriptorOffset + 8) + 1, descriptorOffset + 8);
    }],
    ["local size with descriptor", (copy) => {
      copy.writeUInt32LE(1, 18);
    }],
    ["central local offset", (copy) => {
      copy.writeUInt32LE(1, centralOffset + 42);
    }],
    ["EOCD directory offset", (copy) => {
      copy.writeUInt32LE(copy.readUInt32LE(endOffset + 16) + 1, endOffset + 16);
    }],
    ["trailing bytes", (copy) => Buffer.concat([copy, Buffer.from([0])])],
  ];

  for (const [name, mutate] of malformed) {
    const copy = Buffer.from(archive);
    const result = mutate(copy) || copy;
    expect(() => sanitizeTraceArchiveBuffer(result), name).toThrow();
  }
});

test("rejects many-entry archives whose declared total exceeds the policy", () => {
  const entries = Array.from({ length: 17 }, (_, index) => ({
    name: `attachments/${index.toString(16).padStart(40, "0")}`,
    data: Buffer.from([index]),
  }));
  const archive = createPlaywrightArchive(entries);
  const endOffset = archive.lastIndexOf(Buffer.from([0x50, 0x4b, 0x05, 0x06]));
  let centralOffset = archive.readUInt32LE(endOffset + 16);
  const declaredSize = Math.floor(MAX_TRACE_UNCOMPRESSED_BYTES / entries.length) + 1;

  for (const entry of entries) {
    const nameLength = archive.readUInt16LE(centralOffset + 28);
    const extraLength = archive.readUInt16LE(centralOffset + 30);
    const compressedSize = archive.readUInt32LE(centralOffset + 20);
    const localOffset = archive.readUInt32LE(centralOffset + 42);
    const localNameLength = archive.readUInt16LE(localOffset + 26);
    const localExtraLength = archive.readUInt16LE(localOffset + 28);
    const descriptorOffset =
      localOffset + 30 + localNameLength + localExtraLength + compressedSize;

    archive.writeUInt32LE(declaredSize, centralOffset + 24);
    archive.writeUInt32LE(declaredSize, descriptorOffset + 12);
    centralOffset += 46 + nameLength + extraLength;
  }

  expect(() => sanitizeTraceArchiveBuffer(archive)).toThrow(
    `trace archive exceeds maximum uncompressed size of ${MAX_TRACE_UNCOMPRESSED_BYTES} bytes`,
  );
});

test("rejects an oversized trace archive before parsing", () => {
  const archive = Buffer.alloc(MAX_TRACE_ARCHIVE_BYTES + 1);

  expect(() => sanitizeTraceArchiveBuffer(archive)).toThrow(
    `trace archive exceeds maximum size of ${MAX_TRACE_ARCHIVE_BYTES} bytes`,
  );
});

test("rejects oversized sparse trace files before reading them", async () => {
  const root = await mkdtemp(join(tmpdir(), "failure-artifacts-sparse-"));
  const archivePath = join(root, "trace.zip");
  const sparseSize = MAX_TRACE_ARCHIVE_BYTES * 64;
  try {
    const fileHandle = await openFile(archivePath, "w");
    await fileHandle.truncate(sparseSize);
    await fileHandle.close();

    const message =
      `trace archive exceeds maximum size of ${MAX_TRACE_ARCHIVE_BYTES} bytes`;
    expect(() => sanitizeTraceArchiveSync(archivePath)).toThrow(message);
    await expect(sanitizeTraceArchive(archivePath)).rejects.toThrow(message);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("hard-bounds highly compressible deflate output", () => {
  const name = "trace.trace";
  const data = Buffer.alloc(MAX_TRACE_ENTRY_BYTES + 1, 0x41);
  const archive = createPlaywrightArchive([{ name, data }]);
  const compressedSize = deflateRawSync(data).length;
  const descriptorOffset = 30 + Buffer.byteLength(name) + compressedSize;
  const centralOffset = descriptorOffset + 16;

  archive.writeUInt32LE(MAX_TRACE_ENTRY_BYTES, centralOffset + 24);
  archive.writeUInt32LE(MAX_TRACE_ENTRY_BYTES, descriptorOffset + 12);

  expect(() => sanitizeTraceArchiveBuffer(archive)).toThrow(
    "trace archive entry failed decompression",
  );
});
