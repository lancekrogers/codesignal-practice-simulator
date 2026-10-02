---
fest_type: sequence
fest_id: 01_repository_and_provenance
fest_name: repository_and_provenance
fest_parent: 003_BOOTSTRAP_MIGRATE
fest_order: 1
fest_status: completed
fest_created: 2026-09-08T16:23:17.397871-06:00
fest_updated: 2026-09-08T19:00:59.553631-06:00
fest_tracking: true
fest_working_dir: .
---


# Sequence Goal: Repository and Provenance

**Sequence:** 01_repository_and_provenance | **Phase:** 003_BOOTSTRAP_MIGRATE | **Status:** Completed

## Sequence Objective

Create FETCH_ONLY preflight evidence, then bootstrap the approved private
Python project and implement validated local `file_storage` cache setup.

## Required Deliverables

- [x] **Migration preflight**: reproducible safe/excluded manifest, hashes,
  no-license finding, and exact `FETCH_ONLY` decision.
- [x] **Private scaffold**: a verified Python 3.10+ package with both planned entry points.
- [x] **Fetch-only fixture**: provenance-only tracked metadata plus a
  standard-library fetcher/cache verifier; no vendor bytes in Git.

## Task Alignment

| Task | Objective |
|------|-----------|
| 01_inventory_source_and_approve_migration_boundary | Approve the safe migration boundary before external or source changes. |
| 02_create_private_python_project_after_preflight | Create the private package scaffold after preflight evidence passes. |
| 03_import_and_freeze_attributed_fixture | Implement pinned setup/fetch and prove cache validation. |

## Dependencies and Risks

**Prerequisite:** accepted 002_PLAN decisions and implementation plan.<br>
**Provides:** verified provenance and cache setup for `02_content_transfer_and_campaign`.
**Risk:** source, hash, license, privacy, or path validation fails. **Mitigation:** stop before tracking vendor bytes, publishing, or adding a submodule; record the precise blocker.

## Completion and Gates

- [x] Execute every numbered task and its exact plan verification block.
- [x] Record reproducible results in `results/`.
- [x] Apply and pass testing, review, iterate, and focused-commit gates.

## Completion Evidence

- `results/migration-preflight.md` ends with `preflight manifest: PASS` and
  records the standalone `license decision: FETCH_ONLY`.
- `results/migration-manifest.json` inventories 1,014 source files and declares
  exactly seven hash-pinned fetch records while null-mapping vendor files.
- `results/02_create_private_python_project_after_preflight.md` proves the
  GitHub repository is private, both entry points work, and a fresh clone uses
  the pushed `main` commit.
- Project commit `3352994` adds the fetch-only metadata, downloader, verifier,
  hooks, and passing deterministic tests without tracked vendor bytes.
