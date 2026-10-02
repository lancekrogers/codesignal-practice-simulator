---
fest_type: task
fest_id: 03_verify_cli_compatibility.md
fest_name: verify cli compatibility
fest_parent: 01_runtime_composition
fest_order: 3
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:27.616273-06:00
fest_updated: 2026-09-09T03:36:58.580943-06:00
fest_tracking: true
---


# Task: verify CLI compatibility

## Objective

Prove the public composition extraction is backward compatible across parser behavior, console/module entry points, lifecycle exits, output schemas, and safe context surfaces.

## Requirements

- [ ] Exercise the existing `codesignal-sim` commands and `python -m codesignal_practice_simulator` path through the extracted factory.
- [ ] Prove full/drill start, explicit attempt selection, test candidate-failure exit 5, submit idempotency, and `context --format json|markdown` remain stable.
- [ ] Record focused command output and do not mark implementation tasks complete or alter legacy fixture/provenance behavior.

## Implementation

Follow these steps in order:

1. Run `python3 -m unittest tests.test_cli tests.test_end_to_end tests.test_lifecycle -v` and inspect failures for changes in `cli/v1` documents, exit codes, or active-pointer selection.
2. Use the existing synthetic project helpers to run console and module commands for `fetch`, `start`, `status`, `time`, `task`, `test`, `submit`, and `context`; compare parsed JSON rather than timestamps.
3. Run `python3 scripts/run_legacy_checks.py` and `just verify`; if an assertion changes, fix the public boundary rather than weakening the old test.
4. Run an import check under the minimum supported interpreter available and note unavailable versions without fabricating evidence.

### Safety and content isolation

Use only temporary synthetic attempts. Verify context output excludes `simulation.py`, `test_simulation.py`, solution/study/vendor names, raw paths, and scorer command details.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] All focused CLI, lifecycle, end-to-end, legacy, and canonical checks pass.
- [ ] The extracted application produces byte-compatible envelopes for unchanged command scenarios.
- [ ] A compatibility note identifies the exact commands run and any interpreter not available locally.
