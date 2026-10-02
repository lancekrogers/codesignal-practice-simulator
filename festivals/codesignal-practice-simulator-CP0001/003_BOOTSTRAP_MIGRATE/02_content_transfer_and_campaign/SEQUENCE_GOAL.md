---
fest_type: sequence
fest_id: 02_content_transfer_and_campaign
fest_name: content_transfer_and_campaign
fest_parent: 003_BOOTSTRAP_MIGRATE
fest_order: 2
fest_status: completed
fest_created: 2026-09-08T16:23:17.423632-06:00
fest_updated: 2026-09-08T19:21:24.444244-06:00
fest_tracking: true
fest_working_dir: .
---


# Sequence Goal: Content Transfer and Campaign Integration

**Sequence:** 02_content_transfer_and_campaign | **Phase:** 003_BOOTSTRAP_MIGRATE | **Status:** Completed

## Sequence Objective

Transfer only approved non-verbatim user-authored assets, preserve safe
compatibility evidence, and integrate only the proven private project.

## Required Deliverables

- [x] **Verified approved assets**: all included user-authored bytes match the
  manifest; vendor records remain excluded with null destinations.
- [x] **Compatibility evidence**: user-authored checks and separately verified
  fetched-cache hashes are recorded without concealing known discrepancies.
- [x] **Clean integration**: the approved private remote is reproducible from project and campaign clean clones.

## Task Alignment

| Task | Objective |
|------|-----------|
| 01_transfer_teaching_reference_and_compatibility_assets | Transfer approved assets and retain compatibility evidence. |
| 02_integrate_proven_project_into_campaign | Add only the verified submodule after clean-clone rehearsal. |

## Dependencies and Risks

**Prerequisite:** `01_repository_and_provenance` passing.<br>
**Provides:** the migrated project for `004_SESSION_RUNTIME`.<br>
**Risk:** tracked vendor bytes, unverified remote, failed clone, or unrelated
campaign mutation. **Mitigation:** retain `SOURCE`, use temporary setup seams,
rehearse first, and revert only new submodule entries if a stop occurs.

## Completion and Gates

- [x] Complete all task Verify blocks and record results.
- [x] Apply and pass the required testing, review, iterate, and focused-commit gates.

## Completion Evidence

- `results/01_transfer_teaching_reference_and_compatibility_assets.md` records
  all 24 approved mappings, passing compatibility checks, and exact pushed
  transfer SHA equality.
- `results/02_integrate_proven_project_into_campaign.md` records private
  visibility, temporary project/campaign clone proofs, the committed gitlink,
  and retained source work item `WI-117ed7`.
- The review finding for `score-solution` was fixed and re-approved: the
  tracked solution now uses the ignored pinned grader, while ordinary attempts
  continue using their isolated copied tests.
- Project `HEAD` and `origin/main` are both `0a1c6f2`; campaign commit
  `4c1c3a8` records the same submodule pointer.
