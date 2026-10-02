---
fest_type: sequence
fest_id: 04_agent_continuity
fest_name: agent continuity
fest_parent: 004_ASSESSMENT_IDE
fest_order: 4
fest_status: completed
fest_created: 2026-09-09T03:13:07.475718-06:00
fest_updated: 2026-09-09T20:55:15.216836-06:00
fest_tracking: true
---


# Sequence Goal: 04_AGENT_CONTINUITY

**Sequence:** 04_AGENT_CONTINUITY | **Phase:** 004_ASSESSMENT_IDE | **Status:** Completed

## Sequence Objective

**Primary Goal:** Keep browser lifecycle actions visible through the existing safe derived terminal surfaces while documenting and enforcing the rule that coaching cannot silently read or edit candidate source.

**Contribution to Phase Goal:** This satisfies B13 without putting coaching into the assessment UI or creating a second lifecycle authority, and gives phase 005 an observable cross-surface contract.

## Success Criteria

The sequence goal is achieved when:

### Required Deliverables

- [x] **Derived-surface synchronization**: Web start/status/time/test/submit paths call `DerivedStatusService.refresh()` through the application boundary and update `STATUS.md` consistently.
- [x] **Agent boundary documentation**: Root/attempt `AGENTS.md`, `COACHING.md`, `docs/agent-safety.md`, and README guidance distinguish safe context/coaching from candidate-source permission.
- [x] **Continuity evidence**: Tests and a real-process rehearsal show browser state is visible in context/status without source or reference leakage.

### Quality Standards

- [x] **Safe default**: Agents may use derived context and user-pasted errors by default, but must ask before candidate code/history access.
- [x] **No hidden mutation**: Coaching text is never imported, executed, scored, or written into `simulation.py`.

### Completion Criteria

- [x] All tasks in sequence completed successfully
- [x] Focused verification tasks passed
- [x] Independent review findings addressed
- [x] Relevant documentation updated

## Task Alignment

| Task | Task Objective | Contribution to Sequence Goal |
|------|----------------|-------------------------------|
| 01_synchronize_terminal_surfaces.md | Audit and wire derived status refresh for browser actions. | Makes browser activity visible to terminal agents. |
| 02_document_safe_coaching_workflow.md | Document the parallel practice/coaching workflow and boundaries. | Makes the operational contract executable by agents. |
| 03_verify_browser_terminal_continuity.md | Verify cross-surface state and content isolation. | Proves coaching continuity without candidate-code access. |

## Dependencies

### Prerequisites

- 03_EDITOR_AND_ASSESSMENT_ACTIONS and existing rendering/agent policy

### Provides

- A documented and tested terminal/browser continuity contract for phase 005

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| A browser route exposes or silently changes candidate content through status refresh | Medium | High | Keep rendering derived-only, inspect allowed fields, and assert source/reference strings are absent from status/context responses. |

## Progress Tracking

### Milestones

- [x] **Milestone 1**: All browser mutations refresh derived status
- [x] **Milestone 2**: Agent docs state permission boundaries
- [x] **Milestone 3**: Real-process continuity and leakage checks pass

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
