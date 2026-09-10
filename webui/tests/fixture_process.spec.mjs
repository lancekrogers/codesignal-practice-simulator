import { expect, test } from "@playwright/test";
import { spawn } from "node:child_process";
import {
  diagnosticTail,
  readReadyLine,
  stopChild,
} from "./fixture_process.mjs";

test("drains large fixture stderr after readiness and keeps only a redacted tail", async () => {
  const child = spawn(process.execPath, ["-e", `
    const secret = "capability=${"s".repeat(80)}";
    process.stderr.write(secret + " from /Users/private/workspace/.cache/file.py\\n");
    process.stderr.write("x".repeat(512 * 1024));
    process.stdout.write(JSON.stringify({ origin: "http://127.0.0.1:1" }) + "\\n");
    process.stderr.write("\\nTAIL_MARKER\\n");
    process.stdin.resume();
    process.stdin.on("end", () => process.exit(0));
  `], { stdio: ["pipe", "pipe", "pipe"] });

  try {
    await expect(readReadyLine(child)).resolves.toEqual({
      origin: "http://127.0.0.1:1",
    });
    await expect.poll(() => diagnosticTail(child)).toContain("TAIL_MARKER");
    const tail = diagnosticTail(child);
    expect(Buffer.byteLength(tail)).toBeLessThanOrEqual(4096);
    expect(tail).toContain("TAIL_MARKER");
    expect(tail).not.toContain("capability=");
    expect(tail).not.toContain("/Users/private/workspace");
  } finally {
    await stopChild(child);
  }
});

test("bounds and redacts startup stderr in exit errors", async () => {
  const secret = `browser-fixture-token-${"t".repeat(80)}`;
  const child = spawn(process.execPath, ["-e", `
    process.stderr.write(${JSON.stringify(
      `${secret} from /private/tmp/fixture-secret/diagnostic.py ${"x".repeat(32 * 1024)}`,
    )});
    process.exit(7);
  `], { stdio: ["pipe", "pipe", "pipe"] });

  let startupError;
  try {
    await readReadyLine(child);
  } catch (error) {
    startupError = error;
  }
  expect(startupError).toBeDefined();
  expect(startupError.message).toContain("[REDACTED]");
  expect(startupError.message).not.toContain(secret);
  expect(startupError.message).not.toContain("/private/tmp/fixture-secret");
  expect(Buffer.byteLength(startupError.message)).toBeLessThan(5000);
  await stopChild(child);
});

test("replaces an oversized split line before a sensitive path suffix can leak", async () => {
  const suffix = "SPLIT_SENSITIVE_PATH_SUFFIX";
  const child = spawn(process.execPath, ["-e", `
    process.stderr.write("/Users/");
    for (let index = 0; index < 4096; index += 1) {
      process.stderr.write("private/");
    }
    process.stderr.write(${JSON.stringify(suffix)});
    process.stderr.write("\\nSPLIT_TAIL_MARKER\\n");
    process.stdout.write(JSON.stringify({ origin: "http://127.0.0.1:1" }) + "\\n");
    process.stdin.resume();
    process.stdin.on("end", () => process.exit(0));
  `], { stdio: ["pipe", "pipe", "pipe"] });

  try {
    await expect(readReadyLine(child)).resolves.toEqual({
      origin: "http://127.0.0.1:1",
    });
    const tail = diagnosticTail(child);
    expect(tail).toContain("[REDACTED]");
    expect(tail).toContain("SPLIT_TAIL_MARKER");
    expect(tail).not.toContain(suffix);
    expect(tail).not.toContain("/Users/");
  } finally {
    await stopChild(child);
  }
});

test("removes process and pipe listeners after the child closes", async () => {
  const child = spawn(process.execPath, ["-e", `
    process.stdout.write(JSON.stringify({ origin: "http://127.0.0.1:1" }) + "\\n");
    process.stdin.resume();
    process.stdin.on("end", () => process.exit(0));
  `], { stdio: ["pipe", "pipe", "pipe"] });

  await readReadyLine(child);
  expect(child.stderr.listenerCount("data")).toBe(1);
  await stopChild(child);
  expect(child.stderr.listenerCount("data")).toBe(0);
  expect(child.listenerCount("close")).toBe(0);
  expect(child.listenerCount("error")).toBe(0);
});
