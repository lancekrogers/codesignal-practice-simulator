---
fest_autonomy: medium
fest_created: 2026-09-08T16:37:41.217083-06:00
fest_gate_id: testing
fest_gate_type: testing
fest_id: 07_testing.md
fest_managed: true
fest_name: Testing and Verification
fest_order: 7
fest_parent: 02_cli_end_to_end_and_migration_release_checks
fest_status: completed
fest_tracking: true
fest_type: gate
fest_version: "1.0"
---

# Gate: Testing and Verification

Run the verification commands that apply to the completed direct task specifications in this sequence. The
project is created during phase 003; before an indicated script or its inputs
exist, run only the applicable earlier commands and record why later commands
are deferred.

## Project Verification Commands

```sh
PROJECT="/workspace/campaign/projects/codesignal-practice-simulator"
cd "$PROJECT"
python -m unittest discover -s tests -v
python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope tracked
python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope fixture-cache
python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary
python scripts/run_legacy_checks.py
python solution/test_spec.py
python solution/test_stages.py
python3 study/check.py 4 solution/simulation.py
git diff --check
git status --short
```

`python scripts/run_legacy_checks.py` is added in 006.02.02. Before that task,
run its listed component commands that already exist. `just verify` is a
compatibility check from the plan, but the Python commands above remain the
authoritative evidence.

## Required Evidence

- [x] Applicable planned Python commands pass.
- [x] The manifest verifies tracked mappings, every fetched-cache hash, and
  staged/HEAD Git boundaries separately; no vendor file is tracked.
- [x] The unit and end-to-end tests cover the sequence's changed contract.
- [x] `git diff --check` passes and `git status --short` contains only expected work.

## Evidence

All listed commands passed on 2026-09-09. The maintained suite ran 158 tests;
the canonical migration route, direct solution suites, level-4 study checker,
three manifest scopes, diff check, and clean project status all passed. The two
task result files record process-level and clean-clone evidence.
