# Catalog and distribution

Implemented by the coordinator directly on 2026-09-12 in the linked
cp0002-practice-library worktree. Uncommitted pending 06_fest_commit.

## What changed

- `src/codesignal_practice_simulator/catalog.py` (new): `CatalogService`
  enumerates `registry.definitions()` in stable ID order. Each `CatalogEntry`
  carries stored metadata, description, levels, supported profiles with
  durations, `provider_kind`, the identity a new attempt would pin (from the
  provider's declared manifest, so known before any fetch), and readiness:
  `available` with `setup` ∈ {`fetch_required`, `packaged_content_invalid`,
  `provider_unavailable`} and a path-free `setup_message`. Enumeration
  validates inputs by reading; it writes nothing and never touches attempts.
- `application.py`: `catalog()`; `bootstrap()` no longer hardcodes the
  assessment, levels and profile list. It derives the single-assessment keys
  the current browser entry flow reads from the primary definition (File
  Storage when installed, otherwise the first) and adds `catalog` with every
  installed assessment. The browser normalizer reads known keys only, so the
  accepted journeys are unchanged.
- `web/routes.py`: `GET /api/catalog` through the existing read helper
  (token required, no query, GET only).
- `cli.py`: `catalog` command returning the same document.
- `pyproject.toml`: package-data globs for `resources/assessments/*/*.{md,py,json}`.
- `scripts/run_packaged_browser.py`: archive check accepts exactly
  `resources/assessments/<lowercase id>/{level1..4.md, simulation.py,
  test_simulation.py, content-manifest.json}` and rejects any other member
  under that prefix before the generic `.py` rule, so a bundled `solution.py`
  can never pass as package code.
- `docs/cli-contract.md`: "Assessment catalog" section.

## Deliberate decisions

- Readiness comes from the provider's own `validate`, the same check that gates
  attempt creation, so the catalog cannot claim "available" for content that
  `start` would refuse.
- `setup_message` is a fixed safe sentence per reason; provider error text
  (which may name a path) never reaches transports.
- Bootstrap keeps its existing shape and adds `catalog` rather than replacing
  keys: 005 owns the library UI; this task only makes the data registry-driven.

## Negative cases proven (tests/test_catalog_distribution.py, 8 tests)

- Enumeration with a never-fetched cache: File Storage `fetch_required` with
  the fetch hint and its declared identity; the synthetic original available
  with its version; whole workspace tree unchanged, no `attempts/` created, no
  path in the document; fetched cache flips File Storage to available.
- Tampered packaged file → `packaged_content_invalid`, identity still declared;
  missing manifest → identity unknown; no provider for the kind →
  `provider_unavailable` while File Storage stays available.
- Duplicate IDs (same definition twice, two definitions sharing an ID), wrong
  profile sets (missing drill, extra profile) and wrong level groups are
  rejected at definition/registry construction, before any catalog exists.
- CLI `catalog --json` equals `application.catalog().to_dict()`; bootstrap
  primary is File Storage with the full list in `catalog`.
- HTTP: `GET /api/catalog` shape and identity, bootstrap carries the same list
  and the selected session, 401 without token, 405 on POST, 400 on a query,
  attempts tree unchanged.
- Packaging allowlist: the seven allowed members pass; `solution.py`,
  `notes.md`, `README.md`, nested paths, a file directly under
  `resources/assessments/`, and a non-lowercase directory are rejected;
  `pyproject.toml` declares the three globs; the installed provider resolves
  the `resources` directory as real files.
- Removed-version behavior (old review readable, no metadata rewrite) is
  proven in results/input_providers.md and unchanged here.

## Evidence

    python3 -m unittest tests.test_catalog_distribution   8 tests OK
    just check unit                                       444 tests OK (1 skipped)
    python3 -m unittest tests.test_documentation          OK
    git diff --check                                      clean

Browser/frontend results are recorded at the sequence testing gate.

## Not run here

`just check wheel` (wheel build, install outside the checkout with network
disabled) cannot run: no interpreter on this machine has setuptools/pip/venv/
wheel/build. The archive allowlist logic it uses is unit-tested above; the
end-to-end wheel proof stays owned by 006/01_acceptance_and_distribution, which
already carries this prerequisite gap.
