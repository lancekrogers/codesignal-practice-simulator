---
fest_type: task
fest_id: 01_exercise_full_and_drill_cli_lifecycles.md
fest_name: exercise_full_and_drill_cli_lifecycles
fest_parent: 02_cli_end_to_end_and_migration_release_checks
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-08T16:23:47.67277-06:00
fest_tracking: true
fest_dependencies:
  - ../01_runtime_and_contract_tests/05_fest_commit
---

# Task: 006.02.01 — Exercise Full and Drill CLI Lifecycles

## Objective

Prove real-process CLI behavior in isolated temporary roots for both entry points and modes.

## File anchors

Existing anchors: installed package, `scripts/fetch_fixture.py`, the ignored
cache contract, `tests/test_end_to_end.py`, and `justfiles/verify.just`.
Create/update tests and optional recipe only.

## Ordered implementation steps

1. Use `TemporaryDirectory` and subprocesses; invoke both `codesignal-sim`
   and `python -m codesignal_practice_simulator`. Set up each test with a
   temporary local source fixture or mocked downloader that materializes every
   manifest fetch record, including upstream `README.md` → cache
   `vendor-readme.md`; never use a tracked vendor file or real network.
2. For full and drill, exercise start → status/time/task → test → submit → repeated submit. Capture exit/output/state event counts.
3. Exercise no active pointer, explicit-selector precedence, bad JSONL trailing tail, lock contention, candidate failures, and expiry. Assert status/time persist expired and succeed; expired resume/test exit 4 without scoring; expired submit finalizes once; second submit changes nothing.
4. Assert no attempt data leaks to project root/cache and runtime data remains
   ignored. Verify real scoring subprocesses launch as
   `<absolute-interpreter> -I -S <attempt>/.scoring/run_group.py <group>`.
   With the project installed editable, inject an editable-project sentinel, a
   hostile `PYTHONPATH` sentinel, and a loose reference sentinel outside the
   attempt; prove none can import or influence candidate evaluation.
5. Make the Just verify recipe call the same documented project-local E2E command.

## Error paths

Use of developer attempts, global state, real-time ordering assumptions,
cache/root leakage, tracked vendor data, or differing console/module behavior
blocks this task.

## Do-not-mutate boundaries

Do not change cache/reference/candidate source outside each temporary attempt,
mutate existing attempts, or depend on network services.

## Verification and evidence

Run from the directory named in the commands. Save complete output and exit codes to `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/006_VERIFICATION/02_cli_end_to_end_and_migration_release_checks/results/01_exercise_full_and_drill_cli_lifecycles.md`; a nonzero exit is blocking unless stated below.

```sh
PROJECT="/workspace/campaign/projects/codesignal-practice-simulator"
EVIDENCE="/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/006_VERIFICATION/02_cli_end_to_end_and_migration_release_checks/results/01_exercise_full_and_drill_cli_lifecycles.md"
mkdir -p "$(dirname "$EVIDENCE")"
set -e
set -o pipefail
{
cd "$PROJECT"
python3 -m unittest tests.test_end_to_end -v
git status --ignored --short attempts
git diff --check
git status --short
} 2>&1 | tee "$EVIDENCE"
```

Expected result: the commands produce the stated success output and `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/006_VERIFICATION/02_cli_end_to_end_and_migration_release_checks/results/01_exercise_full_and_drill_cli_lifecycles.md` records it.

## Definition of done

- [x] Both entry points and both modes complete isolated real-process lifecycles.
- [x] E2E assertions prove expiry, finality, and idempotent submit.
- [x] Cache/root isolation, no-tracked-vendor, and Git-ignore checks pass.
- [x] E2E command passes.
