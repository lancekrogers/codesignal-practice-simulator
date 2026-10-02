---
fest_type: task
fest_id: 01_complete_deterministic_unit_and_contract_coverage.md
fest_name: complete_deterministic_unit_and_contract_coverage
fest_parent: 01_runtime_and_contract_tests
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-08T16:23:47.652705-06:00
fest_updated: 2026-09-08T23:07:58.3463-06:00
fest_tracking: true
fest_dependencies:
  - ../../005_CLI_WORKFLOWS/02_evaluation_submission_and_operator_docs/06_fest_commit
---


# Task: 006.01.01 — Complete Deterministic Unit and Contract Coverage

## Objective

Complete deterministic test coverage for every state, persistence, scoring, safety, and CLI contract.

## File anchors

Existing anchors are all `/workspace/campaign/projects/codesignal-practice-simulator/src/codesignal_practice_simulator/*.py`, `tests/{test_models.py,test_persistence.py,test_workspace.py,test_lifecycle.py,test_scoring.py,test_rendering.py,test_cli.py}`, and `docs/cli-contract.md`. Modify only the referenced modules, tests, and documentation.

## Ordered implementation steps

1. Add table-driven valid/invalid schema and transition cases, fake-clock full/drill/expiry cases, lock contention, revision recovery, pointer validation, and JSONL trailing-tail recovery.
2. Assert independent level outcomes, contiguous reach, crash/timeout
   representation, all seven cache-record hashes, setup-required behavior,
   coaching/status non-interference, and atomic workspace rollback at every
   injected filesystem failure point. Inject interruption after publishing a
   marker-owned attempt but before pointer replacement; reconciliation must
   remove only that attempt while preserving the prior pointer and attempts.
3. Create temporary Git repositories to prove the manifest-driven scanner and
   installed hook wrappers reject known vendor hashes and forbidden vendor
   paths in both the staged index and `HEAD`, while safe blobs pass.
4. Verify every scoring group launches exactly
   `<absolute-interpreter> -I -S <attempt>/.scoring/run_group.py <group>`.
   With the project installed editable, inject an importable editable-project
   sentinel, a hostile `PYTHONPATH` sentinel, and a loose reference sentinel
   outside the attempt. Prove the bootstrap admits only copied attempt
   candidate/test paths plus interpreter standard-library paths and that none
   of the sentinels can import or influence a score.
5. Assert console/module human/JSON envelopes and exits 0, 2, 3, 4, and 5. Explicitly test status/time expiry observation, expired resume/test rejection, expired submit finalization, and repeat-submit no-change idempotency.
6. Remove wall-clock/network/global-workspace dependencies by injecting clock,
   process, and filesystem seams. Update cli contract only where tests expose a
   documented discrepancy.
7. Run the full deterministic suite and store output.

## Error paths

Flaky timing, platform-specific locks, nondeterministic subprocess output, uncovered recovery, or a contradictory contract blocks this task. Make the relevant dependency injectable; do not weaken an assertion to mask the behavior.

## Do-not-mutate boundaries

Do not depend on a developer `attempts/` directory, mutate cache/reference
material, track vendor bytes, or introduce network/hidden-service tests.

## Verification and evidence

Run from the directory named in the commands. Save complete output and exit codes to `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/006_VERIFICATION/01_runtime_and_contract_tests/results/01_complete_deterministic_unit_and_contract_coverage.md`; a nonzero exit is blocking unless stated below.

```sh
PROJECT="/workspace/campaign/projects/codesignal-practice-simulator"
EVIDENCE="/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/006_VERIFICATION/01_runtime_and_contract_tests/results/01_complete_deterministic_unit_and_contract_coverage.md"
mkdir -p "$(dirname "$EVIDENCE")"
set -e
set -o pipefail
{
cd "$PROJECT"
python3 -m unittest discover -s tests -v
python3 -m unittest tests.test_models tests.test_persistence tests.test_lifecycle tests.test_scoring tests.test_rendering tests.test_cli -v
git diff --check
git status --short
} 2>&1 | tee "$EVIDENCE"
```

Expected result: the commands produce the stated success output and `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/006_VERIFICATION/01_runtime_and_contract_tests/results/01_complete_deterministic_unit_and_contract_coverage.md` records it.

## Definition of done

- [ ] Tests directly prove each documented state/event/scoring/safety command contract.
- [ ] Expiry and idempotency are deterministic under fake clocks.
- [ ] Workspace rollback, staged/HEAD vendor-boundary, and sanitized scoring
  subprocess isolation are deterministically proven, including
  publish-before-pointer reconciliation and all three import sentinels.
- [ ] The suite has no network, wall-clock, or existing-workspace dependency
  and uses the local-source/downloader seam for setup coverage.
- [ ] Both verification commands pass.
