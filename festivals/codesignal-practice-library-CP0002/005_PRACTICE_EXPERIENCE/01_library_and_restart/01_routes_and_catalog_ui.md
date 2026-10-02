---
fest_type: task
fest_id: 01_routes_and_catalog_ui.md
fest_name: routes_and_catalog_ui
fest_parent: 01_library_and_restart
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-11T14:32:19.009153-06:00
fest_updated: 2026-09-12T21:32:26.304724-06:00
fest_tracking: true
---


# Task: routes_and_catalog_ui

## Objective

Extend `webui/src/app.ts` and state/views with validated library, attempt, history, and review navigation that preserves capability capture, reload/back/forward reconstruction, and metadata-only entry without accidental timer start.

## Requirements

- [ ] Read and apply **D004_history_api_and_ux.md** (route model, library screen, navigation/error states).
- [ ] Extend `webui/src/app.ts` near `:51` and `:97` with a small validated route model (library, attempt, history, review) without external router framework.
- [ ] Library shows catalog readiness/setup, active session summary, History entry, and start confirmation before timer begins.
- [ ] Preserve capability capture on all routes; never put source or tokens into route state.
- [ ] Reconstruct state on reload, back, and forward; handle unknown routes with actionable recovery.
- [ ] Test keyboard focus to screen headings, empty/loading/failure states, and that listing/navigation never requests source content.

## Implementation

1. **Route table** — Define parse/serialize helpers for `/`, `/attempt/:id`, `/history`, `/history/review/:id` (exact paths per existing web server static pattern).
2. **State store** — Extend existing views/state modules to fetch catalog and active attempt summary from APIs built in 003/004.
3. **Library view** — Render exercise cards with readiness badges; Start opens confirmation modal; Resume navigates to active attempt.
4. **Navigation hooks** — Listen to `popstate`; on load, parse URL and fetch required metadata only.
5. **Accessibility** — Move focus to screen `h1` on route change; trap/restore focus in dialogs per D004.
6. **Tests** — Add synthetic browser or DOM tests for unknown route, empty catalog, failed fetch retry, and proof timer not started until confirmed.

### Affected files

- `webui/src/app.ts`
- `webui/src/` state/view modules as needed
- `webui/tests/` or Playwright specs (synthetic fixtures only)

### Negative cases to prove

- Direct URL to attempt does not start timer without explicit user continue.
- Unknown assessment/version in URL → error screen with back to library.
- History navigation does not set reviewed attempt as active selection.
- Capability missing → existing auth/error path, no partial UI leak.

### Commands and evidence

```bash
just check frontend
just check browser
```

## Done When

- [ ] All requirements met
- [ ] Library and route navigation work with reload/back/forward and metadata-only fetches
- [ ] Browser/DOM tests pass with evidence that timer start requires confirmation
