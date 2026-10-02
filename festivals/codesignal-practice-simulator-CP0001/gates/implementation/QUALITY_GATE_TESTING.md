---
# Gate metadata (for fest CLI discovery)
id: QUALITY_GATE_TESTING
aliases:
  - testing-verify
  - qg-test
description: Standard quality gate task for testing and verification

# Fest document metadata (becomes document frontmatter)
fest_type: gate
fest_id: <no value>
fest_name: Testing and Verification
fest_parent: <no value>
fest_order: <no value>
fest_gate_type: testing
fest_autonomy: medium
fest_status: pending
fest_tracking: true
fest_created: 2026-09-08T14:45:08-06:00
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
- [ ] The manifest separately validates tracked mappings, every fetched-cache
  hash, and staged/HEAD Git boundaries, and no vendor byte is tracked.
- [ ] The unit and end-to-end tests cover the sequence's changed contract.
- [ ] `git diff --check` passes and `git status --short` contains only expected work.
