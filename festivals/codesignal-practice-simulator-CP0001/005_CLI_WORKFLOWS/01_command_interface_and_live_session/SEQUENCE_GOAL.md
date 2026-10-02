---
fest_type: sequence
fest_id: 01_command_interface_and_live_session
fest_name: command_interface_and_live_session
fest_parent: 005_CLI_WORKFLOWS
fest_order: 1
fest_status: completed
fest_created: 2026-09-08T16:23:17.498601-06:00
fest_updated: 2026-09-08T21:43:24.956942-06:00
fest_tracking: true
fest_working_dir: .
---


# Sequence Goal: Command Interface and Live Session

**Sequence:** 01_command_interface_and_live_session | **Phase:** 005_CLI_WORKFLOWS | **Status:** Complete

## Sequence Objective

Build one parser and output/error adapter, then expose deterministic session selection and live-session commands through typed services.

## Required Deliverables

- [x] **CLI contract**: common options, stable human/JSON envelopes, and exits 0, 2, 3, 4, and 5.
- [x] **Invocation parity**: `codesignal-sim` and `python -m` have equivalent behavior.
- [x] **Live-session commands**: start, resume, status, time, and task delegate to the runtime.

## Task Alignment

| Task | Objective |
|------|-----------|
| 01_build_parser_output_adapters_and_selection_plumbing | Centralize parsing, output, selection, and errors. |
| 02_expose_start_resume_status_time_and_task | Wire lifecycle-safe candidate commands. |

## Dependencies and Risks

**Prerequisite:** completed session runtime.<br>
**Provides:** the CLI foundation for evaluation/finality and documentation.<br>
**Risk:** parser drift or direct state access in handlers. **Mitigation:** define options once, centralize mapping, and test both entry points.

## Completion and Gates

- [x] Every task Verify block passes with no partial mutation on invalid input.
- [x] Evidence is recorded and all required sequence gates pass.

Evidence: commit `a852b73`; 120-test sequence suite under both interpreters;
all manifest scopes and hooks passed; independent final judge approved with no
critical findings.
