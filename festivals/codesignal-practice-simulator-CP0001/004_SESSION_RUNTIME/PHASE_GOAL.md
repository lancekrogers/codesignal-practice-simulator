---
fest_type: phase
fest_id: 004_SESSION_RUNTIME
fest_name: SESSION_RUNTIME
fest_parent: codesignal-practice-simulator-CP0001
fest_order: 4
fest_status: completed
fest_created: 2026-09-08T16:23:00.303209-06:00
fest_updated: 2026-09-08T20:40:13.226011-06:00
fest_phase_type: implementation
fest_tracking: true
---


# Phase Goal: Durable Session Runtime

**Phase:** 004_SESSION_RUNTIME | **Status:** Pending | **Type:** Implementation

## Phase Objective

**Primary Goal:** Build isolated, recoverable session state, lifecycle services, independent assessment scoring, and safe derived candidate context.

**Context:** The verified migration supplies a validated ignored local cache;
this phase builds authoritative isolated session services for the CLI.

## Required Outcomes

Deliverables this phase must produce:

- [x] Validated state, atomic workspaces, lifecycle, independent scoring, and safe derived candidate context with passing tests.

## Quality Standards

Quality criteria for all work in this phase:

- [x] Operations are deterministic, require validated setup before copying
  cached files, and never mutate the cache, other attempts, or candidate
  simulation.py outside the stated contract.

## Sequence Alignment

| Sequence | Goal | Key Deliverable |
|----------|------|-----------------|
| 01_session_state_and_workspaces | Build validated state, isolated workspaces, and lifecycle services | Recoverable authoritative runtime |
| 02_assessment_scoring_and_agent_surfaces | Add independent scoring and safe agent surfaces | Derived non-authoritative candidate views |

## Pre-Phase Checklist

Before starting implementation:

- [x] Planning phase complete
- [x] Architecture/design decisions documented
- [x] Dependencies resolved
- [x] Development environment ready

## Phase Progress

### Sequence Completion

- [x] 01_session_state_and_workspaces
- [x] 02_assessment_scoring_and_agent_surfaces

## Completion Evidence

- Validated models/clock/errors:
  [`01_session_state_and_workspaces/results/01_define_validated_models_clock_and_error_taxonomy.md`](01_session_state_and_workspaces/results/01_define_validated_models_clock_and_error_taxonomy.md).
- Atomic persistence, locks, workspace rollback, and ownership-safe crash
  reconciliation:
  [`01_session_state_and_workspaces/results/02_build_atomic_persistence_locks_and_workspaces.md`](01_session_state_and_workspaces/results/02_build_atomic_persistence_locks_and_workspaces.md).
- Expiry, illegal-transition invariance, and idempotent submission:
  [`01_session_state_and_workspaces/results/03_implement_lifecycle_application_services.md`](01_session_state_and_workspaces/results/03_implement_lifecycle_application_services.md).
- Exact `-I -S` four-group scoring, sentinel isolation, process containment,
  and bounded descendant cleanup:
  [`02_assessment_scoring_and_agent_surfaces/results/01_generalize_assessment_lookup_and_score_isolated_attempts.md`](02_assessment_scoring_and_agent_surfaces/results/01_generalize_assessment_lookup_and_score_isolated_attempts.md).
- Safe derived Markdown/JSON context and operational agent policy:
  [`02_assessment_scoring_and_agent_surfaces/results/02_render_status_context_coaching_and_agent_boundaries.md`](02_assessment_scoring_and_agent_surfaces/results/02_render_status_context_coaching_and_agent_boundaries.md).
- Consolidated phase quality results:
  [`results/phase-quality-evidence.md`](results/phase-quality-evidence.md).
- Task, review-finding, iterate-gate, and commit-diff proof:
  [`results/WORKFLOW.md`](results/WORKFLOW.md).
- Implemented project files: `src/codesignal_practice_simulator/models.py`,
  `persistence.py`, `workspace.py`, `lifecycle.py`, `assessments.py`,
  `scoring.py`, and `rendering.py`; focused coverage lives in
  `tests/test_models.py`, `test_persistence.py`, `test_workspace.py`,
  `test_lifecycle.py`, `test_scoring.py`, and `test_rendering.py`.
- Both sequence frontmatters are `fest_status: completed`; their testing,
  review, iterate, and `fest_commit` gate task frontmatters are also completed.

Project commit `56cef56` is pushed to private `origin/main`; the campaign
gitlink records that same project commit.

## Notes

session.json is authoritative; Markdown is derived; coaching is non-executable; operational boundaries are not a security sandbox.
