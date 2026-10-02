# CB0001 sustained-output scorer timeout remediation

## Result

Remediated `_collect_bounded_output` so a continuously readable child pipe
cannot monopolize an inner drain loop past the scoring deadline.

The collector now:

- performs one nonblocking read per main-loop iteration;
- rechecks the monotonic deadline after every read;
- caps selector waits at the existing `_PROCESS_POLL_SECONDS`;
- immediately drains an already-exited process only while reads make progress,
  stopping at EOF, would-block, output truncation, or the deadline;
- preserves timeout cleanup ordering: snapshot descendants, stop the fixed
  process tree/group, close the output pipe, then perform bounded cleanup.

No `communicate`, dependency, scan, or transport changes were introduced.

## Synthetic regression coverage

- A deterministic stepping clock and always-readable fake pipe has a six-read
  fail-fast guard. Against the old collector it failed immediately because the
  unbounded inner drain exceeded the guard. Against the remediation it times
  out after bounded reads and verifies capped selector waits.
- A real synthetic writer emits continuously for at most two seconds. A
  100-millisecond scorer timeout returns boundedly, reaps the writer, and still
  runs the three later groups successfully.
- An exited synthetic parent with a descendant-held output pipe returns
  without waiting for descendant EOF.
- HTTP evaluation maps the timeout to the fixed generic error, does not expose
  runtime-output markers or paths, reports later groups as passed, and leaves a
  subsequent `/api/time` request responsive.

All test inputs were first-party synthetic strings. No candidate, reference,
cache, study, hidden-test, or vendor content was read or used.

## Commands and evidence

1. Old-function regression:

   `python3 -m unittest tests.test_scoring.ScoringTests.test_continuously_readable_output_rechecks_deadline_after_each_read -v`

   Ran 1 test in 0.007s: **FAILED (failures=1)**. The fail-fast assertion was
   `continuous output was drained without a deadline recheck`.

2. Same regression after the minimal collector change:

   `python3 -m unittest tests.test_scoring.ScoringTests.test_continuously_readable_output_rechecks_deadline_after_each_read -v`

   Ran 1 test in 0.006s: **OK**.

3. Focused scoring suite:

   `python3 -m unittest tests.test_scoring -v`

   Ran 15 tests in 1.690s: **OK**.

4. Initial focused web evaluation suite:

   `python3 -m unittest tests.test_web_server_evaluation -v`

   Ran 5 tests in 2.587s: **FAILED (failures=1)**. The new test had embedded
   its forbidden marker literally in candidate source, which the API
   intentionally returns. The synthetic fixture was corrected to assemble the
   marker only at runtime; no product behavior changed for this correction.

5. Final focused web evaluation suite:

   `python3 -m unittest tests.test_web_server_evaluation -v`

   Ran 5 tests in 2.907s: **OK**.

6. Focused diff whitespace check:

   `git diff --check && git diff -- src/codesignal_practice_simulator/scoring.py tests/test_scoring.py tests/test_web_server_evaluation.py`

   Exit status 0.

## Limitations

Per task scope, no full canonical suite, build, install, fetch, browser run,
commit, push, or festival-state operation was performed. Timing assertions
provide generous local upper bounds and are not latency benchmarks. POSIX
process-containment regressions are skipped on non-POSIX platforms.
