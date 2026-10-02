# Coordinator review: intercepted-response semantics

The latest whole-suite 160 passed / one failed / three skipped is consistent
with **serial-suite fallout**, not opt-in probe skips: `shell_layout.spec.mjs`
configures serial execution and has three tests after the failed roving case.
`harness_failure_probe.spec.mjs` is excluded by the default configuration. Correct
the earlier agent interpretation in the retained evidence; do not enable expected
failure probes in the outer passing suite. The existing harness tests already
exercise those probes in intentionally failing child runners.

Pending disposition; discovered during the final browser runs, after the earlier
focused checks passed. Inspect the final diff before accepting these as findings.

The installed locked Playwright 1.63 implementation is in
`webui/node_modules/playwright-core/lib/coreBundle.js`, `_innerFulfill` near 59760.
It normalizes header names/values, lets `contentType` override a header, and gives
truthy `json` payloads an application/json content type. The draft scanner did
not mirror those rules. Concrete potential false negatives:

1. `intercept(path, {json: {message: FORBIDDEN_SENTINEL}})` serializes and serves
   scannable JSON, but the scanner omitted its content type and marked the CDP
   response covered, so neither mechanism inspects the body.
2. `headers: {'Content-Type': 'application/octet-stream'}, contentType:
   'application/json', body: <sentinel JSON>` is served as JSON, but the scanner
   honored the old binary header and skipped it.

Normalize only supported inline fulfill options once and pass the same effective
headers/body to scanning and fulfillment, or otherwise preserve exact locked
semantics. Add meaningful forbidden-content regressions for the supported JSON
and overriding-contentType branches. Reject unsupported/mutually exclusive
options explicitly; do not claim an unexamined body was covered.

The draft `interceptedResponseBody` also uses `Buffer.from` for an entire string
or existing Buffer before checking declared length. Preserve the 64 KiB scanner
allocation bound by retaining the supplied body and using existing byte-length
and prefix-copy helpers; an already supplied buffer does not need a full copy.
JSON serialization required for fulfillment should not be duplicated if avoidable.

Rename the fast-response test to describe pre-fulfillment bounded scanning;
its former “arms streaming” title is no longer the behavior asserted.

These are narrow follow-ups to the test-only fix, not authorization for runtime
changes, broader mocking features, additional dependencies, or weakened guards.
