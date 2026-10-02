---
fest_type: task
fest_id: 01_integrate_monaco_and_settings.md
fest_name: integrate monaco and settings
fest_parent: 03_editor_and_assessment_actions
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:29.769399-06:00
fest_updated: 2026-09-09T13:55:52.70088-06:00
fest_tracking: true
---


# Task: integrate Monaco and settings

## Objective

Initialize the locally bundled Monaco editor in Python mode with the requested editing behavior and non-authoritative local preferences.

## Requirements

- [ ] `webui/src/editor.ts` must configure Python language, line numbers, indentation, bracket support, find, undo/redo, autocomplete, theme, font size 12–22px, tab size 2/4/8, minimap, word wrap, and auto-brackets.
- [ ] Preferences may use browser local storage only and must not store lifecycle, source authority, ETags, or attempt selection as truth.
- [ ] Editor initialization failure must show the persisted source read-only with an actionable message and disable source mutations rather than silently losing work.

## Implementation

Follow these steps in order:

1. Load the source/ETag from `webui/src/api.ts`, create Monaco in the editor pane from `webui/src/editor.ts`, and set the initial model value without marking it dirty.
2. Expose a settings dialog with validated values and persist only a versioned `simulator-editor-preferences` object; reapply preferences on model recreation.
3. Configure same-origin worker URLs from the generated manifest and wire Monaco change events to `webui/src/state.ts` dirty status; use accessible labels for settings.
4. Run an offline browser test for syntax/edit/find/undo/redo/settings and force worker/editor failure to assert read-only fallback; run `npm run check`.

### Safety and content isolation

Monaco must load from packaged assets only. Never send keystrokes, source, or settings to telemetry/CDN; do not import test/reference content into the editor.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] The editor provides the requested Python editing interactions without network requests.
- [ ] Preferences persist across refresh while session/time/source authority comes from the server.
- [ ] Initialization failure preserves visible source and disables mutation with a clear accessible error.
