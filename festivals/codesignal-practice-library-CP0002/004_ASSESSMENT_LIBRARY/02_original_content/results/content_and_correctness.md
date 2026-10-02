# Content and correctness

Authored by the coordinator on 2026-09-12 in the linked cp0002-practice-library
worktree. Uncommitted pending this sequence's 06_fest_commit gate.

## What changed

- `src/codesignal_practice_simulator/resources/assessments/in_memory_records/`
  and `.../account_ledger/`: `level1.md`–`level4.md` (candidate-facing prompts
  derived from `docs/content/*.md`), `simulation.py` (starter returning `[]`),
  `test_simulation.py` (`TestSimulateCodingFramework.test_group_1..4`, group N
  covering levels 1..N, each with the worked example, boundary cases and one
  `ValueError` case; imports only `unittest` and `simulation`), and
  `content-manifest.json` (`assessment-package/v1`, versions `records-1` and
  `ledger-1`, SHA-256 per candidate-facing file, generated from the bundled
  bytes).
- `assessments.py`: `IN_MEMORY_RECORDS` and `ACCOUNT_LEDGER` packaged-original
  definitions via `_original(...)`; `DEFAULT_ASSESSMENT_REGISTRY` now lists
  File Storage plus both originals, so the isolated scorer accepts them and the
  catalog, bootstrap, CLI and HTTP expose them.
- `tests/oracles/`: development-only reference implementations
  (`in_memory_records_reference.py`, `account_ledger_reference.py`) with
  anchored comments where deliberate mutations are applied in tests. The
  directory is under `tests/`, outside every package-data glob and rejected by
  the archive allowlist if it ever appeared under `resources/assessments/`.
- `scripts/check_content.py` + `just check content`: build-time check that the
  bundled directories match the packaged definitions exactly (file set,
  regular files, manifest schema/ID/hashes, non-empty prompts) and that the
  test module defines exactly the four runner entry points with only the two
  allowed imports. The runner-contract check runs before the hash check so a
  renamed group is reported as such.
- `tests/test_original_content.py` (7 tests) and an updated catalog route
  assertion for the three-entry default registry.
- `docs/cli-contract.md`: bundled originals, `just check content`, oracles.

## Correctness proofs (tests/test_original_content.py)

Real attempts are created through `LifecycleService.start` with a
never-fetched cache and scored by the real `IsolatedAttemptScorer`
(subprocess per group, isolated import path, audit hook):

- Starter fails all four groups for both exercises; the attempt stays active.
- Reference passes all four groups; scoring twice yields identical results.
- Three deliberately wrong implementations per exercise (case-insensitive scan
  order, inclusive expiry, non-rebased restore lifetimes; insertion-order
  ranking ties, strictly-later schedule execution, exclusive history bound)
  pass every group below their level and fail their level's group.
- Reference matches the specification examples in-process and raises
  `ValueError` on an unknown operation and on an empty query.
- A candidate that raises produces `error` for every group, never a hang.
- Content check: bundled directories satisfy the contract; a renamed group, a
  stray `solution.py`, a stale hash and an extra import are each rejected with
  the specific error.
- Registry/catalog: the never-fetched workspace lists File Storage unavailable
  and both originals available offline.

The packaged `test_simulation.py` files were also run directly against the
oracles (4 tests each, OK). Two arithmetic slips in the hand-written ledger
expectations surfaced this way and were corrected against the specification
(the reference was right both times).

## Evidence

    just check content                                   both exercises OK
    python3 -m unittest tests.test_original_content      7 tests OK
    just check unit                                      452 tests OK (1 skipped)
    just check browser                                   175 passed
    just check frontend                                  passed
    python3 -m unittest tests.test_documentation         OK
    git diff --check                                     clean
    grep -rin codesignal docs/content/ resources/assessments/   nothing

## Not run here

`just check wheel` (outside-checkout install with network disabled) cannot run
without packaging prerequisites; the archive allowlist and content check are
unit-tested, and 006/01 owns the end-to-end wheel proof.
