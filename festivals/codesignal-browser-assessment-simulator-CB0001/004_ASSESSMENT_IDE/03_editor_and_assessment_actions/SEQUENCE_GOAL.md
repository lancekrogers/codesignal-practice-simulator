---
fest_type: sequence
fest_id: 03_editor_and_assessment_actions
fest_name: editor and assessment actions
fest_parent: 004_ASSESSMENT_IDE
fest_order: 3
fest_status: completed
fest_created: 2026-09-09T03:13:07.354241-06:00
fest_updated: 2026-09-09T20:02:15.844267-06:00
fest_tracking: true
---


# Sequence Goal: 03_EDITOR_AND_ASSESSMENT_ACTIONS

**Sequence:** 03_EDITOR_AND_ASSESSMENT_ACTIONS | **Phase:** 004_ASSESSMENT_IDE | **Status:** Completed

## Sequence Objective

**Primary Goal:** Connect the Monaco editor and assessment controls to durable source/API contracts so editing, prompt views, navigation, tests, reset/history, expiry, and submit behave as one coherent candidate workflow.

**Contribution to Phase Goal:** This delivers the core P0/P1 candidate interaction after the shell exists, while preserving server-authoritative lifecycle, isolated scoring, and source conflict safety.

## Success Criteria

The sequence goal is achieved when:

### Required Deliverables

- [x] **Editor/settings integration**: `webui/src/editor.ts` configures Python Monaco and local non-authoritative preferences.
- [x] **Source recovery/actions**: `webui/src/api.ts`, `webui/src/state.ts`, and `webui/src/views.ts` implement ETag autosave/conflict, history preview/restore, reset, tabs, level navigation, and bounded output.
- [x] **Final action flow**: Run Tests, candidate failure, submit confirmation, expiry locking, stored final results, and repeat-submit rendering are wired to fixed API routes.

### Quality Standards

- [x] **Race safety**: Only one save/evaluation action is active, latest source is flushed before test/submit, and conflicts preserve the user's buffer.
- [x] **Honest content**: Descriptions come only from copied prompts; labels describe local practice tests and never imply official hidden cases.

### Completion Criteria

- [x] All tasks in sequence completed successfully
- [x] Focused verification tasks passed
- [x] Independent review findings addressed
- [x] Relevant documentation updated

## Task Alignment

| Task | Task Objective | Contribution to Sequence Goal |
|------|----------------|-------------------------------|
| 01_integrate_monaco_and_settings.md | Initialize Python Monaco and local editor preferences. | Provides realistic editing without runtime network. |
| 02_implement_autosave_conflicts_history_and_reset.md | Implement source save/conflict/history/reset flows. | Makes candidate work durable and recoverable. |
| 03_implement_tabs_levels_and_navigation.md | Implement prompt tabs, four levels, and navigation state. | Matches the assessment interaction model. |
| 04_implement_test_submit_expiry_and_results.md | Implement testing, submission, expiry, and final result state. | Completes the authoritative action lifecycle. |
| 05_verify_assessment_interactions.md | Verify the integrated editor and assessment actions. | Provides focused evidence before continuity and broad browser tests. |

## Dependencies

### Prerequisites

- 02_ENTRY_AND_SHELL plus candidate-document/API contracts

### Provides

- Feature-complete candidate UI for Playwright journey coverage

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Autosave, expiry, and submit race causes lost or double-scored source | High | High | Serialize saves/evaluations, flush through CAS before final actions, poll authoritative state, and test conflicts/timeout/repeat submit. |

## Progress Tracking

### Milestones

- [x] **Milestone 1**: Monaco and preferences work offline
- [x] **Milestone 2**: Source history/conflict/reset and navigation work
- [x] **Milestone 3**: Test/submit/expiry/final state is integrated and verified

## Quality Gates

### Testing and Verification

- [x] Focused unit/API/browser tests pass
- [x] Integration evidence is recorded
- [x] Performance/resource impact is assessed where relevant

### Code Review

- [x] Independent review is conducted
- [x] Review feedback is addressed
- [x] Festival rules and content boundaries are verified

### Iteration Decision

- [x] Need another iteration? No; all identified findings were resolved in the recorded iteration.
- [x] Follow-up tasks required: None.
