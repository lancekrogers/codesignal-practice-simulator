---
fest_type: sequence
fest_id: 02_entry_and_shell
fest_name: entry and shell
fest_parent: 004_ASSESSMENT_IDE
fest_order: 2
fest_status: completed
fest_created: 2026-09-09T03:13:07.233842-06:00
fest_updated: 2026-09-09T13:34:56.386337-06:00
fest_tracking: true
---


# Sequence Goal: 02_ENTRY_AND_SHELL

**Sequence:** 02_ENTRY_AND_SHELL | **Phase:** 004_ASSESSMENT_IDE | **Status:** Completed

## Sequence Objective

**Primary Goal:** Implement the entry/start contract and responsive assessment shell that displays authoritative session state without creating or mutating an attempt prematurely.

**Contribution to Phase Goal:** This is the candidate-facing structure consumed by editor/action modules and establishes the visible spatial hierarchy, loading/error recovery, and no-pause semantics.

## Success Criteria

The sequence goal is achieved when:

### Required Deliverables

- [x] **Entry flow**: `webui/src/views.ts` renders bootstrap metadata, full/drill choice, rules, no-pause warning, and explicit start confirmation.
- [x] **Assessment shell**: `webui/src/app.ts` and `webui/src/styles.css` render top bar, countdown/save state, level navigation, prompt pane, editor/output regions, and action bar.
- [x] **Accessible recovery states**: `webui/src/a11y.ts` supports keyboard/focus/live-region behavior and screens for reconnect, missing/corrupt selection, expiry, and final state.

### Quality Standards

- [x] **Server authority**: Bootstrap never starts time; only a successful POST creates the attempt, and the timer is derived from server observations.
- [x] **Usable layout**: Role-based controls, visible focus, dialog focus containment, responsive panes, and reduced-motion behavior work at narrow laptop widths.

### Completion Criteria

- [x] All tasks in sequence completed successfully
- [x] Focused verification tasks passed
- [x] Independent review findings addressed
- [x] Relevant documentation updated

## Task Alignment

| Task | Task Objective | Contribution to Sequence Goal |
|------|----------------|-------------------------------|
| 01_build_assessment_entry_flow.md | Build the pre-start full/drill screen and explicit start action. | Protects start and timer semantics. |
| 02_build_responsive_assessment_shell.md | Build the desktop/narrow assessment layout and state indicators. | Provides the candidate workspace. |
| 03_implement_accessibility_and_error_states.md | Add keyboard, focus, live-region, dialog, and recovery behavior. | Makes the shell usable and safe under failure. |
| 04_verify_shell_interaction_and_layout.md | Check visible hierarchy, roles, start semantics, and narrow layout. | Catches shell defects before action integration. |

## Dependencies

### Prerequisites

- 01_EDITOR_ASSETS and phase-003 API bootstrap/start schemas

### Provides

- Stable DOM landmarks, accessible names, and UI state slots for editor/actions

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Client state accidentally starts or changes the authoritative attempt | High | High | Keep start/timer transitions in `webui/src/state.ts` driven by API snapshots; assert no attempt exists before explicit start. |

## Progress Tracking

### Milestones

- [x] **Milestone 1**: Entry renders complete metadata and no-pause choice
- [x] **Milestone 2**: Shell layout renders authoritative loading/active/final states
- [x] **Milestone 3**: Keyboard and responsive checks pass

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
