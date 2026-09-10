import { expect, test } from "@playwright/test";
import PrivacySafeReporter from "./privacy_safe_reporter.mjs";

test("ignores raw streaming chunks and emits only safe final status", () => {
  const writes = [];
  const originalWrite = process.stdout.write;
  process.stdout.write = (chunk) => {
    writes.push(String(chunk));
    return true;
  };
  try {
    const reporter = new PrivacySafeReporter();
    reporter.onBegin({});
    reporter.onStdOut(Buffer.from("STREAM_RAW_PROMPT_SENTINEL"));
    reporter.onStdErr("STREAM_RAW_SOURCE_SENTINEL");
    reporter.onTestEnd({}, {
      status: "failed",
      error: {
        message: "RAW_FAILURE_MESSAGE_SENTINEL",
        stack: "/Users/private/source.py",
      },
    });
    reporter.onEnd({});
  } finally {
    process.stdout.write = originalWrite;
  }

  const output = writes.join("");
  expect(output).toContain("Test failed; inspect sanitized artifacts.");
  expect(output).toContain("1 failed");
  expect(output).not.toContain("STREAM_RAW_PROMPT_SENTINEL");
  expect(output).not.toContain("STREAM_RAW_SOURCE_SENTINEL");
  expect(output).not.toContain("RAW_FAILURE_MESSAGE_SENTINEL");
  expect(output).not.toContain("/Users/private/source.py");
});
