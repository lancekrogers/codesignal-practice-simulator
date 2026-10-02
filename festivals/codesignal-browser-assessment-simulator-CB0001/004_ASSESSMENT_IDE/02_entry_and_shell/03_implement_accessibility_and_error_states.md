---
fest_type: task
fest_id: 03_implement_accessibility_and_error_states.md
fest_name: implement accessibility and error states
fest_parent: 02_entry_and_shell
fest_order: 3
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:29.527614-06:00
fest_updated: 2026-09-09T12:34:47.858802-06:00
fest_tracking: true
---


# Task: implement accessibility and error states

## Objective

Make the shell keyboard-usable and resilient to API/editor failures with correct focus, announcements, and bounded recovery states.

## Requirements

- [ ] `webui/src/a11y.ts` must provide visible focus, keyboard navigation for levels/tabs/actions, live-region announcements for save/results, and focus-contained Escape-close dialogs.
- [ ] Error views must distinguish conflict, unavailable session, expired/submitted read-only, candidate test failure, and internal-safe failure without exposing stack traces.
- [ ] Support reduced motion and WCAG AA contrast targets in `webui/src/styles.css`, with focus restored to the invoking control after dialogs/results.

## Implementation

Follow these steps in order:

1. Implement roving/standard tab behavior for level and info tabs, `aria-selected`/`aria-controls`, and an `aria-live` status region in `webui/src/views.ts`/`webui/src/a11y.ts`.
2. Create a dialog helper that captures the opener, focuses the first actionable control, traps Tab, closes on Escape, and restores focus after confirmation/cancel.
3. Map API error codes in `webui/src/api.ts` to user-actionable messages and recovery buttons; keep source buffer visible on conflict and lock mutation controls after authoritative expiry.
4. Run a keyboard-only browser smoke, inspect focus order at narrow width, and run `npm run check` plus a contrast/style lint if configured.

### Safety and content isolation

Never announce or render candidate source, test output, or prompt bytes in a generic error. Do not suggest reading solution/study/vendor content as recovery.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] Every shell action is reachable by keyboard with visible focus and sensible focus restoration.
- [ ] Save/results/conflict/expiry messages are announced without duplicate or misleading lifecycle claims.
- [ ] Error and dialog tests pass with no raw exception/path leakage.
