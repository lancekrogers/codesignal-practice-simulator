---
fest_type: sequence
fest_id: 02_cli_end_to_end_and_migration_release_checks
fest_name: cli_end_to_end_and_migration_release_checks
fest_parent: 006_VERIFICATION
fest_order: 2
fest_status: completed
fest_created: 2026-09-08T16:23:17.572688-06:00
fest_tracking: true
fest_working_dir: .
---

# Sequence Goal: CLI End-to-End and Migration Release Checks

**Sequence:** 02_cli_end_to_end_and_migration_release_checks | **Phase:** 006_VERIFICATION | **Status:** Completed

## Sequence Objective

Exercise real full/drill CLI lifecycles in temporary roots and prove migration fidelity, legacy compatibility, and clean-clone reproducibility.

## Required Deliverables

- [x] **Real-process evidence**: console and module full/drill lifecycle tests, including failure and recovery paths.
- [x] **Canonical verification**: tracked mappings, fetched-cache hashes, unit,
  end-to-end, and lawful compatibility checks compose into one command.
- [x] **Clone rehearsal**: fresh project and recursively initialized campaign
  clones succeed with a temporary local source or mocked downloader.

## Task Alignment

| Task | Objective |
|------|-----------|
| 01_exercise_full_and_drill_cli_lifecycles | Prove isolated real-process candidate workflows. |
| 02_prove_migrated_fidelity_and_clean_clone_reproducibility | Prove source fidelity and release reproduction. |

## Dependencies and Risks

**Prerequisite:** `01_runtime_and_contract_tests`.<br>
**Provides:** release evidence for `007_REVIEW_RELEASE`.<br>
**Risk:** a developer-local dependency, tracked vendor byte, clone failure,
cache difference, or root leak. **Mitigation:** temporary roots, fresh clones,
the setup seam, documented dependencies, and retaining `SOURCE` on failure.

## Completion and Gates

- [x] Every planned verifier passes and results are recorded.
- [x] All required sequence gates pass before release review.
