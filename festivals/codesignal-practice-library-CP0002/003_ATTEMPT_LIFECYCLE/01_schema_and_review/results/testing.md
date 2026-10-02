# Sequence testing gate — 003/01_schema_and_review

Covers 01_versioned_models, 02_creation_identity, 03_submission_capture and
04_readonly_review_service. Per-task evidence is in the sibling results files.

## Commands run and results

    just check unit                     361 tests, OK (1 skipped)
    just check frontend                 passed
    just check browser                  175 passed, 0 failed
    python3 scripts/verify_manifest.py --scope tracked        passed
    python3 scripts/verify_manifest.py --scope git-boundary   passed
    git diff --check                    clean

Focused modules: tests.test_attempt_models_v2 (24), tests.test_creation_identity
(16), tests.test_submission_capture (12), tests.test_attempt_reviews (13). All
use synthetic first-party workspaces in temporary directories.

## Failure boundaries actually exercised

- Creation: staged bytes differing from declared hashes; missing or malformed
  manifest commit; a caller-supplied identity that differs from the computed
  one; a pinned version that is not installed.
- Submission: source changed while the scorer ran; unreadable source at
  submission; duplicate submit; WAL failure injected at review write, review
  published then reported failure, session replace, event append/replace, and
  marker cleanup — each replayed without a second scorer call.
- Integrity: tampered review score, tampered review source, wrong revision,
  oversized member, symlinked member, and a review that does not match its
  session digest.
- Reads: whole-directory snapshot equality across every review call, pending
  finalization treated as retryable, no baseline or history creation, unsafe
  identifiers and symlinked attempt directories.
- Legacy v1: full command set with v1 records and v1 events, v1 WAL replay, and
  no fabricated content identity anywhere.

Mutation checks were run for each new guard (creation identity, staged-byte
verification, pinned lookup, scored-bytes re-verification, review byte
verification, terminal payload rejection, review-session binding, pending
marker, legacy source labeling, record identity). Every mutant was killed by
the named test.

## Not run here, with reasons

- `just verify` stops at `run_legacy_checks.py --scope fixture-cache`: this
  worktree has no fetched fixture cache. Fetching downloads vendored upstream
  assessment content over the network, which was not authorized for this
  session, and the check proves cache provenance rather than any behavior this
  sequence changed. Its other two scopes (tracked, git-boundary) passed, and
  `just check unit` runs the same suite `just verify` would, including
  tests.test_end_to_end, which builds its own synthetic manifest.
- `just check wheel`: no interpreter here satisfies setuptools/pip/venv/wheel/
  build. Owned by 006/01_acceptance_and_distribution.
- `just build assets` / `assets-check`: no frontend source changed in this
  sequence.

## Known flakiness

Three subprocess-timeout tests (`test_scoring` continuous-writer and
crash/timeout, and the web continuous-output case) failed once under machine
load and passed on isolated and clean full reruns. They are wall-clock
sensitive, not affected by this sequence's changes.
