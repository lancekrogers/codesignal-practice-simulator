# Phase 004_ASSESSMENT_LIBRARY — deliverable inventory and evidence

Recorded 2026-09-12 for the implementation phase gate. Every path below is in
the linked worktree `projects/worktrees/codesignal-practice-simulator/
cp0002-practice-library` at commit `9676ed5` (branch `cp0002-practice-library`),
which contains the two sequence commits:

    9676ed5 feat: bundle two original four-level exercises with specs, tests, oracles and content checks
    614aaf5 feat: validated input providers and registry-driven catalog

Nothing is pushed; no PR exists. The audit checkout was not modified.

## Deliverable 1 — validated input providers with digest-pinned attempts (D003)

`src/codesignal_practice_simulator/input_providers.py` (303 lines)

- `InputProvider` protocol (`validate` :53, `pinned_assessment` :56,
  `stage_file` :62); `PinnedFetchedProvider` (:73) wraps the File Storage
  fixture cache unchanged; `PackagedOriginalProvider` (:111, `installed` :125,
  `validate` :139, `pinned_assessment` :162, `stage_file` :181) verifies
  bundled originals against `content-manifest.json`, rejects any file outside
  the six candidate-facing files plus the manifest, and checks every directory
  segment and file for symlinks; `InputProviders` (:247, `for_definition` :270)
  resolves a definition's kind and fails closed on unknown kinds.
- `assessments.py`: `provider_kind` (:46) on `AssessmentDefinition`;
  `AssessmentRegistry.definitions()` (:199); duplicate IDs and duplicate input
  directories rejected.
- `workspace.py`: `validate_inputs` (:192) and `_provider` (:201) route
  creation identity, staging and staged-byte re-verification through the
  selected definition's provider; `_validate_creation_state` (:224) rejects an
  unpinned v2 state. `restart_attempt` validates the replacement's inputs
  before touching the old attempt.

Tests: `tests/test_input_providers.py` (12): the File Storage digest equals
the recorded pre-refactor value; legacy creation still copies six cache files;
missing/tampered cache still refused; originals start with a never-fetched
cache; eleven package faults and five symlink placements refused before
`attempts/` exists; package changed between validation and staging caught on
staged bytes; tampered package blocks restart before the old attempt is
touched; removed definition leaves stored results reviewable.

## Deliverable 2 — registry-driven catalog with CLI/HTTP discovery (R1/R8/R11)

- `catalog.py` (156 lines): `CatalogEntry` (:46), `CatalogService.list_assessments`
  (:93) enumerating `registry.definitions()` with per-provider readiness
  (`fetch_required`, `packaged_content_invalid`, `provider_unavailable`) and
  path-free messages; read-only.
- `application.py`: `catalog()` (:231); `bootstrap()` derived from the registry
  with a `catalog` list; `web/routes.py`: `GET /api/catalog` (:123); `cli.py`:
  `catalog` command.
- Packaging: `pyproject.toml` package-data globs for
  `resources/assessments/*/*`; `scripts/run_packaged_browser.py` allowlist
  (`PACKAGED_ASSESSMENT_MEMBERS` :45) evaluated before the generic `.py` rule,
  plus oracle segment/suffix rejection (`FORBIDDEN_ARCHIVE_SUFFIXES` :40).

Tests: `tests/test_catalog_distribution.py` (9): readiness per provider
without side effects, tampered/unprovided content reported, duplicate identity
and wrong profiles rejected before exposure, CLI/application parity, HTTP
route (200, 401, 405, 400, tree unchanged, bootstrap carries the list),
archive allowlist and oracle rejection, pyproject globs, installed provider
resolves the resources directory as files.

## Deliverable 3 — original four-level exercises (R1/R2), after D005

- `docs/content/README.md`, `in_memory_records.md`, `account_ledger.md`:
  conventions and full specifications (signatures, return/error conventions,
  ordering, time units, level dependencies, worked examples, edge cases).
- `src/codesignal_practice_simulator/resources/assessments/in_memory_records/`
  and `.../account_ledger/`: `level1.md`–`level4.md`, `simulation.py`
  (starter returning `[]`), `test_simulation.py`
  (`TestSimulateCodingFramework.test_group_1..4`, the fixed runner contract at
  `scoring.py`), `content-manifest.json` (`records-1`, `ledger-1`).
- `assessments.py`: `IN_MEMORY_RECORDS` (:169), `ACCOUNT_LEDGER` (:176),
  `DEFAULT_ASSESSMENT_REGISTRY` (:212) listing File Storage plus both.
- `tests/oracles/`: development reference implementations, never packaged.
- `scripts/check_content.py` (`check_bundled_content` :45,
  `_check_test_module` :108) and `just check content`.

Tests: `tests/test_original_content.py` (7, each running the real isolated
scorer on real attempts): starter fails every group; reference passes every
group twice identically; nine deliberate mutants pass every group below their
level and fail their level; malformed input raises; a raising candidate is an
error, not a hang; content check rejects a renamed group, a stray solution, a
stale hash and an extra import; catalog on a never-fetched workspace lists both
originals available and File Storage unavailable.

## Suite results (after 9676ed5)

    just check content                               both exercises OK
    python3 -m unittest <the three phase modules>    28 tests, OK
    just check unit                                  453 tests, OK (1 skipped)
    just check browser                               175 passed, 0 failed
    just check frontend                              passed
    verify_manifest.py --scope tracked/git-boundary  passed
    grep -rin codesignal docs/content/ resources/assessments/   0 matches
    git diff --check                                 clean

Not run here: `just check wheel` (no interpreter with packaging prerequisites)
and `just verify`'s fixture-cache scope (no fetched cache; network fetch not
authorized). Both are recorded in each sequence's `results/testing.md`; 006/01
owns the outside-checkout wheel proof.

## Reviews

Each sequence ran a delegated read-only Cursor review
(`claude-sonnet-5-thinking-high`) plus a coordinator review; findings and
dispositions are in each `results/review.md`, fixes with regression tests in
each `results/iterate.md`. One blocking finding was raised (004/02 F1, two
specified closure rules not asserted by the packaged tests) and fixed with new
scenarios and mutants.
