# Shared lifecycle actions (abandon, restart, live-selection policy)

Implemented by the coordinator directly in the linked cp0002-practice-library
worktree on 2026-09-12, on top of results/restart_journal.md. Uncommitted
pending this sequence's 06_fest_commit gate. HTTP handlers are deferred to
003/03/02 as the task requires; the shared services, error contract, and CLI
are complete.

## What changed

- `lifecycle.py`
  - `abandon(attempt_id, expected_revision, reason="ended") -> AbandonResult`:
    under the workspace+attempt locks (`selected_attempt`, which now also runs
    restart and abandonment recovery), reads the record, expires it if overdue,
    rejects terminal states (`cannot abandon an attempt in X state`), then
    stale revisions, then writes ahead `.abandonment-recovery.json` and
    publishes the abandoned state and `abandoned` event through
    `publish_transition_locked`. A repeat at the same expected revision returns
    the stored record with `newly_abandoned: false`.
  - `restart(attempt_id, operation_id, expected_revision, assessment=None,
    mode=None, drill_duration_seconds=None) -> RestartResult`: resolves the
    implicit selection once under the workspace lock, expires an overdue
    attempt, defaults target assessment/profile to the old attempt's, pins the
    target to the installed content, then calls
    `WorkspaceManager.restart_attempt`.
  - `_read_abandonable_session_locked`: a pinned v2 record needs no registry
    lookup to be ended (an uninstalled content version must not trap the user
    in a live attempt); a legacy record still goes through the adapter, so an
    uninterpretable v1 record blocks the mutation but never read-only review.
  - `start_exclusive` is the guarded plain start (`start_web` kept as an
    alias); `start` remains the unguarded primitive tests use for neighbors.
    `_reject_live_selection` now raises `LiveSelectionError`, decides liveness
    from stored status/deadline only, and names the attempt and resolutions.
  - `resume --attempt X` while the selected attempt Y is live is the same
    `LiveSelectionError`; a corrupt pointer or missing selected directory does
    not block the explicit resume, which repairs the pointer.
  - `_read_recovered_session_locked(validate=...)` runs
    `recover_attempt_locked` (submission or abandonment) before policy.
- `persistence.py`: `ABANDONMENT_RECOVERY_FILENAME`, `RECOVERY_MARKER_FILENAMES`,
  `persist_abandonment_locked`, `recover_abandonment_locked`,
  `recover_attempt_locked` (both markers present is corruption; nothing written).
- `models.py`: `AbandonmentRecovery` (`abandonment-recovery/v1`) validates that
  the final state equals `abandoned_record(prior)` and the event matches;
  `END_REASON = "ended"`.
- `application.py`: `abandon(...)` and `restart(...)` shared entrypoints with
  derived-status refresh; `_start_locked` always uses `start_exclusive`, so the
  CLI and browser share one live-selection policy.
- `cli.py`: `abandon --expected-revision N`; `restart --expected-revision N
  [--operation-id UUID] [--mode] [--drill-duration-seconds]` (the CLI mints and
  echoes an operation ID when none is given; a duration requires drill mode);
  `serialize_result` for `AbandonResult`/`RestartResult`; error envelopes use
  the new specific codes when present.
- `errors.py`: `DomainError.code`; `StaleRevisionError` → `stale_revision`,
  `RestartConflictError` → `operation_conflict`, `LiveSelectionError` →
  `live_selection` (exit 4); `RestartRecoveryPendingError` → `recovery_pending`
  (exit 3). Existing envelopes are unchanged.
- `workspace.py`: terminal state is reported before a stale revision
  (refreshing cannot make a submitted attempt restartable); `restart_attempt`
  and `selected_attempt` run `recover_attempt_locked`.
- `attempt_reviews.py`: a pending abandonment marker is reported as
  `ReviewPendingError`, like a pending submission.
- `docs/cli-contract.md`: command tree, abandon/restart semantics,
  live-selection policy, specific error codes, lifecycle table row.

## Contract change and its test fallout

D001 ("plain start must not silently replace a selected live attempt in either
CLI or browser") changes behavior the old tests encoded. Adjusted:

- `tests/test_lifecycle.py`: the resume test now asserts the conflict while
  the selected attempt is live and the replacement of selection once it has
  expired.
- `tests/test_cli.py`: two runtime tests end the first attempt with the new
  `abandon` command before starting a second; the neighbor-recovery test
  creates its live neighbor through the unguarded primitive; the parser test
  lists the two new commands.
- `tests/test_end_to_end.py`: the selection test ends the neighbor with a real
  `abandon` process before starting the attempt under test.
- `tests/test_web_server_lifecycle.py`: the second live attempt comes from the
  unguarded primitive.

No accepted browser journey needed changes: the browser already used the
guarded start.

## Negative cases proven (tests/test_lifecycle_actions.py, 17 tests)

- Abandon: repeat at the same revision is byte-identical; stale revision;
  invalid revisions; overdue attempt is expired (the only mutation) then
  refused; submitted attempt refused; resume/test/submit on an abandoned
  attempt exit 4 without writes; scorer never called.
- Legacy v1 abandonment: interrupted at session replace and at an unavailable
  event log; review reports pending while the marker exists; `status` recovers
  the upgrade (session/v2, `content_identity: unavailable`, v1 then v2 events);
  repeat abandon replays; a non-selected legacy neighbor stays byte-identical
  and selected.
- Uninstalled pinned content: abandon works, resume still refuses; restart
  lands on the installed content; plain start is refused for the live attempt
  (not for the uninstalled content) and works after ending it.
- Uninterpretable legacy record blocks abandon and restart, review still works.
- Restart service: defaults, replay, conflict, stale tab on the live
  replacement, terminal answer for the abandoned attempt, duration without
  drill mode; overdue → expired then refused; restart during scoring is a
  bounded busy error; after submit it is a terminal answer; retry after a
  failed response replays the committed operation with the original timer.
- Selection policy: plain start refused with `live_selection` naming the
  attempt; abandon and restart are the resolutions; source reset keeps ID,
  deadline, selection and directory set; explicit resume repairs a corrupt
  pointer but never displaces live work.
- CLI: dispatch of both commands, minted operation ID, seven invalid argument
  shapes exit 2 without calling the application; result serialization; the
  five error codes and exit codes.
- Two processes: two real Python processes restart the same attempt with one
  operation ID concurrently; exactly one replacement exists, the loser (if any)
  gets a bounded error and its retry replays the same replacement ID.

## Evidence

    python3 -m unittest tests.test_lifecycle_actions   17 tests OK
    just check unit                                    405 tests OK (1 skipped)
                                                       (includes the real-process
                                                       end-to-end abandon)
    just check browser                                 175 passed
    just check frontend                                passed
    git diff --check                                   clean

`just check wheel` and `just verify` remain unrunnable here, as recorded.

## Follow-ups

- 003/03/02: HTTP `POST /api/attempts/{id}/abandon|restart` should call
  `application.abandon/restart` and map `StaleRevisionError`,
  `RestartConflictError`, `LiveSelectionError` → 409 with their codes and
  `RestartRecoveryPendingError` → 503/`recovery_pending` per D004; the web
  `_domain_failure` mapping still folds them into 423/404 today.
- 005 UI: the restart confirmation (D004) must send `expected_revision` and a
  client-minted `operation_id`, and reuse the same ID on retry.
- Server startup should call `WorkspaceManager.recover_restarts()`.
- 003/03: surface `abandonment.practice_score` in history/review.
