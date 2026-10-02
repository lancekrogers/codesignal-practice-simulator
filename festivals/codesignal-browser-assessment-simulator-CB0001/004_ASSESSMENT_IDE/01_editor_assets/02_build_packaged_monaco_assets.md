---
fest_type: task
fest_id: 02_build_packaged_monaco_assets.md
fest_name: build packaged monaco assets
fest_parent: 01_editor_assets
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:29.025302-06:00
fest_updated: 2026-09-09T07:04:31.321804-06:00
fest_tracking: true
---


# Task: build packaged Monaco assets

## Objective

Bundle the first-party browser shell, Monaco Python editor, and explicit worker entries into package resources that the Python server can serve offline.

## Requirements

- [ ] Implement `webui/build.mjs` and source entries under `webui/src/` for application code, editor worker, and language worker with same-origin manifest URLs.
- [ ] Generate `src/codesignal_practice_simulator/web/static/index.html`, hashed JS/CSS/worker assets, `manifest.json`, and license/provenance output without requiring Node at runtime.
- [ ] Keep CSP compatible with the tested Monaco worker strategy; use a read-only source fallback and disable mutation if Monaco initialization fails.

## Implementation

Follow these steps in order:

1. Define entry modules `webui/src/app.ts`, `webui/src/api.ts`, `webui/src/state.ts`, `webui/src/views.ts`, `webui/src/editor.ts`, and `webui/src/styles.css`; configure esbuild outputs and a manifest consumed by `src/codesignal_practice_simulator/web/resources.py`.
2. Configure Monaco worker URL resolution to same-origin fingerprinted assets, and include only the Python language/editor features needed for syntax, indentation, autocomplete, find, undo/redo, themes, and settings.
3. Copy generated files atomically into the planned package static directory; make the server serve only manifest-listed paths and set immutable cache headers for hashed assets.
4. Run `npm run build`, inspect the manifest and output paths, then load the generated `index.html` through the phase-003 server with network disabled.

### Safety and content isolation

Generated files may contain licensed editor/application runtime only. Do not bundle prompts, tests, cache records, candidate source, hidden-test claims, or external CDN URLs.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] Build output contains the application, Monaco, workers, manifest, and required notices with no runtime Node requirement.
- [ ] The package resource loader can resolve every manifest entry and rejects unlisted/traversal paths.
- [ ] A network-denied server load reaches the app and provides a safe read-only fallback when editor initialization is forced to fail.
