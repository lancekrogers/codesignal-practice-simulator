# Immutable submission capture

Implemented by the coordinator directly (not delegated). Builds on
02_creation_identity; see results/creation_identity.md.

## What changed

- `models.py`: `ReviewSource` (filename, sha256, content, self-verifying) and a
  rewritten `ReviewRecord` carrying `state_revision`, the stored `assessment`,
  `content_identity` (`pinned` for v2, `unavailable` for v1), timestamps, score
  and the source member. `canonical_review_bytes()` / `review_digest()` define
  the exact published bytes. `SessionStateV2.review_digest` is required on a
  submitted state and forbidden otherwise. `SubmissionRecovery` carries the
  review; a v2 submission must have one, and a pre-capture
  `submission-recovery/v1` file with no review key still replays.
- `persistence.py`: `review.json` is published first, once, and never rewritten;
  an existing member must be byte-identical or recovery fails closed.
  `read_review()` is bounded (2 MiB), rejects symlinks and non-files.
- `lifecycle.py`: submit reads the source, scores, then re-reads it under one
  attempt lock. A change during scoring raises the new `ScoredSourceChangedError`
  (exit 4) and commits nothing. An unreadable source records `source: null` and
  still finalizes, because the deadline is authoritative.
- `application.py`: payload rules at the shared boundary — active saves with
  If-Match; expired/abandoned refuse a payload that would change the saved
  source (read-only, nothing written) and ignore an identical one; submitted
  always returns the committed result without saving or rescoring. The saved
  source is read directly, so no baseline or history is created on that path.
- `docs/cli-contract.md`: v1/v2 schemas and the unsupported mixed-version
  writer case, the review record and its three axes, the scored-bytes rule, and
  the payload contract change.

## Decision corrected during the task

The task file I wrote earlier in this session said a submitted attempt should
reject a differing payload with an error. Reading the accepted journeys showed
that contradicts D002 ("repeated submitted requests return the existing
committed result") and `browser_continuity`, which already pins that behavior.
D002 targets *mutation* payloads on expired/abandoned attempts, so a payload
identical to the saved source is not a mutation. The task file now records the
corrected rule, and both accepted journeys still pass unchanged.

## Verification actually run

    python3 -m unittest tests.test_submission_capture -v     12 tests, OK
    just check unit                                          348 tests, OK (1 skipped)
    just check browser                                       175 passed, 0 failed
    python3 -m unittest tests.test_documentation -q          OK
    git diff --check                                         clean

Covered: exact scored bytes bound to the result; source changed during scoring
commits nothing; unreadable source finalizes with recorded absence; duplicate
submit returns the committed result with one scorer call; legacy v1 submission
captures source with `content_identity: unavailable`; recovery at five durable
boundaries (review write, review published then reported failure, session
replace, event unavailable, marker cleanup) republishes the recorded review with
the scorer spy armed to fail if called; a tampered published review fails closed
with the state left active and the marker intact; oversized and symlinked review
members rejected; all four payload rules.

Mutation check (each guard disabled in turn, then restored; all killed by the
named test): scored-bytes re-verification, review-member byte verification, and
the terminal payload rejection.

## Flaky, not a regression

One `just check unit` run failed three subprocess-timeout tests
(`test_scoring` continuous-writer and crash/timeout cases, and the web
continuous-output case) while the machine was loaded. They passed individually
twice and in a clean full rerun. They are wall-clock sensitive; treat a failure
there as load, but re-check at the sequence testing gate.

## Not verified

- `just check wheel` still cannot run here (no interpreter with setuptools, pip,
  venv, wheel, build). Unchanged from the previous task.
- No real candidate attempt or fetched File Storage content was read or scored.

## Follow-ups

- 003/01/04 consumes these axes; it must treat a submitted v2 state whose
  `review.json` is missing as not captured rather than as corruption.
- A UI affordance for finalizing an expired attempt belongs to 005/02: the
  browser disables Submit after expiry, so the CLI remains the finalize path.
