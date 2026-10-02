# CodeSignal Practice Simulator Release Review

Date: 2026-09-09<br>
Decision: **GO**

## Reviewed release

- Project: `lancekrogers/codesignal-practice-simulator`
- Project commit: `f1a178ae5276dd36cdba7c450dcc2fe39b5d49d3`
- Campaign commit and gitlink proof: `a4365835cebab4a68fb63bf5599d2d5ec905ea07`
- Repository visibility: `PRIVATE`
- Canonical verification: `python3 scripts/run_legacy_checks.py`
- Maintained suite: 158 tests passing
- Independent Cursor release audit: `RELEASE GO`; blockers: none

## Blocking review checklist

| Review area | Result | Dated evidence |
| --- | --- | --- |
| Requirements traceability | PASS | `002_PLAN/plan/IMPLEMENTATION_PLAN.md` requirement matrix plus phase 003–006 result files; R01–R15 have implementation and acceptance evidence. |
| Privacy/provenance | PASS | `003_BOOTSTRAP_MIGRATE/01_repository_and_provenance/results/migration-preflight.md`, `assessment-provenance-draft.md`, and phase-006 clean-clone evidence prove PRIVATE, FETCH_ONLY, seven hashes, and no tracked vendor bytes. |
| Isolation/lifecycle | PASS | `006_VERIFICATION/01_runtime_and_contract_tests/results/01_complete_deterministic_unit_and_contract_coverage.md` records fake-clock, lock, rollback, reconciliation, recovery, expiry, finality, and idempotency coverage. |
| Assessment fidelity | PASS | Phase-006 runtime evidence proves four independent group outcomes and contiguous reach; `scripts/run_legacy_checks.py` proves the lawful spec/staged/study profiles without executing the fetched upstream test. |
| CLI/candidate experience | PASS | `006_VERIFICATION/02_cli_end_to_end_and_migration_release_checks/results/01_exercise_full_and_drill_cli_lifecycles.md` proves generated console/module entry points across full/drill, stable output/exits, and failure paths. |
| Agent safety | PASS | Phase-004/005 result files and the phase-006 suite prove status/context/coaching non-interference, no reference imports, and the documented operational—not cryptographic—agent boundary. |
| Campaign integration | PASS | `006_VERIFICATION/02_cli_end_to_end_and_migration_release_checks/results/02_prove_migrated_fidelity_and_clean_clone_reproducibility.md` proves a clean recursive campaign clone, correct private gitlink, independent fetch, clean statuses, and cleanup. |

No blocking row is missing dated reproducible evidence. No unresolved
high-severity defect was found.

## Requirements disposition

| Requirement | Disposition | Review evidence |
| --- | --- | --- |
| R01 | PASS | Private project and approved campaign submodule reproduce from clean clones. |
| R02 | PASS | Complete classification manifest and FETCH_ONLY license decision retained. |
| R03 | PASS | Seven-record ignored cache is fetched and hash-validated before use. |
| R03a | PASS | Manifest scanner and hermetic hook tests cover staged index and HEAD vendor paths/hashes. |
| R04 | PASS | Four independently executed groups produce a contiguous reached level. |
| R05 | PASS | Stable console/module command, JSON, human, and exit-code contract is tested and documented. |
| R06 | PASS | Persisted full/drill timing and fake-clock expiry are deterministic. |
| R07 | PASS | Attempts are isolated and creation failures roll back only owned state. |
| R07a | PASS | Scoring uses exact absolute-interpreter `-I -S` attempt-local argv; editable, `PYTHONPATH`, and loose-reference sentinels cannot import. |
| R08 | PASS | Atomic state/event writes and crash recovery have injected-fault coverage. |
| R09 | PASS | Selection, locks, lifecycle transitions, expiry, and idempotent submission are covered. |
| R10 | PASS | Status and context are derived, versioned, safe views rather than state. |
| R11 | PASS | Coaching is non-executable and score-invariant. |
| R12 | PASS | Root and attempt agent guidance enforce live-session boundaries. |
| R13 | PASS | Teaching/reference material stays outside attempts; the Level-4 dual profile is explicit. |
| R14 | PASS | 158 deterministic tests plus real-process and two clean-clone rehearsals pass. |
| R15 | PASS | User-authored spec, staged, and cumulative study checks pass; upstream tests remain untracked and noncanonical. |
| R16 | DEFERRED AS PLANNED | The one-assessment `AssessmentRegistry` seam and registry test were examined. Adding a second assessment remains outside the approved first release. |
| R17 | DEFERRED AS PLANNED | No weighted scoring, hidden-test emulation, or remote CodeSignal integration is implemented or claimed; these require a future opt-in profile. |

R16 and R17 are the only deferred requirements. Their deferrals are scope
decisions, not hidden release dependencies.

## Feedback incorporation

All accepted findings were implemented and regression-tested:

- The process E2E uses a real offline editable installation and its generated
  `codesignal-sim`, covers console/module × full/drill, snapshots checkout and
  subprocess-parent leakage, and robustly captures exact scorer argv.
- The canonical verifier provides recovery guidance for absent, invalid-file-
  set, and hash-mismatched caches.
- Submission recovery, pointer rollback, JSONL tails/duplicate IDs, hook
  isolation, detached-child cleanup, and all seven cache hashes have focused
  tests.

The only nonblocking note is the intentional explicit E2E rerun in `just
verify`; it keeps the documented E2E command visible as its own gate while
full discovery also contains it.

## Handoff

After fixture setup, run:

```sh
python3 scripts/run_legacy_checks.py
python3 -m unittest discover -s tests -v
```

For practice, use `codesignal-sim start` (90-minute full mode by default) or
`codesignal-sim start --mode drill`, then `task`, `test`, `context`, and
`submit`. Terminal agents should read generated `STATUS.md`/`COACHING.md` and
the attempt `AGENTS.md` before coaching.
