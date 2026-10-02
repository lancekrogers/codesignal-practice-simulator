---
fest_type: sequence
fest_id: 01_browser_harness
fest_name: browser harness
fest_parent: 005_BROWSER_VERIFICATION
fest_order: 1
fest_status: completed
fest_created: 2026-09-09T03:13:07.599711-06:00
fest_updated: 2026-09-10T09:33:07.364338-06:00
fest_tracking: true
---


# Sequence Goal: 01_BROWSER_HARNESS

**Sequence:** 01_BROWSER_HARNESS | **Phase:** 005_BROWSER_VERIFICATION | **Status:** Pending

## Sequence Objective

**Primary Goal:** Provide deterministic Playwright infrastructure that starts the real local app against isolated synthetic workspaces, controls time and capability inputs, denies network, and emits useful failure-only diagnostics.

**Contribution to Phase Goal:** A shared harness prevents individual journey tests from bypassing package, server, timer, cleanup, or network-boundary behavior and makes later evidence reproducible.

## Success Criteria

The sequence goal is achieved when:

### Required Deliverables

- [ ] **Locked browser fixture**: `browser-tests/fixtures/server.ts` or the chosen locked test location creates temporary fixtures, starts the packaged app, injects clock/token seams, and cleans up.
- [ ] **Page helpers**: `browser-tests/pages/` selects by accessible roles/names and exposes reusable entry, IDE, dialog, output, and final-result actions.
- [ ] **Diagnostics/network guard**: Playwright config denies unexpected requests, captures console/page failures, and saves traces/screenshots only on failure.

### Quality Standards

- [ ] **Isolation**: Every test owns a temporary workspace and synthetic seven-record fixture; no test depends on a user's active attempt.
- [ ] **Determinism**: Clock, token, port, browser version, and cleanup behavior are controlled and recorded.

### Completion Criteria

- [ ] All tasks in sequence completed successfully
- [ ] Focused verification tasks passed
- [ ] Independent review findings addressed
- [ ] Relevant documentation updated

## Task Alignment

| Task | Task Objective | Contribution to Sequence Goal |
|------|----------------|-------------------------------|
| 01_lock_playwright_and_browser_fixture.md | Lock Playwright/Chromium and build the isolated server fixture. | Establishes repeatable test setup. |
| 02_implement_browser_helpers_and_network_guard.md | Add role-first page objects and network/diagnostic hooks. | Standardizes observable assertions. |
| 03_verify_deterministic_harness.md | Run fixture smoke tests and failure-cleanup checks. | Proves the harness itself is trustworthy. |

## Dependencies

### Prerequisites

- 004_ASSESSMENT_IDE feature-complete UI and server launch contract

### Provides

- Reusable Playwright fixture/page helpers for all candidate journeys

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Tests pass through mocked UI seams but miss real package/server behavior | Medium | High | Start the actual local server and load packaged assets; mock only injected clock/token controls. |

## Progress Tracking

### Milestones

- [ ] **Milestone 1**: Locked browser dependency and fixture exist
- [ ] **Milestone 2**: Helpers and network denial are reusable
- [ ] **Milestone 3**: Harness smoke/cleanup checks pass

## Quality Gates

### Testing and Verification

- [ ] Focused unit/API/browser tests pass
- [ ] Integration evidence is recorded
- [ ] Performance/resource impact is assessed where relevant

### Code Review

- [ ] Independent review is conducted
- [ ] Review feedback is addressed
- [ ] Festival rules and content boundaries are verified

### Iteration Decision

- [ ] Need another iteration? No; create targeted follow-up tasks only if execution evidence identifies a defect or unmet criterion.
- [ ] If yes, new tasks created: None at planning time; record exact task paths when evidence requires iteration.
