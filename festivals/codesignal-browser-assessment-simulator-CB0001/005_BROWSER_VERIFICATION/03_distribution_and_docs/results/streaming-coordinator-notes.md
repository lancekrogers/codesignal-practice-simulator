# Streaming investigation direction

Current temporary instrumentation only catches the diagnostics-count poll. It
does not catch the following `responseScanViolations()` assertion or the global
`afterEach` policy assertion. A failure in either path could therefore leave no
diagnostic record and be incorrectly attributed to missing scan registration.

Before more large repetition batches, capture safe aggregate counters/reasons
across the ENTIRE test and its afterEach policy assertion: test stage, expected
fast-response count, observed fast count, reason counts for all skips/violations,
and any policy failure category. Do not include capabilities, body/source text,
raw error messages, or URLs. Preserve all default reporters and bounds. Temporary
instrumentation must be removed before final code/review.

The suggested settled-before-response path is a hypothesis, not yet the observed
cause. Distinguish it from unrelated bootstrap/asset scan violations or a final
policy assertion failure. Prefer one deterministic controlled-event regression
over further hundreds of blind repetitions once evidence identifies the path.

Do not weaken fail-closed scanning, count/byte limits, network policy or assertions.
The coordinator's first full run was 160 passed/1 failed; canonical 277+4 and docs
passed. Resolve this bounded harness issue, then rerun focused and full browser
checks. Current uncommitted docs remain coordinator-owned and must be preserved.
