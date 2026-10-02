# Sequence testing gate — 003/02_restart_and_abandon

Covers 01_restart_journal and 02_shared_lifecycle_actions. Per-task evidence,
including mutation checks and the list of injected boundaries, is in the two
sibling results files.

## Commands run and results (final code, 2026-09-12)

    python3 -m unittest tests.test_restart_journal       24 tests, OK
    python3 -m unittest tests.test_lifecycle_actions     17 tests, OK
    just check unit                                      405 tests, OK (1 skipped)
    just check browser                                   175 passed, 0 failed
    just check frontend                                  passed
    python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope tracked        passed
    python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary   passed
    python3 -m unittest tests.test_documentation         6 tests, OK
    git diff --check                                     clean

`just check unit` includes tests.test_end_to_end, which now runs the new
`abandon` command in a real console process, and tests.test_lifecycle_actions,
which restarts one attempt from two real Python processes concurrently. All
tests use synthetic first-party workspaces in temporary directories; no real
attempt data was read.

## Failure boundaries actually exercised

- Restart, pre-commit: input copy, staged session, journal not durable; journal
  durable but reported failed.
- Restart, post-commit (each for a v2 and a v1 old attempt): old session
  replace before/after, old event log unavailable, replacement publish
  before/after, pointer replace before/after, pointer flush, receipt write
  before/after, journal prune. Recovery entered through `recover_restarts`,
  `reconcile`, `create_attempt`, implicit `status`, explicit `resolve_attempt`.
- Restart, fail closed: tampered journal checksum, pointer moved to a third
  attempt while pending, staging deleted while pending, receipt immutability.
- Restart, identity: identical replay (fresh, after reselection, after the
  replacement was submitted), changed profile/revision/old-attempt/content
  version conflicts, changed arguments against a pending journal.
- Abandon: interrupted at session replace and at an unavailable event log for a
  legacy v1 record; review pending while the marker exists; replay; stale,
  terminal and overdue rejection; uninstalled pinned content; uninterpretable
  legacy record.
- Concurrency: restart while the old attempt lock is held; restart after
  submit; two processes with one operation ID.
- Policy: plain start against a live selection (including one whose content is
  uninstalled); explicit resume against a live selection and against a corrupt
  pointer; source reset leaving ID, deadline and selection unchanged.
- CLI: seven invalid argument shapes; five error codes and exits; result
  serialization for both new commands.

Mutation checks: journal-first ordering in `_reconcile_locked` (6 tests fail
without it) and the verify-before-write pass in `_roll_forward_locked` (the
pointer-moved test fails without it).

## Not run here, with reasons

- `just verify` stops at `run_legacy_checks.py --scope fixture-cache`: no
  fetched fixture cache in this worktree, and fetching third-party content over
  the network is not authorized for this session. Its other two scopes passed
  and `just check unit` runs the same test suite.
- `just check wheel`: no interpreter here satisfies the packaging
  prerequisites. Owned by 006/01_acceptance_and_distribution.
- `just build assets` / `assets-check`: no frontend source changed.

## Contract change

The D001 live-selection rule (plain start and explicit resume never displace a
live selected attempt) changed behavior four existing tests encoded; they were
updated to the approved contract, not loosened. Details in
results/shared_lifecycle_actions.md.

## Known flakiness

One browser journey failed once when `just check browser` ran concurrently with
the 110-second unit suite and passed on the isolated rerun; the same wall-clock
sensitivity was recorded in 003/01.
