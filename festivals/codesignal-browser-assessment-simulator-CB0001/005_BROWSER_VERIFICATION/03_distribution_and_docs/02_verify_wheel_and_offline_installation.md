---
fest_type: task
fest_id: 02_verify_wheel_and_offline_installation.md
fest_name: verify wheel and offline installation
fest_parent: 03_distribution_and_docs
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:32.007935-06:00
fest_updated: 2026-09-10T11:48:21.753824-06:00
fest_tracking: true
---


# Task: verify wheel and offline installation

## Objective

Prove a wheel-only installation contains the browser runtime and can complete a local browser smoke flow without the source tree, Node, or network.

## Requirements

- [ ] Build sdist/wheel, inspect package contents, install the wheel into a clean temporary virtualenv, and ensure the source checkout is not importable.
- [ ] Set up only the approved synthetic fixture/cache contract, start `codesignal-sim web --no-open`, and load all static/Monaco worker assets with external network denied.
- [ ] Run entry/start/edit/save/test/submit smoke and assert wheel runtime does not serve fixture/vendor/reference bytes or rely on runtime Node.

## Implementation

Follow these steps in order:

1. Run `python3 -m build` and inspect with `unzip -l`; compare package data to `web/static/manifest.json`, license/provenance files, and `pyproject.toml` package-data rules.
2. Create a clean venv outside the project, `pip install --no-index <wheel>` from a local wheel path, and invoke the installed console/module entry points with `PYTHONPATH` unset.
3. Use a synthetic seven-record fixture source only when the documented setup requires it; deny network at Playwright and OS/test fixture level, then complete a short browser flow.
4. Run the installed-package browser smoke and remove the wheel, venv, attempts, traces, and temporary fixture after capturing aggregate evidence.

### Safety and content isolation

Never add FETCH_ONLY bytes to the wheel or test package. Assert no `node_modules`, cache, attempt, solution/study/vendor, or source checkout path is imported or served.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] Clean wheel installation launches the app and serves every manifest asset offline.
- [ ] Browser smoke completes entry/start/edit/save/test/submit without source-tree or Node runtime access.
- [ ] Wheel manifest and forbidden-content scans pass and temporary artifacts are removed.
