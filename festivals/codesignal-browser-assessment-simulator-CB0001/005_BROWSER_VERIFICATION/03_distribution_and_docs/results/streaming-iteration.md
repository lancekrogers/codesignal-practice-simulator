# Streaming harness iteration

## Cause and remediation

The recurring failure was a harness ordering defect, not a wheel or documentation
change. Harness-owned `route.fulfill()` responses were classified as strict
synthetic responses, but their bodies were inspected through an independently
issued `Network.streamResourceContent` command. Playwright fulfillment could
finish before pinned Chromium accepted that command. Chromium then rejects a
late command because the resource already has content; a pending or rejected
command could leave the fast-response assertion without all diagnostics or with
a strict `streaming-unavailable` violation.

Waiting for the stream command before fulfillment is not viable: the command
does not resolve while Playwright has the request paused. A same-CDP-session
barrier also blocks behind the pending stream command. Both designs timed out in
controlled experiments and were removed.

The guard now normalizes supported inline fulfillment options once using the
locked Playwright 1.63 semantics, scans the supplied bytes synchronously before
`route.fulfill()`, and passes the same effective status, headers, and body to
Playwright. The scan:

- retains the existing 64 KiB prefix and 100-response limits;
- does not copy a complete supplied string or Buffer before eligibility checks;
- applies JSON's default MIME type and lets `contentType` override headers;
- rejects path-, response-, mixed body/JSON-, and unsupported-body options;
- runs even if the matching CDP request has not arrived, then correlates that
  request later only to suppress duplicate network scanning;
- excludes already scanned requests when matching repeated identical URLs; and
- reports `scanMechanism: "intercepted-body"` while honestly leaving
  `streamEstablished` false.

Network streaming remains in place for non-intercepted responses. Existing
per-response non-synthetic stream failures remain explicit skips; global CDP
setup failure and harness-controlled synthetic failures remain fail-closed.
This distinction was part of the existing guard and was not broadened.

## Additional confirmed guard defect

`assertPolicyState` previously awaited one snapshot of `scanPromises`. A
deterministic A/B check proved that assertion could start with pending A, acquire
pending B while awaiting A, and finish without awaiting B. The pre-fix causal
test failed once as intended. Draining now continues to a fixed point and runs
again after relevant requests settle; B's deferred violation is observed and
rejects the assertion.

A request begun after the final empty fixed-point check is still outside that
assertion invocation. Tests are required to await their browser operations;
closing or freezing the page inside this guard would be a broader lifecycle
change and was not added.

## Regression coverage

New checks prove:

- eight fast intercepted responses are bounded-scanned before fulfillment;
- repeated identical method/URL responses each receive a scan, and a forbidden
  sentinel in the later body is detected;
- JSON default MIME and overriding `contentType` both expose forbidden JSON;
- unsupported fulfillment shapes are rejected before routing;
- missing and rejected stream setup remains a `streaming-unavailable`
  violation without retrieving `response.body()`; and
- scans queued while assertion is already draining are awaited.

Existing invalid/conflicting/missing length, over-budget/lying body, forbidden
sentinel, and retained-prefix checks remain enabled.

## Commands and counts

Initial and diagnostic evidence:

- Original focused command,
  `npm --prefix webui run test:browser -- harness.spec.mjs --grep "arms streaming before fast same-origin responses finish" --repeat-each=100`:
  99 passed, 1 failed with default privacy reporters.
- Temporary poll-only instrumentation: 100/100 and 200/200 passed. It was
  insufficient because it did not cover the following violation assertion or
  teardown, and was replaced.
- Full test/teardown aggregate instrumentation: 120/120 repeats, one 19/19
  harness-file run, and 20/20 fresh single-test processes passed. No capabilities,
  URLs, body/source text, or raw errors were recorded. The original sanitized
  failure therefore has no recoverable per-stage counter; this is a retained
  diagnostic limitation.
- Await-stream experiment: one focused test timed out; process exited after
  67.923 seconds.
- Same-session dispatch-barrier experiment: one causal test passed and the fast
  browser test timed out; process exited after 68.813 seconds.
- Pre-fix A/B scan-drain regression: 1 failed as expected.

Final focused verification:

- Nine bounded/forbidden/length/setup/ordering checks: 9 passed.
- Three normalized intercepted-response browser checks with
  `--repeat-each=10`: 30 passed.
- Earlier bounded fast/repeated browser checks with `--repeat-each=20`:
  40 passed.
- `npm --prefix webui run test:browser -- harness.spec.mjs`: 24 passed. This
  includes subprocess coverage of the synthetic failure, output-ownership, and
  cleanup-failure probe modes with their expected outcomes.
- `npm --prefix webui run check`, Node syntax checks, and `git diff --check`:
  passed.

Complete browser verification:

- First post-fix complete run: 160 passed, 1 failed, 3 skipped. The failure was
  `shell_layout.spec.mjs` keyboard roving; because that file is serial, its
  remaining three tests were automatically skipped. These were not opt-in probe
  skips.
- Exact shell test: 1 passed. Temporary stage-only instrumentation then passed
  20/20 repeats and emitted no failure stage. The complete serial shell file
  passed 10/10 after instrumentation was removed. No shell test was changed.
- Two subsequent complete commands,
  `npm --prefix webui run test:browser`: 166 passed each with the configured
  default reporters and no skips.

The shell failure's exact assertion remains unavailable because the default
reporter correctly redacted it and it did not recur under stage-only diagnosis.
Its focused, repeated, serial-file, and two complete-suite reruns all passed, so
no unsupported shell change or retry policy was introduced.

Successful cleanup left only `webui/.test-results/.last-run.json`, containing
`status: passed` and no failed test IDs. Temporary streaming and shell-stage
diagnostic files were removed. No real cache, attempt, source, capability,
reference, or fetched assessment material was inspected or retained.

Only `webui/tests/harness.spec.mjs`, `webui/tests/network_guard.mjs`, and this
aggregate evidence file were changed by this iteration. Runtime product code,
privacy reporters, network/content limits, coordinator-owned documentation, and
festival status were not changed. The coordinator will perform the installed-
wheel rerun after review.
