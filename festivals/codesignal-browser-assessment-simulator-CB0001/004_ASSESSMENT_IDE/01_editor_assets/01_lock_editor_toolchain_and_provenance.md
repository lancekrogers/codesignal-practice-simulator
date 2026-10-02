---
fest_type: task
fest_id: 01_lock_editor_toolchain_and_provenance.md
fest_name: lock editor toolchain and provenance
fest_parent: 01_editor_assets
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:28.90259-06:00
fest_updated: 2026-09-09T05:57:03.009414-06:00
fest_tracking: true
---


# Task: lock editor toolchain and provenance

## Objective

Create the reproducible frontend workspace and provenance records for Monaco 0.56.0, esbuild, and locked Playwright tooling.

## Requirements

- [ ] Add `webui/package.json` and `webui/package-lock.json` with exact versions, `build`, `check`, and `test:browser` scripts, and no runtime dependency assumption.
- [ ] Record npm package name/version, registry/repository, integrity/lock information, MIT license notice, build command, and generated-output policy in `webui/PROVENANCE.md` and `webui/LICENSES/`.
- [ ] Keep `node_modules/`, browser caches, FETCH_ONLY bytes, and temporary build output ignored and outside Python package data.

## Implementation

Follow these steps in order:

1. Create the `webui/` workspace with a minimal `src/` tree and package scripts targeting `webui/build.mjs`; pin `monaco-editor@0.56.0`, esbuild, and the selected Playwright version in the lockfile.
2. Use the lockfile's integrity fields and package metadata to write provenance; copy the Monaco MIT notice without copying CodeSignal material or assessment fixture content.
3. Add root/project ignore rules only where the project convention allows, and define the generated asset destination `src/codesignal_practice_simulator/web/static/` in the build documentation.
4. Run `npm ci --ignore-scripts`, `npm run check`, and a clean-lockfile metadata inspection; do not run the browser or install assets until the lock is stable.

### Safety and content isolation

Use the public Monaco package only. Scan `webui/` for `solution`, `study`, `vendor`, fetched prompt/test content, and external URLs; the only allowed runtime dependency is local package output.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] Lockfile versions and integrity data are committed and reproducible.
- [ ] Provenance/license/build records identify the exact editor source and generated-output boundary.
- [ ] A clean `npm ci` and static/provenance check pass with no assessment bytes or `node_modules` tracked.
