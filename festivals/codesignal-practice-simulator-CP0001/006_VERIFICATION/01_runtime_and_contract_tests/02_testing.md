---
fest_type: gate
fest_id: 06_testing.md
fest_name: Testing and Verification
fest_parent: 01_runtime_and_contract_tests
fest_order: 6
fest_status: completed
fest_autonomy: medium
fest_gate_id: testing
fest_gate_type: testing
fest_managed: true
fest_created: 2026-09-08T16:37:41.215714-06:00
fest_updated: 2026-09-08T23:07:58.412889-06:00
fest_tracking: true
fest_version: "1.0"
---


# Gate: Testing and Verification

Run the implementation-plan verification that applies to this sequence. The
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

- [x] Applicable planned Python commands pass: 150 full tests under both
  interpreters and 105 named contract tests pass.
- [x] The manifest verifies tracked mappings, every fetched-cache hash, and
  staged/HEAD Git boundaries separately; no vendor file is tracked.
- [x] Deterministic tests cover schema/state/exit matrices, locks, JSONL tails,
  write-ahead recovery, all seven hashes, real hook wrappers, exact scorer
  launch/isolation, and every workspace publish/rollback outcome.
- [x] `git diff --check` passes and `git status --short` contains only expected work.

`scripts/run_legacy_checks.py` remains the next sequence's planned task; all
currently available component checks pass.
