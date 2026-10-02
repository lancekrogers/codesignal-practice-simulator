---
fest_type: sequence
fest_id: 02_restart_and_abandon
fest_name: restart_and_abandon
fest_parent: 003_ATTEMPT_LIFECYCLE
fest_order: 2
fest_status: completed
fest_created: 2026-09-11T14:32:06.95712-06:00
fest_updated: 2026-09-12T15:46:02.705017-06:00
fest_tracking: true
fest_working_dir: projects/worktrees/codesignal-practice-simulator/cp0002-practice-library
---


# Sequence Goal: 02_restart_and_abandon

**Sequence:** 02_restart_and_abandon | **Phase:** 003_ATTEMPT_LIFECYCLE | **Status:** Pending | **Created:** 2026-09-11T14:32:06-06:00

## Sequence Objective

**Primary Goal:** Implement explicit abandonment and restart with recoverable operation journal and shared CLI/browser lifecycle actions.

**Contribution to Phase Goal:** Delivers R3/R4 fresh practice and R9 recovery without ambiguous source reset or in-place timer changes.

## Success Criteria

The sequence goal is achieved when:

### Required Deliverables

- [ ] **Restart journal:** D001 write-ahead commit intent and idempotent operation UUID completion at `workspace.py:116/:145`.
- [ ] **Shared actions:** Abandon/restart services at `lifecycle.py:82/:132` with CLI and `web/routes.py` validation.

### Quality Standards

- [ ] **Lock ordering:** Workspace → old attempt → replacement; never workspace lock while holding attempt lock.
- [ ] **Preservation:** Old source bytes and original timer unchanged after restart; exactly one replacement per operation.

### Completion Criteria

- [ ] All tasks in sequence completed successfully
- [ ] Quality verification tasks passed
- [ ] Code review completed and issues addressed
- [ ] Documentation updated

## Task Alignment

| Task | Task Objective | Contribution to Sequence Goal |
|------|----------------|-------------------------------|
| 01_restart_journal | Operation record and recovery | Durable restart commit point |
| 02_shared_lifecycle_actions | CLI/web abandon/restart | User-visible explicit transitions |

## Dependencies

### Prerequisites (from other sequences)

- **01_schema_and_review:** Versioned models and persistence dispatch for abandoned/replacement records.

### Provides (to other sequences)

- **Restart/abandon actions:** Used by 03_attempt_history_api routes and 005 restart UX.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Partial restart leaving dual active attempts | Med | High | Inject failures at every journal boundary |
| Submit/restart race double mutation | Med | High | Old-attempt lock serialization tests |

## Progress Tracking

### Milestones

- [ ] **Milestone 1:** Restart journal with recovery helpers
- [ ] **Milestone 2:** Shared CLI/web actions with conflict errors
- [ ] **Milestone 3:** Cross-process and stale-tab tests green

## Quality Gates

### Testing and Verification

- [ ] All unit tests pass
- [ ] Integration tests complete
- [ ] Performance benchmarks met

### Code Review

- [ ] Code review conducted
- [ ] Review feedback addressed
- [ ] Standards compliance verified

### Iteration Decision

- [ ] Need another iteration? No
- [ ] If yes, new tasks created: N/A
