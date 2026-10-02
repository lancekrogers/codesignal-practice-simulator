---
fest_type: task
fest_id: 02_implement_browser_helpers_and_network_guard.md
fest_name: implement browser helpers and network guard
fest_parent: 01_browser_harness
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:30.918474-06:00
fest_updated: 2026-09-09T22:08:36.160453-06:00
fest_tracking: true
---


# Task: implement browser helpers and network guard

## Objective

Create reusable role-first page helpers and diagnostic/network guards so journey tests assert observable behavior consistently.

## Requirements

- [x] Add page objects under the project-equivalent `webui/tests/pages/` for entry, assessment shell, editor/settings, dialogs, output, and final results.
- [x] Prefer accessible role/name locators; use stable `data-testid` only for ambiguous panes or generated editor regions.
- [x] Configure Playwright to fail on unexpected requests, console/page errors, and forbidden response content while retaining trace/screenshot only on failure.

## Implementation

Follow these steps in order:

1. Implement helpers around the stable accessible names planned in `webui/src/views.ts`; centralize API waits and authoritative state polling rather than duplicating selectors in specs.
2. Add `browser-tests/fixtures/network.ts` to allow only loopback API/static requests and record request URL/method/resource type; fail on CDN, file, proxy, or external requests.
3. Add diagnostic hooks for console errors, uncaught page errors, failed requests, and bounded response-body/content scans; configure `trace: 'retain-on-failure'` and failure screenshot only.
4. Run the helper smoke with `npm run test:browser -- harness` and inspect that successful runs leave no trace, screenshot, cache, or attempt artifacts.

### Safety and content isolation

Response scans must use synthetic forbidden sentinels and never dump candidate/reference content. Keep token/header values redacted in diagnostics.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [x] All common pages expose role-first actions and authoritative wait helpers.
- [x] Unexpected network/console/page errors fail tests and diagnostics are failure-only/redacted.
- [x] Harness helper smoke passes without leaving generated artifacts in Git.
