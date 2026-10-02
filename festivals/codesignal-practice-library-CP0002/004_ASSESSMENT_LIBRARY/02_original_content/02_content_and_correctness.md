---
fest_type: task
fest_id: 02_content_and_correctness.md
fest_name: content_and_correctness
fest_parent: 02_original_content
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-11T14:32:19.009153-06:00
fest_updated: 2026-09-12T20:41:48.684382-06:00
fest_tracking: true
---


# Task: content_and_correctness

## Objective

Author package prompts, starters, deterministic tests, and version manifests for each accepted track from task 01 specs, preserving `test_simulation.TestSimulateCodingFramework.test_group_1..4` entry points and verifying correctness without oracle leak in candidate-distributed resources.

## Requirements

- [ ] **Depends on:** task `01_content_specifications` completed with D005 user choice recorded and specs approved.
- [ ] Read and apply **D003_assessment_catalog.md** (content package layout, scorer entry points) and **D005_content_scope.md** (accepted tracks only).
- [ ] Author four progressive prompt files, deterministic starter, four-group checks, and machine-readable content metadata per accepted exercise.
- [ ] Keep fixed scorer entry points `test_simulation.TestSimulateCodingFramework.test_group_1..4` observed at `src/codesignal_practice_simulator/scoring.py:193`.
- [ ] Add development-only correct and deliberately wrong reference implementations; never ship solutions in candidate-facing package resources.
- [ ] Verify all levels, invalid inputs, determinism, bounded execution, and isolated scorer compatibility using existing scorer—no second runner.

## Implementation

1. **Content tree** — Under package resources (aligned with task 01 spec IDs), create prompts L1–L4, `simulation.py` starter, `test_simulation.py` with test_group_1..4, and manifest with version/digest.
2. **Manifest pinning** — Declare hashes for all bundled files; wire into assessments registry from 004/01.
3. **Development oracles** — Keep correct/wrong examples in `tests/` or dev-only paths excluded from wheel allowlist.
4. **Progression tests** — For each level: starter fails, reference solution passes, wrong solution fails specific groups; boundary/invalid input cases per spec.
5. **Determinism** — Repeated scoring same source yields identical outcomes; enforce timeouts consistent with existing runner bounds.
6. **Build validation** — Extend packaging checks to assert all four test_group methods exist and import targets remain allowlisted.

### Affected files

- Package resource directories for each accepted assessment
- `src/codesignal_practice_simulator/scoring.py` (reference only unless runner extension demonstrated necessary)
- `tests/test_original_content_*.py` (per track or parameterized)
- packaging allowlist/checker modules

### Negative cases to prove

- Wrong implementation fails at correct group only (no false passes).
- Invalid inputs raise/return per spec without hanging runner.
- Candidate wheel contains no development oracle files (allowlist scan).
- Renaming test groups away from test_group_1..4 breaks build check intentionally.

### Commands and evidence

```bash
python3 -m unittest discover -s tests -p 'test_original_content_*.py' -v
just verify  # or focused module tests per project Justfile
```

## Done When

- [ ] All requirements met
- [ ] Each accepted track passes isolated scorer for all four levels with deterministic tests
- [ ] Packaging scan confirms no oracle leak and manifest digests match bundled files
