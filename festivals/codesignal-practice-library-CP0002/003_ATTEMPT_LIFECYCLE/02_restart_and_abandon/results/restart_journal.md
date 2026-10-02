# Restart journal (D001 restart transaction)

Implemented by the coordinator directly in the linked cp0002-practice-library
worktree on 2026-09-12. Uncommitted pending this sequence's 06_fest_commit gate.

## What changed

- `models.py`
  - `SessionStateV2.assessment` is `PinnedAssessment | AssessmentMetadata`. The
    disk record now carries an explicit `content_identity` key (`pinned` |
    `unavailable`); `from_dict` parses the assessment by that label and never
    infers it from shape. The `unavailable` variant is legal only in the
    `abandoned` status ("a session without content identity may only record
    abandonment"). session/v2 is unreleased, so the added key changes no
    shipped record; every hand-built v2 dict in tests round-trips via `to_dict`.
  - `abandoned_record(state, ended_at, reason)`: the abandoned successor of an
    active v1 or v2 record. Original start/deadline/identity unchanged, revision
    +1, `score` moved to `abandonment.practice_score`. A v1 input yields the
    explicit legacy-identity v2 variant.
  - `RestartRequest` (`restart-request/v1`): operation UUID, old attempt ID,
    expected revision, target `PinnedAssessment`, profile; `fingerprint` is the
    SHA-256 of its canonical JSON.
  - `RestartJournal` (`restart-journal/v1`, checksummed) validates that the
    final state equals `abandoned_record(prior, committed_at)`, both events match
    their states and `committed_at`, the replacement is revision 0, active,
    pinned to the request target and started at `committed_at`, and the staging
    name is `.<replacement>.staging-<token>`.
  - `RestartCompletion` (`restart-completion/v1`, checksummed): request,
    replacement ID, committed_at. `from_journal()`.
  - `adapt_session_record` and `ReviewRecord.plan` decide content identity by
    the assessment type, not the schema version.
- `persistence.py`
  - `publish_transition_locked(attempt, prior, state, event)` factored out of
    submission recovery: idempotent state+event publication that accepts only
    the prior or final state and appends the event exactly once at its
    revision. Submission recovery now calls it; its tests are unchanged.
  - `attempts/.restart-journal/<op>.json` and `attempts/.restart-completed/<op>.json`
    read/write helpers, bounded at 4 MiB, symlink and non-file entries rejected,
    interrupted `.tmp` writes skipped. `write_restart_completion_locked` is
    idempotent for an equal receipt and corruption for a different one.
- `workspace.py`
  - `restart_attempt(request, now, reason)`: workspace lock → reconcile
    (journals, then markers) → completed receipt replay/conflict → old attempt
    lock → submission recovery → validate revision/status/deadline → build
    replacement through `_validate_creation_state` → stage through
    `_populate_staging` (verified v2 creation path, journal-supplied `started`
    event) → durable journal (commit point) → roll forward.
  - Pre-commit failure removes only staging. A journal write that reports
    failure after becoming durable is detected by re-reading it and the
    operation proceeds instead of orphaning a committed intent.
  - `_roll_forward_locked`: verifies the old record, replacement placement and
    pointer against their allowed prior/target states before the first write;
    then publishes old state+event, `replace(staging, destination)`, pointer,
    receipt, prunes the journal, removes the creation marker. Storage failures
    raise `RestartRecoveryPendingError` (exit 3) with the operation ID and keep
    the journal; corruption raises `SessionCorruptError` and preserves evidence.
  - `_recover_restarts_locked` runs first inside `_reconcile_locked` (so the
    creation-marker scan cannot delete a published-but-unselected replacement),
    and in `resolve_attempt` and `selected_attempt` under the workspace lock.
    `recover_restarts()` is the explicit entrypoint. Review/history reads do not
    touch it.
  - `_definition_for_persisted_session` uses the legacy adapter for any
    `AssessmentMetadata` assessment, so an upgraded legacy record still resolves
    its definition for candidate-document reads.
  - `_validate_creation_state` rejects a v2 state without a pinned identity.
- `errors.py`: `RestartConflictError`, `StaleRevisionError` (both exit 4),
  `RestartRecoveryPendingError` (exit 3).
- `rendering.py`: `_next_legal_commands` treats `abandoned` as terminal
  (status/context only) so STATUS.md refresh and `context` work on old attempts.
- `docs/cli-contract.md`: `content_identity` key, abandonment metadata, the
  legacy upgrade rule, a new "Restart transaction" section, exit table rows.

## Deliberate decisions

- The journal lives beside the attempts (workspace-owned, dot-prefixed), not
  inside either attempt: it spans two records and the pointer, and the marker
  scan already skips dot-prefixed entries.
- Restart requires the old attempt to be `active` and before its deadline. An
  expired attempt is finalized with `submit` or replaced by a plain start; that
  is the D001 state contract, not a gap.
- The old attempt's definition is not consulted: abandonment needs no scoring.
  Task 02 decides whether an uninstalled content version blocks the user action.
- Events carry `operation_id` plus `replacement_attempt_id` /
  `replaces_attempt_id` so the two records reference each other durably.
- `RestartResult` on replay carries IDs and `committed_at` only; reading the
  replacement's current state is the caller's choice (it may be submitted).

## Negative cases proven (tests/test_restart_journal.py, 24 tests)

- Pre-commit: input copy failure, staged session failure, journal not durable:
  old active and selected, tree unchanged, no staging, no journal, no receipt.
- Journal durable but reported failed: operation completes, one replacement.
- Post-commit boundaries, each for a v2 and a v1 old attempt: old session
  replace (before/after), old event log unavailable, replacement publish
  (before/after), pointer replace (before/after), pointer flush, receipt write
  (before/after), journal prune. Each raises recovery-pending, keeps the exact
  journal, preserves old source bytes, then `recover_restarts()` yields exactly
  one replacement, the abandoned old record, the pointer on the replacement, the
  receipt, no journal, no marker, no staging; repeat recovery is a no-op and a
  repeat request replays.
- Discovery: a journal pending after replacement publish (marker present,
  pointer still old) is rolled forward by `reconcile`, `create_attempt`,
  implicit `status`, and explicit `resolve_attempt`; the marker scan does not
  delete the replacement.
- Receipt written but journal left: pruned without state checks.
- Replay: identical repeat returns the original ID, states unchanged; after
  another attempt is selected the selection is untouched; after the replacement
  is submitted nothing is written and the scorer is not called.
- Conflict: same UUID with changed profile, revision, old attempt, or content
  version → `RestartConflictError`, tree unchanged; against a pending journal it
  recovers first, then conflicts, still one replacement.
- Fail closed: tampered journal (checksum) from every entrypoint, pointer moved
  to a third attempt while pending, staging deleted while pending: nothing
  written, evidence kept. Receipt is immutable.
- Validation: stale revision, at/after deadline, unknown target content,
  submitted old attempt, old attempt lock held (bounded `LockUnavailableError`).
- Timer: recovery three hours later leaves `started_at`/`deadline_at` at the
  committed timestamp.
- Legacy identity model: unpinned v2 only as abandoned; mislabeled or unlabeled
  `content_identity` rejected; practice score relocation; no creation from a
  legacy identity; journal binding cases and checksum tamper.

Mutation checks: removing journal-first recovery from `_reconcile_locked` fails
six cases; removing the verify-before-write pass fails the pointer-moved case.

## Evidence

    python3 -m unittest tests.test_restart_journal   24 tests OK
    just check unit                                  388 tests OK (1 skipped)
    just check frontend                              passed
    just check browser                               175 passed (alone)
                                                     171 passed / 1 failed when run
                                                     concurrently with the unit suite;
                                                     load-related, same flakiness
                                                     recorded in 003/01
    git diff --check                                 clean
    python3 -m unittest tests.test_documentation     6 OK

`just check wheel` and `just verify` remain unrunnable here (no interpreter with
packaging prerequisites; fixture cache not fetched), as recorded in 003/01.

## Follow-ups for later tasks

- 003/02/02: `LifecycleService.restart_attempt` should compute the pinned target
  via `workspace.pinned_assessment`, expire the old attempt first when overdue,
  and map `StaleRevisionError`/`RestartConflictError` → conflict and
  `RestartRecoveryPendingError` → recovery-pending per D004. Abandon-only can be
  built from `abandoned_record` + `publish_transition_locked` behind a small
  attempt-owned WAL, mirroring submission recovery.
- 003/03: `AttemptReview` has no `practice_score` field; the history/review API
  should surface `abandonment.practice_score` honestly labeled.
- Server startup should call `WorkspaceManager.recover_restarts()` (D001
  "server recovery entrypoints own repair").
