---
fest_type: task
fest_id: 01_lock_playwright_and_browser_fixture.md
fest_name: lock playwright and browser fixture
fest_parent: 01_browser_harness
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:30.759098-06:00
fest_updated: 2026-09-09T21:45:42.364463-06:00
fest_tracking: true
---


# Task: lock Playwright and browser fixture

## Objective

Lock browser tooling and create an isolated fixture that starts the real packaged server against a synthetic temporary workspace with controllable dependencies.

## Requirements

- [x] Add the selected Playwright version to `webui/package-lock.json`/browser test package and pin the Chromium install expectation.
- [x] Implement `browser-tests/fixtures/server.ts` (or the chosen project-equivalent) to create synthetic seven-record fixture/workspace, inject fake clock/token/browser opener, start loopback server, and clean up.
- [x] Ensure each test gets a unique temporary root and cannot select a user's `active.json` or read the repository cache.

## Implementation

Follow these steps in order:

1. Reuse Python fixture patterns from `tests/test_cli.py`/`tests/test_workspace.py` and the server injection seams from `src/codesignal_practice_simulator/web/server.py`; create only candidate-facing synthetic files.
2. Expose fixture handles for base URL, capability token, attempt ID, workspace path, fake-clock controls, and cleanup; wait for readiness through HTTP rather than fixed sleeps.
3. Add a minimal test that loads bootstrap and closes the server in `afterEach`/fixture teardown, including cleanup after a failed test.
4. Run `npm ci`, install the locked browser, and execute the harness smoke command with external network denied.

### Safety and content isolation

Never point the fixture at `.cache/codesignal-fixtures`, a real project attempt, or a campaign root. Do not log capability tokens or preserve successful traces.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [x] The locked browser fixture starts and stops the actual local app with isolated synthetic data.
- [x] Fake clock/token and temporary workspace controls are available to tests.
- [x] Smoke and failure-cleanup tests pass with no unexpected network requests.
