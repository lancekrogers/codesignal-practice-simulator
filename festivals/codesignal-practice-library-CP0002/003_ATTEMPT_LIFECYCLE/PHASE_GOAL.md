---
fest_type: phase
fest_id: 003_ATTEMPT_LIFECYCLE
fest_name: ATTEMPT_LIFECYCLE
fest_parent: codesignal-practice-library-CP0002
fest_order: 3
fest_status: completed
fest_created: 2026-09-11T14:31:52.971252-06:00
fest_updated: 2026-09-12T19:45:13.193966-06:00
fest_phase_type: implementation
fest_tracking: true
---


# Phase Goal: 003_ATTEMPT_LIFECYCLE

**Phase:** 003_ATTEMPT_LIFECYCLE | **Status:** Pending | **Type:** Implementation

## Phase Objective

**Primary Goal:** Durable reusable attempts with versioned schema, immutable submission review, restart/abandon recovery, and metadata history APIs.

**Context:** Implements D001/D002 persistence and service contracts from approved 002_PLAN. Establishes authoritative lifecycle, review, and history boundaries required before catalog expansion (004) and UI flows (005). Sequence order is strict: 01 → 02 → 03 with no parallel writes to the same persistence surfaces.

## Required Outcomes

Deliverables this phase must produce:

- [x] Versioned attempt/event/review models with v1 adapters and safe unknown-version rejection (R8).
- [x] Immutable submission capture and read-only review service without rescoring or read-triggered upgrades (R6/R7).
- [x] Recoverable restart/abandon with operation UUID idempotency and preserved old source/timer (R3/R4/R9).
- [x] Metadata-only history listing and explicit review routes with unchanged active selection (R5/R7).

## Evidence of deliverables (2026-09-12)

Project code lives in the linked worktree
`projects/worktrees/codesignal-practice-simulator/cp0002-practice-library`,
branch `cp0002-practice-library`, in three commits made with
`fest commit --no-root`: `268c07c` (003/01), `4751dd5` (003/02), `661a9cb`
(003/03). None is pushed. Symbol locations below are from those commits; the
full inventory with test names is in `results/phase_evidence.md`.

| Deliverable | Where it exists | How it is proven functional |
| --- | --- | --- |
| Versioned models + v1 adapters + unknown-version rejection | `src/codesignal_practice_simulator/models.py` (1976 lines): `SessionStateV2` :509, `EventRecordV2` :984, `ReviewRecord` :1157, `SubmissionRecovery` :1348, `parse_session_record` :816 / `parse_event_record` :1062 dispatch on `schema_version` and raise `UnsupportedSchemaVersionError` for unknown versions; `adapt_session_record` normalizes v1 in memory | `tests/test_attempt_models_v2.py` (24), `tests/test_creation_identity.py` (16): v1 records keep v1 writes, no fabricated identity, unknown version rejected before any field is read |
| Immutable submission capture (WAL) + read-only review service | `persistence.py`: `persist_submission_locked` :232, `recover_submission_locked` :260 (publishes `review.json` once, never rescoring); `lifecycle.submit` :430 captures, scores and re-verifies bytes under one lock; `attempt_reviews.py` (341 lines): `AttemptReviewService.get_review` :164, three independent axes | `tests/test_submission_capture.py` (14), `tests/test_attempt_reviews.py` (15): WAL replay at every boundary with a scorer spy, whole-directory hash unchanged by review reads, verified review outranks an edited session |
| Recoverable restart/abandon, operation-UUID idempotency, old source/timer preserved | `models.py`: `RestartRequest` :1500, `RestartJournal` :1591 (checksummed commit intent), `RestartCompletion` :1812, `AbandonmentRecovery` :1737, `abandoned_record` :826; `workspace.py`: `restart_attempt` :310, `_roll_forward_locked` :468, `_recover_restarts_locked` :605, `recover_restarts` :643; `lifecycle.py`: `abandon` :240, `restart` :296, `start_exclusive` :118; `persistence.py`: `publish_transition_locked` :354, `persist_abandonment_locked` :307, `recover_attempt_locked` :287 | `tests/test_restart_journal.py` (24), `tests/test_lifecycle_actions.py` (18): failure injection at 12 post-commit boundaries for v1 and v2 old attempts, identical-request replay, changed-argument conflict, fail-closed corruption cases, a real two-process concurrent restart, cross-process lock contention, old `simulation.py` bytes and `started_at`/`deadline_at` asserted unchanged |
| Metadata-only history listing + explicit review routes, selection unchanged | `attempt_history.py` (535 lines): `AttemptHistoryService.list_attempts` :308; `web/routes.py`: `_list_attempts` :213 (`GET /api/attempts`), `_attempt_action` :240 (`GET /api/attempts/{uuid}/review`, `POST .../abandon|restart`); CLI `history`/`review` in `cli.py` | `tests/test_attempt_history.py` (11): read-spy filesystem proves no source/review/event/prompt reads, tree and `active.json` unchanged; `tests/test_history_review_routes.py` (8): review of an old attempt while another is live leaves pointer, selection and scorer-call count unchanged |

Focused suites for the phase: 129 tests, OK. Full project suite after the last
commit: `just check unit` 425 tests OK (1 skipped), `just check browser` 175
passed, `just check frontend` passed, manifest provenance scopes passed. Each
sequence has `results/testing.md`, `results/review.md` (delegated Cursor review
plus coordinator review; all accepted findings fixed in `results/iterate.md`).

## Quality Standards

Quality criteria for all work in all sequences:

- [x] **Evidence-based acceptance:** Each task proves behavior with focused tests, injected failure boundaries, and recorded command output—not structural fest validation alone.
- [x] **Decision fidelity:** Implementation matches D001_attempt_lifecycle.md and D002_submission_review.md; deviations require a new decision record. Two execution amendments were recorded (D002, D003) for the identity ordering repair; D005 was resolved on the user's delegation.
- [x] **Safety boundary:** No reads of real candidate/cache/reference data; synthetic workspaces only.

## Sequence Alignment

| Sequence | Goal | Key Deliverable |
|----------|------|-----------------|
| 01_schema_and_review | Preserve and explain persisted work | v2 models, submission WAL, attempt_reviews.py |
| 02_restart_and_abandon | Explicit fresh practice | Restart journal, shared abandon/restart actions |
| 03_attempt_history_api | Browse without changing selection | attempt_history.py, history/review routes |

## Pre-Phase Checklist

Before starting implementation:

- [ ] Planning phase complete
- [ ] Architecture/design decisions documented
- [ ] Dependencies resolved
- [ ] Development environment ready

## Phase Progress

### Sequence Completion

- [x] 01_schema_and_review (commit 268c07c; results in 01_schema_and_review/results/)
- [x] 02_restart_and_abandon (commit 4751dd5; results in 02_restart_and_abandon/results/)
- [x] 03_attempt_history_api (commit 661a9cb; results in 03_attempt_history_api/results/)

## Notes

Anchors verified at planning baseline `7833def`; revalidate `models.py:338/:521`, `persistence.py:86/:172`, `lifecycle.py:82/:315`, `application.py:174/:371`, `web/routes.py:120/:208` before edits. Execute from a dedicated project worktree relinked to this festival; audit checkout remains read-only.

---

*Implementation phases use numbered sequences. Create sequences with `fest create sequence`.*
