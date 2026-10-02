---
fest_type: gate
fest_id: 07_testing.md
fest_name: Testing and Verification
fest_parent: 01_command_interface_and_live_session
fest_order: 7
fest_status: completed
fest_autonomy: medium
fest_gate_id: testing
fest_gate_type: testing
fest_managed: true
fest_created: 2026-09-08T16:37:41.213102-06:00
fest_updated: 2026-09-08T21:42:56.421325-06:00
fest_tracking: true
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

- [x] Applicable planned Python commands pass. Evidence: 120 unit tests pass
  under both `.venv/bin/python` (Python 3.10) and `python3`; 26 specification
  tests, 12 staged-solution tests, and all four study checkpoints pass.
- [x] The manifest verifies tracked mappings, every fetched-cache hash, and
  staged/HEAD Git boundaries separately; no vendor file is tracked.
- [x] The unit and end-to-end tests cover parser/adapter behavior, live command
  flows, adversarial path selection, installed-wheel offline fetch and start,
  and atomic fixture publication rollback.
- [x] `git diff --check` passes and `git status --short` contains only the
  expected sequence work.

`scripts/run_legacy_checks.py` and the `just verify` compatibility recipe are
deferred to phase 006 as planned. Their currently available component commands
were run directly and passed.
