---
fest_type: task
fest_id: 05_verify_assessment_interactions.md
fest_name: verify assessment interactions
fest_parent: 03_editor_and_assessment_actions
fest_order: 5
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:30.261066-06:00
fest_updated: 2026-09-09T17:50:18.974645-06:00
fest_tracking: true
---


# Task: verify assessment interactions

## Objective

Run a focused integration review of the complete editor/action sequence before broad Playwright journey coverage.

## Requirements

- [x] Exercise the real packaged UI against the fixed API for source editing, settings, tabs/levels, autosave/conflict, history/reset, Run Tests, Submit, expiry, refresh, and restart.
- [x] Assert accessible names, focus restoration, save/action indicators, bounded output, honest local-test labels, and server-authoritative session/time.
- [x] Use synthetic fixtures and failure-only evidence; no implementation task is marked complete by this verification document.

## Implementation

Follow these steps in order:

1. Use the shared page objects planned under `browser-tests/pages/` and extend focused specs rather than adding a second fixture implementation.
2. Run `npm run test:browser -- editor actions`, `python3 -m unittest tests.test_web_server tests.test_candidate_documents -v`, and `npm run check`; correlate failures to API versus UI state.
3. Force stale ETag, fake clock expiry, candidate group failure, server restart, and Monaco initialization failure; assert each recovery message and persisted state.
4. Review the DOM and network log for forbidden paths/content and inspect only failure traces/screenshots before cleanup.

### Safety and content isolation

The test must fail if source/history includes non-candidate bytes, if the UI calls an undocumented route, or if an action bypasses the API/CAS contract.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [x] Focused editor/action tests pass across active, conflict, expired, submitted, and restart states.
- [x] All browser requests are documented API/static requests and all accessible critical actions have stable names.
- [x] Failures are triaged into implementation tasks without changing task completion status in the festival.

## Verification evidence

- `npm run test:browser -- editor actions`: 32 passed.
- Full Playwright regression: 76 passed, serially, against the real packaged UI and synthetic fixture server.
- `npm run check`, asset build, and packaged-asset integrity checks passed.
- Full Python regression: 304 passed, 1 skipped, and 190 subtests passed.
- The task's pre-refactor unittest module names no longer exist. Their current five web-server and four candidate-document modules passed 46 tests through `unittest`.
- Forced stale ETag/conflict, candidate failure, fake-clock expiry, submit/reload, real process restart, and Monaco initialization failure cases passed.
- The shared browser policy rejects undocumented same-origin routes, failed or blocked static resources, console/page errors, and forbidden fixture content. Source mutations remain CAS guarded.
- `browser-tests/pages/` is scheduled for phase 005 and is not present yet. This verification reused the single existing `webui/tests/browser_harness.mjs` and `fixture_server.py` implementation; it did not add a competing fixture layer.
- A final read-only Cursor judge review returned `APPROVE` with no missing verification or implementation regression.
