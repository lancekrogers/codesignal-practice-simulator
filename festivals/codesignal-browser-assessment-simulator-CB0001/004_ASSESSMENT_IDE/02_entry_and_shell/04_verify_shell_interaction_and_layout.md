---
fest_type: task
fest_id: 04_verify_shell_interaction_and_layout.md
fest_name: verify shell interaction and layout
fest_parent: 02_entry_and_shell
fest_order: 4
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:29.647777-06:00
fest_updated: 2026-09-09T12:52:12.642611-06:00
fest_tracking: true
---


# Task: verify shell interaction and layout

## Objective

Verify the entry and shell against the API contract, responsive layout, accessibility expectations, and server-authoritative start/timer behavior.

## Requirements

- [ ] Use the real packaged page/server with synthetic temporary workspace and accessible-role selectors.
- [ ] Cover pre-start no-attempt state, full/drill choice, explicit Start, shell landmarks, timer resynchronization, loading/reconnect/final states, and narrow viewport layout.
- [ ] Record failures with screenshot/trace only when needed and remove temporary artifacts after the run.

## Implementation

Follow these steps in order:

1. Add or extend the focused browser test near `browser-tests/pages/entry-page.ts` and `browser-tests/pages/assessment-page.ts`; assert role/name contracts rather than CSS classes.
2. Intercept no requests except the documented loopback API/static assets; assert `/api/attempts` is absent before Start and that refresh reads the same attempt/deadline.
3. Run keyboard traversal through entry, shell tabs, level navigation, and dialogs; use a narrow viewport and assert panes remain reachable without horizontal clipping.
4. Run the focused command `npm run test:browser -- shell` (or the locked equivalent) and `npm run check`; inspect console errors.

### Safety and content isolation

Use synthetic prompts/source and assert DOM/network artifacts contain no forbidden sentinels, paths, tokens, or scorer internals.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] Focused shell tests pass for full/drill entry, explicit start, timer observation, refresh, errors, and responsive layout.
- [ ] Keyboard/focus assertions pass and all unexpected network/console errors fail the test.
- [ ] Evidence is failure-only and the temporary workspace is cleaned.
