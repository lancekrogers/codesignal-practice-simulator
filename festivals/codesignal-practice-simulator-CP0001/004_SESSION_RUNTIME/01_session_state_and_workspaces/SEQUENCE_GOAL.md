---
fest_type: sequence
fest_id: 01_session_state_and_workspaces
fest_name: session_state_and_workspaces
fest_parent: 004_SESSION_RUNTIME
fest_order: 1
fest_status: completed
fest_created: 2026-09-08T16:23:17.448655-06:00
fest_updated: 2026-09-08T19:53:35.856633-06:00
fest_tracking: true
fest_working_dir: .
---


# Sequence Goal: Session State and Workspaces

**Sequence:** 01_session_state_and_workspaces | **Phase:** 004_SESSION_RUNTIME | **Status:** Completed

## Sequence Objective

Implement validated models, injected time, atomic persistence, locks, deterministic selection, and lifecycle services for isolated attempts.

## Required Deliverables

- [x] **Validated durable models**: versioned state, event, score, and pointer schemas with stable errors.
- [x] **Atomic workspaces**: validated-cache attempt inputs, locks, atomic
  state/pointer writes, JSONL recovery, and a setup-required failure path.
- [x] **Lifecycle services**: deterministic start, resume, expiry, and idempotent submission behavior.

## Task Alignment

| Task | Objective |
|------|-----------|
| 01_define_validated_models_clock_and_error_taxonomy | Establish the durable data, time, and error contracts. |
| 02_build_atomic_persistence_locks_and_workspaces | Build isolated workspace and recovery primitives. |
| 03_implement_lifecycle_application_services | Enforce legal session transitions outside CLI parsing. |

## Dependencies and Risks

**Prerequisite:** completed migration.<br>
**Provides:** trustworthy workspaces and lifecycle services to scoring/rendering.<br>
**Risk:** corrupt or concurrent state changes. **Mitigation:** validate before writes, lock mutations, use atomic replacement/recovery events, and never select by newest directory.

## Completion and Gates

- [x] The fetched cache, other attempts, and candidate `simulation.py` remain
  unchanged after setup/copy validation.
- [x] Run every task Verify block, record evidence, and pass all sequence gates.

## Completion Evidence

The three files in `results/` record 17 model tests, 16 focused
persistence/workspace tests, 17 final lifecycle tests, injected filesystem
failures, marker-owned crash recovery, and the judge-approved terminal-state
and repeat-submit ordering fixes. Project commit `6909f22` contains this
sequence.
