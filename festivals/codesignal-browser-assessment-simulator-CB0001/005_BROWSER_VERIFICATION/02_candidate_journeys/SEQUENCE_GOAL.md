---
fest_type: sequence
fest_id: 02_candidate_journeys
fest_name: candidate journeys
fest_parent: 005_BROWSER_VERIFICATION
fest_order: 2
fest_status: completed
fest_created: 2026-09-09T03:13:07.724456-06:00
fest_updated: 2026-09-10T11:16:20.565365-06:00
fest_tracking: true
---


# Sequence Goal: 02_CANDIDATE_JOURNEYS

**Sequence:** 02_CANDIDATE_JOURNEYS | **Phase:** 005_BROWSER_VERIFICATION | **Status:** Pending

## Sequence Objective

**Primary Goal:** Exercise every consequential candidate journey and boundary in a real browser, including races, failures, expiry, recovery, accessibility, responsive use, security, offline assets, and terminal continuity.

**Contribution to Phase Goal:** This converts B01-B19 into visible evidence and supplies the release reviewers with reproducible proof that the simulator is useful and safe in practice.

## Success Criteria

The sequence goal is achieved when:

### Required Deliverables

- [ ] **Core journey suite**: Playwright tests cover entry/full-drill start, timer, levels/tabs, Monaco settings, autosave/conflict, history/reset, refresh, and restart.
- [ ] **Action/recovery suite**: Tests cover passing/failing practice checks, safe output, expiry, submit confirmation/idempotency, final state, and terminal status sync.
- [ ] **Boundary/accessibility suite**: Tests cover keyboard/focus/live regions, narrow layout, invalid token/origin/routes/methods/bodies, headers, forbidden content, and zero unexpected network requests.

### Quality Standards

- [ ] **Visible outcomes**: Assertions use roles, accessible names, live-region text, bounded output, and stored result state rather than private implementation details.
- [ ] **Negative coverage**: Candidate failure, stale CAS, expiry, malformed requests, forbidden content, and network violations are explicitly asserted.

### Completion Criteria

- [ ] All tasks in sequence completed successfully
- [ ] Focused verification tasks passed
- [ ] Independent review findings addressed
- [ ] Relevant documentation updated

## Task Alignment

| Task | Task Objective | Contribution to Sequence Goal |
|------|----------------|-------------------------------|
| 01_cover_entry_editor_and_recovery_journey.md | Cover entry through editing, autosave, history/reset, navigation, and refresh. | Proves the main active-session flow. |
| 02_cover_test_expiry_submit_and_restart_journey.md | Cover test outcomes, expiry, submit idempotency, restart, and continuity. | Proves final-action correctness. |
| 03_cover_accessibility_security_and_offline_journey.md | Cover keyboard/responsive/a11y and HTTP/offline boundaries. | Proves usability and isolation. |
| 04_review_browser_evidence.md | Review artifacts and map each journey to acceptance criteria. | Creates a release-ready evidence index. |

## Dependencies

### Prerequisites

- 01_BROWSER_HARNESS and feature-complete phase-004 UI

### Provides

- Real-browser pass/fail evidence and focused regression commands for release review

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Timing-sensitive tests are flaky or mask server-authority defects | High | High | Use injected clocks and polling for authoritative responses; assert no-pause and expiry through server snapshots, not sleeps alone. |

## Progress Tracking

### Milestones

- [ ] **Milestone 1**: Core active journey passes
- [ ] **Milestone 2**: Final/recovery/race journeys pass
- [ ] **Milestone 3**: A11y/security/offline evidence is indexed

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
