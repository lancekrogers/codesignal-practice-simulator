---
fest_type: phase
fest_id: 004_ASSESSMENT_LIBRARY
fest_name: ASSESSMENT_LIBRARY
fest_parent: codesignal-practice-library-CP0002
fest_order: 4
fest_status: completed
fest_created: 2026-09-11T14:31:59.408298-06:00
fest_updated: 2026-09-12T21:00:11.828815-06:00
fest_phase_type: implementation
fest_tracking: true
---


# Phase Goal: 004_ASSESSMENT_LIBRARY

**Phase:** 004_ASSESSMENT_LIBRARY | **Status:** Pending | **Type:** Implementation

## Phase Objective

**Primary Goal:** Complete original exercises offline with versioned catalog, validated input providers, and progressive four-level content.

**Context:** Depends on 003 schema/version contracts for attempt pinning and honest review when definitions are removed. Delivers R1/R2 library content and R11 distribution evidence foundation. Sequence 02 blocked on D005 user topic/count confirmation recorded in task 01_content_specifications.

## Required Outcomes

Deliverables this phase must produce:

- [x] Validated pinned-fetched and packaged-original input providers with digest-pinned attempts (D003).
- [x] Registry-driven catalog replacing hardcoded list with offline-ready originals and CLI/HTTP discovery (R1/R8/R11).
- [x] Original four-level exercises with deterministic tests and no oracle leak in candidate packages (R1/R2)—after D005 user choice (recorded in D005 on 2026-09-12).

## Evidence of deliverables (2026-09-12)

Project code lives in the linked worktree
`projects/worktrees/codesignal-practice-simulator/cp0002-practice-library`,
branch `cp0002-practice-library`, in two commits made with
`fest commit --no-root`: `614aaf5` (004/01) and `9676ed5` (004/02). None is
pushed. Symbol locations below are from those commits; the full inventory with
test names is in `results/phase_evidence.md`.

| Deliverable | Where it exists | How it is proven functional |
| --- | --- | --- |
| Validated input providers, digest-pinned attempts | `src/codesignal_practice_simulator/input_providers.py` (303 lines): `InputProvider` protocol (`validate` :53, `pinned_assessment` :56, `stage_file` :62), `PinnedFetchedProvider` :73 (File Storage cache unchanged), `PackagedOriginalProvider` :111 (`installed` :125, `validate` :139, `pinned_assessment` :162, `stage_file` :181), `InputProviders.for_definition` :270; `assessments.py` `provider_kind` :46; `workspace.py` `validate_inputs` :192, `_provider` :201, `_validate_creation_state` :224 | `tests/test_input_providers.py` (12): File Storage digest equals the recorded pre-refactor value; originals start with a never-fetched cache; eleven package faults and five symlink placements refused before `attempts/` exists; staged-byte re-check catches a package changed after validation; tampered package blocks restart before the old attempt is touched; removed definition leaves results reviewable |
| Registry-driven catalog with CLI/HTTP discovery and packaging | `catalog.py` (156 lines): `CatalogEntry` :46, `CatalogService.list_assessments` :93; `application.catalog` :231 and registry-derived `bootstrap` with a `catalog` list; `web/routes.py` `GET /api/catalog` :123; `cli.py` `catalog`; `pyproject.toml` package-data for `resources/assessments/*/*`; `scripts/run_packaged_browser.py` allowlist `PACKAGED_ASSESSMENT_MEMBERS` :45 and oracle suffix rejection :40 | `tests/test_catalog_distribution.py` (9): readiness per provider without side effects, tampered/unprovided content reported not hidden, duplicate identity and wrong profiles rejected before exposure, CLI/application parity, HTTP 200/401/405/400 with tree unchanged, archive allowlist and oracle rejection, pyproject globs, installed provider resolves resources as files |
| Original four-level exercises, deterministic tests, no oracle leak | `docs/content/{README,in_memory_records,account_ledger}.md` specifications; `resources/assessments/in_memory_records/` and `resources/assessments/account_ledger/` each with `level1..4.md`, `simulation.py`, `test_simulation.py` (`TestSimulateCodingFramework.test_group_1..4`), `content-manifest.json`; `assessments.py` `IN_MEMORY_RECORDS` :169, `ACCOUNT_LEDGER` :176, `DEFAULT_ASSESSMENT_REGISTRY` :212; `tests/oracles/` (never packaged); `scripts/check_content.py` (`check_bundled_content` :45, `_check_test_module` :108) via `just check content` | `tests/test_original_content.py` (7, real isolated-scorer runs): starter fails every group; reference passes every group twice identically; nine deliberate mutants fail from their level onward; malformed input raises; a raising candidate is an error not a hang; content check rejects a renamed group, a stray solution, a stale hash, an extra import; `grep -rin codesignal` and `grep -rn CP0002` over the content find nothing |

Focused suites for the phase: 28 tests, OK. Full project suite after the last
commit: `just check unit` 453 tests OK (1 skipped), `just check browser` 175
passed, `just check frontend` passed, `just check content` OK, manifest
provenance scopes passed. Each sequence has `results/testing.md`,
`results/review.md` (delegated Cursor review plus coordinator review; one
blocking finding in 004/02 fixed) and `results/iterate.md`.

## Quality Standards

Quality criteria for all work in all sequences:

- [x] **Runner contract:** Preserve `test_simulation.TestSimulateCodingFramework.test_group_1..4` entry points at `scoring.py:193` unless a documented runner extension is approved. No runner change was made; `scripts/check_content.py` enforces exactly those four methods and the original tests are scored by the unchanged `IsolatedAttemptScorer`.
- [x] **Content integrity:** No proprietary assessment copying; stable exercise IDs distinct from festival ID CP0002. IDs are `in_memory_records` and `account_ledger`; vendor-name and festival-ID scans over all content find nothing and are enforced by the content check.
- [ ] **Packaging proof:** Wheel install outside checkout with network disabled completes accepted originals. NOT RUN HERE: no interpreter on this machine has the packaging prerequisites (`setuptools/pip/venv/wheel/build`). The archive allowlist and content checks the proof relies on are unit-tested; the end-to-end wheel proof is explicitly carried to 006/01_acceptance_and_distribution, which already owns `just check wheel`.

## Sequence Alignment

| Sequence | Goal | Key Deliverable |
|----------|------|-----------------|
| 01_versioned_catalog | Separate original and fetched inputs | Input providers, catalog routes, packaging |
| 02_original_content | Progressive deterministic practice | Specs (post-D005), prompts/starters/tests |

## Pre-Phase Checklist

Before starting implementation:

- [ ] Planning phase complete
- [ ] Architecture/design decisions documented
- [ ] Dependencies resolved
- [ ] Development environment ready

## Phase Progress

### Sequence Completion

- [x] 01_versioned_catalog (commit 614aaf5; results in 01_versioned_catalog/results/)
- [x] 02_original_content (commit 9676ed5; results in 02_original_content/results/)

## Notes

File Storage cache validation remains unchanged for fetched assessments. Original exercises must start without legacy fetch. Content task 01 remains blocked until D005 records explicit user preference.

---

*Implementation phases use numbered sequences. Create sequences with `fest create sequence`.*
