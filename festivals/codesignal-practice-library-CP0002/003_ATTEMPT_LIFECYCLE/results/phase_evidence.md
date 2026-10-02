# Phase 003_ATTEMPT_LIFECYCLE — deliverable inventory and evidence

Recorded 2026-09-12 for the implementation phase gate. Every path below is in
the linked worktree `projects/worktrees/codesignal-practice-simulator/
cp0002-practice-library` at commit `661a9cb` (branch `cp0002-practice-library`),
which contains the three sequence commits:

    661a9cb feat: metadata history listing and explicit review, abandon and restart routes
    4751dd5 feat: recoverable restart journal and explicit abandon/restart actions
    268c07c feat: pin attempt content identity and capture immutable submission reviews

Nothing is pushed; no PR exists. The audit checkout was not modified.

## Deliverable 1 — versioned models (R8)

`src/codesignal_practice_simulator/models.py` (1976 lines)

- `SessionStateV2` (line 509): session/v2 with `PinnedAssessment` or the
  explicit legacy identity (`content_identity: unavailable`, abandoned only),
  `abandonment` metadata and `review_digest`.
- `EventRecordV2` (984); `parse_session_record` (816) and `parse_event_record`
  (1062) dispatch on `schema_version` and raise `UnsupportedSchemaVersionError`
  for unknown versions before any other field is interpreted.
- `ReviewRecord` (1157), `review_digest` (1326), `SubmissionRecovery` (1348)
  with `submission-recovery/v1` and `/v2` families.
- `adapt_session_record` normalizes v1 and v2 in memory; disk is never upgraded
  by a read.

Tests: `tests/test_attempt_models_v2.py` (24), `tests/test_creation_identity.py`
(16, includes v1 attempts completing every command with v1 records).

## Deliverable 2 — immutable submission capture and read-only review (R6/R7)

- `persistence.py`: `persist_submission_locked` (232) writes the WAL then
  `recover_submission_locked` (260) publishes `review.json` exactly once before
  the submitted state, replaying without rescoring.
- `lifecycle.py`: `submit` (430) captures the source, scores, re-reads and
  refuses a changed source, all under the attempt lock.
- `attempt_reviews.py` (341 lines): `AttemptReviewService.get_review` (164)
  reports stored metadata, content identity and source binding as independent
  axes; takes no lock, repairs nothing, never consults the registry.

Tests: `tests/test_submission_capture.py` (14), `tests/test_attempt_reviews.py`
(15): WAL replay at review write, review published-then-reported, session
replace, event append/replace and marker cleanup with a scorer spy; whole
directory snapshot unchanged across review reads; verified review outranks an
edited `session.json`.

## Deliverable 3 — recoverable restart/abandon (R3/R4/R9)

- `models.py`: `RestartRequest` (1500, fingerprinted identity),
  `RestartJournal` (1591, checksummed commit intent that recomputes
  `abandoned_record(prior)` and requires equality), `RestartCompletion` (1812,
  immutable receipt), `AbandonmentRecovery` (1737), `abandoned_record` (826).
- `workspace.py` (998 lines): `restart_attempt` (310; lock order workspace →
  old attempt → staging), `_roll_forward_locked` (468; verify before write,
  idempotent publication, storage failure → `recovery_pending`, corruption →
  fail closed), `_recover_restarts_locked` (605; runs before creation-marker
  reconciliation and before every selection mutation), `recover_restarts`
  (643).
- `lifecycle.py` (637 lines): `abandon` (240), `restart` (296),
  `start_exclusive` (118; plain start never displaces a live selection).
- `persistence.py`: `publish_transition_locked` (354), `persist_abandonment_locked`
  (307), `recover_attempt_locked` (287).
- CLI `abandon`/`restart` with `--expected-revision` and `--operation-id`.

Tests: `tests/test_restart_journal.py` (24), `tests/test_lifecycle_actions.py`
(18): pre-commit failures leave the old attempt active; twelve post-commit
boundaries roll forward the same replacement for v1 and v2 old attempts;
identical replay after reselection and after the replacement was submitted;
changed arguments conflict; tampered journal, moved pointer and missing
replacement fail closed with evidence preserved; delayed recovery does not
extend the timer; a real two-process concurrent restart yields one replacement;
cross-process flock contention is a bounded busy error; old `simulation.py`
bytes and original `started_at`/`deadline_at` asserted unchanged everywhere.

## Deliverable 4 — metadata history and explicit review routes (R5/R7)

- `attempt_history.py` (535 lines): `AttemptHistoryService.list_attempts`
  (308): bounded pages (25/100), creation-time-then-UUID ordering, cursors
  bound to a filters fingerprint, pending restarts/finalizations reported not
  recovered, corrupt records unavailable, unsafe entries counted.
- `web/routes.py` (469 lines): `_list_attempts` (213) for `GET /api/attempts`;
  `_attempt_action` (240) for `GET /api/attempts/{uuid}/review` and
  `POST /api/attempts/{uuid}/abandon|restart`; specific 409/503 codes.
- `cli.py`: `history` and `review` commands calling the same services.

Tests: `tests/test_attempt_history.py` (11): read-spy filesystem proves no
`simulation.py`, `review.json`, `events.jsonl` or prompt reads and unchanged
trees/pointer; `tests/test_history_review_routes.py` (8): review of a submitted
attempt while another is live leaves pointer, bootstrap selection and scorer
count unchanged; unsafe IDs rejected before filesystem access; 401/403 leak
nothing.

## Suite results

    python3 -m unittest <the eight phase modules>   129 tests, OK
    just check unit (after 661a9cb)                 425 tests, OK (1 skipped)
    just check browser                              175 passed, 0 failed
    just check frontend                             passed
    verify_manifest.py --scope tracked/git-boundary passed
    git diff --check                                clean

Not run here: `just check wheel` (no interpreter with packaging prerequisites;
owned by 006) and `just verify`'s fixture-cache scope (no fetched cache;
network fetch of third-party content not authorized). Recorded in each
sequence's `results/testing.md`.

## Reviews

Each sequence ran a delegated read-only Cursor review
(`claude-sonnet-5-thinking-high`) plus a coordinator review; findings and
dispositions are in each `results/review.md`, fixes with regression tests in
each `results/iterate.md`. One blocking finding was raised in the whole phase
(003/01 F1, review boundary trusting mutable session fields) and fixed.
