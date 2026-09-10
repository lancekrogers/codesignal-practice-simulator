const SAFE_FAILURE_MESSAGE = "Test failed; inspect sanitized artifacts.";
const TERMINAL_STATUSES = new Set([
  "failed",
  "timedOut",
  "interrupted",
  "passed",
  "skipped",
]);

export default class PrivacySafeReporter {
  constructor() {
    this.counts = new Map();
  }

  onBegin() {
    this.counts.clear();
  }

  onStdOut() {}

  onStdErr() {}

  onTestEnd(_test, result) {
    const status = TERMINAL_STATUSES.has(result?.status)
      ? result.status
      : "failed";
    this.counts.set(status, (this.counts.get(status) || 0) + 1);
    const detail = ["failed", "timedOut", "interrupted"].includes(status)
      ? `: ${SAFE_FAILURE_MESSAGE}`
      : "";
    process.stdout.write(`test ${status}${detail}\n`);
  }

  onEnd() {
    const failed = sum(this.counts, ["failed", "timedOut", "interrupted"]);
    const passed = this.counts.get("passed") || 0;
    const skipped = this.counts.get("skipped") || 0;
    const summary = [
      failed ? `${failed} failed` : "",
      passed ? `${passed} passed` : "",
      skipped ? `${skipped} skipped` : "",
    ].filter(Boolean);
    process.stdout.write(`${summary.join(", ") || "0 tests"}\n`);
  }
}

function sum(counts, statuses) {
  return statuses.reduce(
    (total, status) => total + (counts.get(status) || 0),
    0,
  );
}
