---
fest_type: gate
fest_id: 07_testing.md
fest_name: Testing and Verification
fest_parent: 02_content_transfer_and_campaign
fest_order: 7
fest_status: completed
fest_autonomy: medium
fest_gate_id: testing
fest_gate_type: testing
fest_managed: true
fest_created: 2026-09-08T16:37:41.208142-06:00
fest_updated: 2026-09-08T19:20:18.59756-06:00
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

- [ ] Applicable planned Python commands pass.
- [ ] The manifest verifies tracked mappings, every fetched-cache hash, and
  staged/HEAD Git boundaries separately; no vendor file is tracked.
- [ ] Transfer evidence contains exactly one valid successful
  `transfer_commit_sha`/remote-equality record; before campaign mutation its
  SHA equals both PROJECT `HEAD` and `origin/main`.
- [ ] The unit and end-to-end tests cover the sequence's changed contract.
- [ ] `git diff --check` passes and `git status --short` contains only expected work.
