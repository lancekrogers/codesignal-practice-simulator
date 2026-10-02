---
fest_type: task
fest_id: 03_implement_tabs_levels_and_navigation.md
fest_name: implement tabs levels and navigation
fest_parent: 03_editor_and_assessment_actions
fest_order: 3
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:30.01622-06:00
fest_updated: 2026-09-09T15:32:44.74686-06:00
fest_tracking: true
---


# Task: implement tabs levels and navigation

## Objective

Implement the four-level assessment navigation and Description/History/Rules/Info views using only safe candidate-facing data.

## Requirements

- [ ] Level navigation must select 1–4, preserve the one cumulative `simulation.py`, and display reached/completed/test status from authoritative session/score data.
- [ ] Description must call `/api/prompts/{1..4}` for the selected copied prompt; History is candidate-source history only; Rules/Info are first-party static guidance.
- [ ] Previous/Next/Skip controls must never start, pause, reset, or extend the attempt and must remain usable/read-only according to lifecycle state.

## Implementation

Follow these steps in order:

1. Add selected-level/tab state to `webui/src/state.ts` and accessible tab/level controls in `webui/src/views.ts`; fetch only the selected prompt and cache it in disposable UI state.
2. Render score markers from `SessionState.score` and never label a local group as an official hidden test; preserve editor model content while switching levels.
3. Connect previous/next/Skip to selection changes only, with focus movement to the prompt/editor as appropriate; ensure refresh reconstructs selection without changing server state.
4. Test all four prompts, tab keyboard behavior, level status markers, source preservation, inaccessible levels, and forbidden-content sentinels with `npm run test:browser -- navigation`.

### Safety and content isolation

Do not fetch cache paths, solution/study/vendor files, raw `test_simulation.py`, or scorer internals. Prompt rendering is allowed only through the fixed PromptService-backed route.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] All four levels and four tabs are keyboard-accessible and display distinct safe content.
- [ ] Switching/navigation preserves source and does not alter lifecycle/timer state.
- [ ] Focused navigation/content-isolation tests pass with honest practice-test wording.
