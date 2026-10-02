---
fest_type: phase
fest_id: 005_CLI_WORKFLOWS
fest_name: CLI_WORKFLOWS
fest_parent: codesignal-practice-simulator-CP0001
fest_order: 5
fest_status: completed
fest_created: 2026-09-08T16:23:00.321537-06:00
fest_updated: 2026-09-08T22:42:37.141833-06:00
fest_phase_type: implementation
fest_tracking: true
---


# Phase Goal: Candidate and Agent CLI Workflows

**Phase:** 005_CLI_WORKFLOWS | **Status:** Complete pending gate approval | **Type:** Implementation

## Phase Objective

**Primary Goal:** Expose the session runtime through a documented console and module CLI with stable human and JSON behavior.

**Context:** The runtime owns state and business rules; this phase exposes it through console and module interfaces without duplicate domain logic.

## Required Outcomes

Deliverables this phase must produce:

- [x] Stable lifecycle, scoring, finality, and context commands with documented human/JSON/error behavior and compatibility guidance.

## Quality Standards

Quality criteria for all work in this phase:

- [x] Handlers only adapt typed services and never directly edit state, locks,
  the fetch-only cache, candidate code, or scoring inputs; missing validated
  setup yields an actionable error.

## Sequence Alignment

| Sequence | Goal | Key Deliverable |
|----------|------|-----------------|
| 01_command_interface_and_live_session | Build shared parsing and live-session commands | Equivalent console and module CLI behavior |
| 02_evaluation_submission_and_operator_docs | Add evaluation/finality commands and operator documentation | Accurate CLI-first documentation |

## Pre-Phase Checklist

Before starting implementation:

- [x] Planning phase complete
- [x] Architecture/design decisions documented
- [x] Dependencies resolved
- [x] Development environment ready

## Phase Progress

### Sequence Completion

- [x] 01_command_interface_and_live_session — committed and pushed as `a852b73`
- [x] 02_evaluation_submission_and_operator_docs — committed and pushed as `c206300`

## Notes

codesignal-sim is canonical; python -m is equivalent; failed candidate groups are scored outcomes, not crashes.

## Completion Evidence

- 136 tests pass under both the project Python 3.10 environment and system Python.
- Console and module help are byte-identical; live temporary-workspace
  start/context/test/submit/repeat-submit flows pass with the documented exits.
- All tracked, fetched-cache, and staged/HEAD manifest scopes plus both Git
  hooks pass; the private repository contains no upstream fixture bytes.
- Independent Cursor judges approved both sequences after all findings were
  fixed, including coherent selection, cache-path isolation, typed CLI
  services, installed-wheel setup, and exact-once submission recovery.
- `just verify`, specification tests, staged-solution tests, and all four study
  checkpoints pass. The aggregate `scripts/run_legacy_checks.py` remains the
  explicitly planned phase-006 deliverable.
