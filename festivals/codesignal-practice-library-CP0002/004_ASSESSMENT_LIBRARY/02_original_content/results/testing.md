# Sequence testing gate — 004/02_original_content

Covers 01_content_specifications (documentary) and 02_content_and_correctness.
Per-task evidence is in the sibling results files.

## Commands run and results (final code, 2026-09-12)

    just check content                                          both exercises OK (7 files each)
    python3 -m unittest tests.test_original_content             7 tests, OK (real isolated scorer runs)
    packaged test_simulation.py run against each oracle         4 tests OK, 4 tests OK
    just check unit                                             452 tests, OK (1 skipped)
    just check browser                                          175 passed, 0 failed
    just check frontend                                         passed
    python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope tracked        passed
    python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary   passed
    python3 -m unittest tests.test_documentation                OK
    grep -rin codesignal docs/content/ resources/assessments/   0 matches
    grep -rn CP0002 docs/content/                               0 matches
    git diff --check                                            clean

The browser suite matters because the default registry now has three entries,
which changes `bootstrap.catalog`; the accepted journeys pass unchanged.

## Failure boundaries and negative cases exercised

- Starter fails every group; a raising candidate is `error` for every group,
  not a hang; the reference passes every group and scores identically twice.
- Six deliberate mutants (three per exercise) pass every group below their
  level and fail at their level: scan case order, inclusive expiry, non-rebased
  restore lifetimes; insertion-order ties, strictly-later schedule execution,
  exclusive history bound.
- Reference rejects an unknown operation and an empty query with `ValueError`;
  packaged groups each include a wrong-arity and an unknown-operation case.
- Content check rejects a renamed group, a stray `solution.py`, a stale hash
  and an extra import, each with its specific message; the check runs the
  runner-contract validation before the hash comparison.
- Catalog on a never-fetched workspace: File Storage unavailable, both
  originals available and packaged-original.

## Not run here, with reasons

- `just check wheel`: no interpreter with packaging prerequisites, so the
  outside-checkout install proving the bundled originals ship and the oracles
  do not cannot be executed here. The archive allowlist that check enforces is
  unit-tested, and 006/01 owns the end-to-end proof.
- `just verify` fixture-cache scope: no fetched cache; network fetch of
  third-party content is not authorized.
