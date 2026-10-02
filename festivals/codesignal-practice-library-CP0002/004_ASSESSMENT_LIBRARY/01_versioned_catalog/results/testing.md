# Sequence testing gate — 004/01_versioned_catalog

Covers 01_input_providers and 02_catalog_and_distribution. Per-task evidence is
in the sibling results files.

## Commands run and results (final code, 2026-09-12)

    python3 -m unittest tests.test_input_providers            11 tests, OK
    python3 -m unittest tests.test_catalog_distribution        8 tests, OK
    just check unit                                            444 tests, OK (1 skipped)
    just check browser                                         175 passed, 0 failed
    just check frontend                                        passed
    python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope tracked        passed
    python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary   passed
    python3 -m unittest tests.test_documentation               OK
    git diff --check                                           clean

The browser suite matters here because `bootstrap` changed from a hardcoded
catalog to a registry-driven one; the accepted journeys pass unchanged.

## Failure boundaries exercised

- File Storage identity equality with the recorded pre-refactor digest through
  provider, cache and workspace; legacy creation still copies six cache files
  and verifies them; absent or tampered cache still refused before any attempt.
- Eleven packaged-content faults, each refused before `attempts/` exists; a
  package that changes between validation and staging is caught on the staged
  bytes with no residue; a tampered package blocks restart before the old
  attempt is touched.
- Unknown provider kind, provider kind mismatch, invalid definition kind,
  duplicate IDs, duplicate input directories, wrong profile sets, wrong groups.
- Definition removed later: lifecycle blocks, review and history still read;
  newer package version leaves the old attempt reviewable and starts fresh.
- Catalog: readiness per provider without side effects, tampered/unprovided
  content reported not hidden, no paths in documents; HTTP 401/405/400 and
  tree unchanged; CLI and application agree.
- Packaging allowlist: six rejected member shapes including a bundled
  `solution.py`.

## Not run here, with reasons

- `just check wheel`: no interpreter with packaging prerequisites on this
  machine, so the wheel build, outside-checkout install and network-disabled
  discovery cannot be executed. The allowlist logic that check relies on is
  unit-tested; the end-to-end proof is owned by 006/01.
- `just verify` fixture-cache scope: no fetched cache; fetching third-party
  content over the network is not authorized.
