---
fest_type: task
fest_id: 02_build_responsive_assessment_shell.md
fest_name: build responsive assessment shell
fest_parent: 02_entry_and_shell
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:29.407755-06:00
fest_updated: 2026-09-09T11:51:04.738753-06:00
fest_tracking: true
---


# Task: build responsive assessment shell

## Objective

Implement the CodeSignal-familiar but first-party assessment layout around authoritative browser state.

## Requirements

- [ ] `webui/src/app.ts` and `webui/src/styles.css` must render compact title/timer/save/connection/settings header, four-level navigation, prompt pane, editor pane, output drawer, and bottom action bar.
- [ ] Use semantic landmarks and accessible names for Description, History, Rules, Info, Run Tests, navigation/Skip, Reset, and green Submit actions.
- [ ] Render server-derived active/expired/submitted/loading/reconnect/final states without allowing layout code to mutate lifecycle state.

## Implementation

Follow these steps in order:

1. Implement `renderAttemptShell()` in `webui/src/views.ts` and mount it from `webui/src/app.ts`; reserve stable `data-testid` values only for ambiguous panes while controls use roles/names.
2. Add CSS grid/flex layouts for desktop and narrow laptop widths, resizable prompt/output regions, sticky action bar, visible save/connection state, and reduced-motion media handling.
3. Have `webui/src/state.ts` compute display countdown from the latest `/api/time` observation/deadline and schedule resynchronization; navigation changes selected level only.
4. Run the shell browser smoke at desktop and a narrow viewport, assert all landmarks/actions are visible or intentionally scrollable, and run `npm run check`.

### Safety and content isolation

Do not render raw server exceptions, internal paths, scorer commands, or unbounded test output in the shell. Keep selection/UI state separate from `SessionState` lifecycle authority.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] The shell has the planned spatial regions and accessible controls at desktop and narrow widths.
- [ ] Countdown/save/connection indicators update from API snapshots and never pause/extend/reset the server session.
- [ ] Loading, reconnect, expired, submitted, and final states are reachable and safe.
