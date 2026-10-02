# Sequence testing gate — 006/01_acceptance_and_distribution

Covers 01_full_acceptance_matrix and 02_offline_and_docs. The matrix itself
(`results/acceptance_matrix.md`) maps every R1–R11 row to executed evidence;
`results/offline_and_docs.md` records the packaged, offline and documentation
proof. This gate reruns every suite on the final code of the sequence.

## Commands run and results (final code, 2026-09-13)

    just check unit                                            459 tests OK (1 skipped)
    just check browser (locked privacy reporters, source)      199 passed, 0 failed
    just check wheel (build_mode pep517-hooks; wheel 67, sdist 127, static 14 members;
      installed into a temp venv with --no-index, network denied)   199 passed, exit 0
    just check frontend                                        passed
    just build assets (twice) / just build assets-check        identical manifest hash; verified
    just check content                                         2 exercises × 7 files OK
    python3 scripts/verify_manifest.py --scope tracked / git-boundary   passed
    python3 -m unittest tests.test_documentation               6 OK (after the README rewrite)
    git diff --check                                           clean

All three heavy suites ran sequentially on the same final tree (unit, then
browser, then wheel), after the last code change of the sequence (the history
"Last practice" label and the README transcript completion).

## What this sequence added and proved

- New evidence: `tests/test_end_to_end.py::test_original_exercise_console_lifecycle_restart_history_review_and_end`
  (console, packaged original, no fetch: catalog → start → test exit 5 →
  restart + replay → history → review → stale/valid abandon → refused submit →
  two-page filtered history → cursor/filter mismatch);
  `webui/tests/acceptance_matrix.spec.mjs` (stale second tab cannot restart;
  a real `session/v1` record listed and reviewed without upgrade).
- Defects found by executing the matrix, fixed with unit tests:
  `PackagedOriginalProvider` now tolerates pip's `__pycache__` beside bundled
  files (installed originals were refused before);
  `scripts/packaging_support.py::discover_builder` lets `just check wheel`
  build through the setuptools PEP 517 hooks when `build` is absent.
- Documentation: README rewritten for the library, End/Restart/Reset, history
  and review with real CLI transcripts and negative paths, record
  compatibility statement, offline install, troubleshooting;
  `docs/cli-contract.md` and `docs/agent-safety.md` updated;
  `tests/test_documentation.py` passes.

## Failure boundaries exercised in this sequence

- Installed package with byte-compiled bundled files; a stray file, a plain
  file or a symlink named `__pycache__` still refused.
- Wheel check with and without a `build` frontend; unknown build mode raises.
- CLI: stale revision (exit 4), operation replay and changed-argument conflict
  (exit 4), live selection (exit 4), submit after end (exit 4
  `illegal_lifecycle`), candidate failure (exit 5), cursor issued for another
  filter (exit 2).
- Browser: stale tab restart after another tab restarted; legacy record with
  no review and no events; both under the locked privacy reporters.

## Not run here, with reasons

- `verify_manifest.py --scope fixture-cache` (inside `just verify` and
  `run_legacy_checks.py`): the third-party File Storage cache is absent and
  fetching it over the network is not authorized. The `tracked` and
  `git-boundary` scopes pass; the unit and end-to-end suites `just verify`
  runs are reported above.
- `python -m build --no-isolation`: no `build` distribution on this machine;
  the wheel check used the equivalent PEP 517 hook path and reports it.
- TypeScript type checking: no `tsc` in the locked toolchain.
