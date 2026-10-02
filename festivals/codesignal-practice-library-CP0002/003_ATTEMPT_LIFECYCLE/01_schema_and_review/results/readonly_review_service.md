# Read-only review service

Implemented by the coordinator directly (not delegated).

## What changed

- New `src/codesignal_practice_simulator/attempt_reviews.py` with
  `AttemptReviewService.get_review(attempt_id, include_source=True)` returning
  `AttemptReview`: stored metadata, a `ReviewAssessment` carrying
  `content_identity` (`pinned` with version/digest, or `unavailable`), the
  `source_binding` axis (`captured` / `not_captured` / `not_applicable`), an
  optional `ReviewSourceView`, and typed issue codes.
- The service takes no lifecycle lock, so it cannot create a `.session.lock`,
  a source baseline, a history order file, an event, or a pointer write. It
  reads `session.json`, re-reads it after the review member, and reports
  `ReviewPendingError` (new, retryable) if the record changed underneath or a
  `.submission-recovery.json` marker exists. Finalization owns repair.
- It never consults the assessment registry, so stored results stay readable
  when the pinned content version is uninstalled.
- Integrity: the review must match its session (attempt, revision, submitted_at,
  score) and, for v2, the state's `review_digest`. A mismatch is corruption.
- Legacy: a submission with no review member is `not_captured` with
  `submitted_source_binding_unavailable`. The current `simulation.py` is offered
  only as `legacy_unbound` source, read bounded and symlink-safe, and is never
  presented as the submitted bytes.

## Verification actually run

    python3 -m unittest tests.test_attempt_reviews -v      13 tests, OK
    just check unit                                        361 tests, OK (1 skipped)
    git diff --check                                       clean

Every review read in these tests is wrapped in a whole-directory snapshot
comparison plus an `active.json` byte comparison, so "no side effects" is
asserted, not assumed. Also covered: pinned submission returns the verified
immutable source; review still served with the registry removed; unsubmitted
attempt is `not_applicable`; unreadable-at-submission is `not_captured`; legacy
labeling with and without a current file; metadata-only reads; tampered score,
tampered source and wrong-revision members fail closed; a reformatted but
semantically identical member is still the same review (the digest binds
content, not file formatting); pending finalization is retryable and unrepaired;
unsafe IDs, a symlinked attempt directory, a record whose identity does not
match its directory, and an oversized member; a concurrent active attempt keeps
its bytes and deadline. The scorer spy raises if called during any review.

Mutation check (each disabled in turn, then restored; all killed by the named
test): review-to-session binding, the pending-marker check, the
`legacy_unbound` label, and the record-identity check.

## Not wired yet, by design

`attempt_reviews.py` has no HTTP route or CLI command: the plan gives that to
003/03/02_history_and_review_routes, which also owns listing. The service is
constructed by its tests only, so nothing in the running app depends on it yet.

## Not verified

- `just check wheel` still cannot run here (no interpreter with the packaging
  prerequisites).
- The browser suite was last run green at the end of 003/01/03; this task added
  no transport or UI code. The sequence testing gate re-runs it.
