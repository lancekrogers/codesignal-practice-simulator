---
fest_type: sequence
fest_id: 01_library_and_restart
fest_name: library_and_restart
fest_parent: 005_PRACTICE_EXPERIENCE
fest_order: 1
fest_status: completed
fest_created: 2026-09-11T14:32:06.95712-06:00
fest_updated: 2026-09-12T22:09:31.851835-06:00
fest_tracking: true
fest_working_dir: projects/worktrees/codesignal-practice-simulator/cp0002-practice-library
---


# Sequence Goal: 01_library_and_restart

**Sequence:** 01_library_and_restart | **Phase:** 005_PRACTICE_EXPERIENCE | **Status:** Pending | **Created:** 2026-09-11T14:32:06-06:00

## Sequence Objective

**Primary Goal:** Add library navigation and distinct End/Restart/Reset UX wired to 003 lifecycle APIs with capability-safe routing.

**Contribution to Phase Goal:** Delivers R1 selection, R3/R4 repeat flows, and R10 primary navigation for practice entry.

## Success Criteria

The sequence goal is achieved when:

### Required Deliverables

- [x] **Routes and catalog UI:** Validated route model at `webui/src/app.ts:51/:97` with library and attempt views. Delivered as `webui/src/router.ts` (`parseRoute` :17, `navigateTo` :82), `webui/src/app.ts` (`showRoute` :84, `showLibrary` :137, `showAttemptRoute` :195, `reconnect` :260), `webui/src/library_view.ts` (`renderLibrary` :34, `renderAttemptEntry` :140), server shell routing `web/routes.py::is_shell_path` :413. Evidence: results/routes_and_catalog_ui.md; `webui/tests/library_routes.spec.mjs` (6 journeys); `tests/test_web_server_static.py` (8 OK). Commit c72c8ab.
- [x] **Restart UX:** End attempt and Restart confirmations through operation locks; Reset source distinct. Delivered as `webui/src/attempt_lifecycle_actions.ts` (`endAttempt` :38, `restartAttempt` :49, `performRestart` :101) with the `lifecycle` lease kind and the "Reset source" / "End attempt" / "Restart" action bar in `attempt_panes.ts`. Evidence: results/restart_ux.md; `webui/tests/restart_end.spec.mjs` (6 journeys incl. on-disk bytes and a real fixture process restart). Commit c72c8ab.

### Quality Standards

- [x] **No accidental timer start:** Start requires explicit confirmation after library selection. Proven: zero POST/PUT on library load, selection, dialog open/cancel, direct attempt address, back/forward and history shells; the only POST is the confirmed start (`library_routes.spec.mjs`).
- [x] **Saved work preserved:** Restart/abandon never lose saved old bytes; unsaved buffer gated. Proven: old `simulation.py` bytes identical after restart and end; failed saves lead to the explicit discard dialog and the stored source keeps only the saved marker (`restart_end.spec.mjs`).

### Completion Criteria

- [x] All tasks in sequence completed successfully (01_routes_and_catalog_ui, 02_restart_ux)
- [x] Quality verification tasks passed (results/testing.md: unit 454 OK, browser 187 passed, frontend passed, assets verified)
- [x] Code review completed and issues addressed (results/review.md, results/iterate.md: one fix, one nit left with rationale)
- [x] Documentation updated (`docs/cli-contract.md`: Browser routes; Attempt actions in the browser and their CLI equivalents)

## Task Alignment

| Task | Task Objective | Contribution to Sequence Goal |
|------|----------------|-------------------------------|
| 01_routes_and_catalog_ui | Library/history route shell | Navigation and catalog readiness |
| 02_restart_ux | End/Restart/Reset controls | Explicit repeat practice UX |

## Dependencies

### Prerequisites (from other sequences)

- **003/02:** Abandon/restart APIs with operation UUID.
- **004/01:** Catalog GET and readiness metadata.

### Provides (to other sequences)

- **Navigation model:** Used by 02_history_and_review for back/stack preservation.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Timer starts on deep link | Med | High | Browser tests on direct URLs |
| Restart loses unsaved editor text | Med | High | Save-or-discard gate tests |

## Progress Tracking

### Milestones

- [x] **Milestone 1:** Library route with catalog cards (`renderLibrary`, three exercises with readiness badges)
- [x] **Milestone 2:** Attempt toolbar with three distinct actions (Reset source, End attempt, Restart)
- [x] **Milestone 3:** Synthetic browser restart proofs (`restart_end.spec.mjs`, 6 passed)

## Quality Gates

### Testing and Verification

- [x] All unit tests pass (454 OK, 1 skipped)
- [x] Integration tests complete (browser 187 passed with locked privacy reporters)
- [x] Performance benchmarks met (none defined for this sequence; the bounded page and asset checks pass)

### Code Review

- [x] Code review conducted (Cursor claude-sonnet-5-thinking-high, read-only; results/review.md)
- [x] Review feedback addressed (results/iterate.md)
- [x] Standards compliance verified (no framework router; fixed error copy; no path or token in DOM or URL)

### Iteration Decision

- [x] Need another iteration? No
- [x] If yes, new tasks created: N/A

Sequence commit: c72c8ab on `cp0002-practice-library` (`fest commit --no-root`, not pushed).
