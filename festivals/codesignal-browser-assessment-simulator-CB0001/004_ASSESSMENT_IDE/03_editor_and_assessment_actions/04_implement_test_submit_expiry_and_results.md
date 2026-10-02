---
fest_type: task
fest_id: 04_implement_test_submit_expiry_and_results.md
fest_name: implement test submit expiry and results
fest_parent: 03_editor_and_assessment_actions
fest_order: 4
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:30.137628-06:00
fest_updated: 2026-09-09T17:44:51.623451-06:00
fest_tracking: true
---


# Task: implement test submit expiry and results

## Objective

Implement the separate Run Tests and final Submit workflows, server-derived expiry locking, bounded results, and stored final-state recovery.

## Requirements

- [ ] Run Tests must flush the latest source, call `/api/test`, display bounded per-level results/output, and distinguish candidate failure from transport/internal failure.
- [ ] Submit must confirm consequences, flush source, call `/api/submit` once, render immutable stored results, and handle repeat submit/reload without rescoring.
- [ ] Client timer zero may disable controls optimistically but must refresh authoritative `/api/time`/session state; it cannot create expiry, pause, extend, or reset time.

## Implementation

Follow these steps in order:

1. Add `idle|testing|submitting` action state and a single evaluation lock in `webui/src/state.ts`; disable competing Run/Submit actions while a request is active.
2. Implement `runTests()` and `submitAttempt()` in `webui/src/api.ts`/`webui/src/app.ts`; save via CAS first, map candidate-failure score data to bounded output, and map final `SubmissionResult` to the final screen.
3. Add timeout polling/resynchronization, read-only editor/action rendering, confirmation dialog focus, and authoritative refresh on reconnect/refresh/restart.
4. Test pass/fail practice groups, output cap, save/test race, expiry, cancel/confirm submit, repeat submit, final immutability, and server restart with `npm run test:browser -- actions`.

### Safety and content isolation

Never claim CodeSignal hidden tests, show raw commands/paths, or allow editor/test/submit mutation after final state. Keep scorer output bounded and candidate-safe.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] Run Tests and Submit are visibly distinct and use the correct backend services.
- [ ] Expiry disables illegal actions from server state, and repeat submission returns the stored result without a second score.
- [ ] Focused browser/API tests pass for success, candidate failure, timeout, confirmation, idempotency, and final recovery.
