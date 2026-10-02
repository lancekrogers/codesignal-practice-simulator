---
fest_type: task
fest_id: 01_build_assessment_entry_flow.md
fest_name: build assessment entry flow
fest_parent: 02_entry_and_shell
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:29.278765-06:00
fest_updated: 2026-09-09T10:51:28.694483-06:00
fest_tracking: true
---


# Task: build assessment entry flow

## Objective

Build the pre-assessment screen that explains the local practice session and creates an attempt only after explicit full/drill confirmation and Start.

## Requirements

- [ ] `webui/src/views.ts` must render assessment name, duration, four-level outline, rules, no-pause warning, practice framing, full/drill controls, and explicit start confirmation.
- [ ] `webui/src/state.ts` and `webui/src/api.ts` must call bootstrap first and POST `/api/attempts` only from the confirmed Start action.
- [ ] Missing fixture, invalid bootstrap, start conflict, and reconnect errors must produce actionable safe messages without revealing paths or creating client-owned lifecycle state.

## Implementation

Follow these steps in order:

1. Define the `booting` and `entry` states in `webui/src/state.ts`; map `/api/bootstrap` data into view models and render level metadata without reading prompt/reference files directly.
2. Add accessible full/drill radio/buttons, a no-pause explanation, confirmation dialog, and Start handler that sends only the selected mode/duration; transition to `attempt` only on authoritative success.
3. Show practice language such as local assessment checks and explicitly avoid CodeSignal logos, copied wording, or hidden-test claims.
4. Run `npm run check` and a focused browser smoke test that asserts no attempt exists before Start and exactly one active session exists after Start.

### Safety and content isolation

Bootstrap and entry views must not preload candidate source, copied tests, solution/study/vendor material, or arbitrary paths. Never store timer/lifecycle authority in local storage.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] No server attempt or timer exists after bootstrap/choice/cancel alone.
- [ ] A confirmed Start creates the selected full/drill profile and renders the server session/deadline.
- [ ] Entry/error smoke tests pass with accessible controls and no forbidden content in DOM text.
