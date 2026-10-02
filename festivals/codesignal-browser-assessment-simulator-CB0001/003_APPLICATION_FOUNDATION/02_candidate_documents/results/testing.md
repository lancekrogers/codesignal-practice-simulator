# Candidate Document Testing

Date: 2026-09-09
Base commit: `42b27da`

## Final evidence

- Candidate-document focused suite: 24 passed.
- Full unittest suite: 187 passed after final remediation; earlier remediation
  milestones passed 179, 182, and 185 tests twice as coverage expanded.
- `scripts/run_legacy_checks.py`: passed all provenance, reference-study, and
  staged checks.
- `just verify`: passed during the sequence after populating the ignored,
  hash-validated fixture cache.
- `python3 -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- New production/test files are below 500 lines and new functions below 50.

Tests cover strict UTF-8/256-KiB boundaries, ETags, separate-service CAS races,
attempt locks, atomic failure boundaries, deterministic identical-clock history
ordering, newest-50 pruning, duplicate/orphan/corrupt records, missing files,
symlinks/ownership, reset/restore, every final mutation, legacy baselines, exact
attempt-tree immutability after rejection, and prompt/test/vendor exclusion.

No test artifact or FETCH_ONLY byte is tracked.
