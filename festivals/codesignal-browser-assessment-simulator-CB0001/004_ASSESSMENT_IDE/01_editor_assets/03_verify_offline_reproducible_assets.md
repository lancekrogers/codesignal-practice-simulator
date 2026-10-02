---
fest_type: task
fest_id: 03_verify_offline_reproducible_assets.md
fest_name: verify offline reproducible assets
fest_parent: 01_editor_assets
fest_order: 3
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:29.143855-06:00
fest_updated: 2026-09-09T07:57:25.007783-06:00
fest_tracking: true
---


# Task: verify offline reproducible assets

## Objective

Verify the asset bundle is deterministic, license-complete, CSP-compatible, and included identically in editable and wheel installations.

## Requirements

- [ ] Rebuild from a clean temporary output using only `package-lock.json`, compare the declared manifest and hashes, and inspect for undeclared generated files.
- [ ] Build an sdist/wheel and assert every required static/worker/license file is present while `node_modules`, caches, and fixture bytes are absent.
- [ ] Load the app through the real server with browser network denial and assert all script/style/worker requests are same-origin and successful.

## Implementation

Follow these steps in order:

1. Add `webui/check-assets.mjs` or a Python equivalent that reads the manifest, hashes outputs, checks required MIME types, and rejects output outside the static directory.
2. Run `npm ci`, two clean builds into separate temporary directories, and the reproducibility checker; if timestamps or random names differ, make build naming deterministic rather than weakening comparison.
3. Run `python3 -m build`, inspect the wheel with `unzip -l`, and use the existing package-data tests in `tests/test_cli.py` as the pattern for import/install assertions.
4. Run a minimal Playwright/network-denied load against the packaged static server and record only pass/fail plus manifest hashes.

### Safety and content isolation

Do not save screenshots/traces containing candidate or fixture content for successful runs. Scan wheel/static output for FETCH_ONLY sentinels, source paths, external URLs, and secrets.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] Two clean builds have matching declared asset manifests/hashes or a documented deterministic normalization.
- [ ] Wheel inspection proves all required assets/notices are present and forbidden artifacts are absent.
- [ ] Network-denied browser load passes CSP/worker checks with no unexpected request.
