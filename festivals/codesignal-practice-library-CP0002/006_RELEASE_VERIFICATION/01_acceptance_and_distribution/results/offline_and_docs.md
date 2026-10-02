# Offline distribution and documentation — R11

Recorded 2026-09-13 in the linked worktree
`projects/worktrees/codesignal-practice-simulator/cp0002-practice-library`.

## Build and asset determinism

    just build assets            rebuilt; then rebuilt again with no source change
    just build assets-check      manifest verified after each build
    manifest.json sha256 before/after second build: 21384695d98280be4b22a6d311912b54c02f0de7d37719869b01eb604da26e12 (identical); same file set
    just check content           account_ledger: ledger-1 (7 files); in_memory_records: records-1 (7 files)

The bundled-resource manifests (`content-manifest.json`) hash the exact
packaged bytes; `scripts/check_content.py` recomputes them on every run.

## Wheel and sdist, installed outside the checkout, network denied

`just check wheel` (`scripts/run_packaged_browser.py`) on this machine:

    builder      /home/build-user/.local/bin/python3.11
    build_mode   pep517-hooks   (no `build` distribution installed; setuptools 82 hooks called in-process)
    archives     wheel 67 members, sdist 127 members, static 14 members (13 assets + manifest)
    install      python -m venv <temp>/environment; pip install --no-index --no-deps <wheel>
    probe        package, cli, web resources and static all import from the venv's site-packages,
                 nothing from the checkout; PYTHONHOME/PYTHONPATH absent; node/npm/npx not on PATH;
                 13 served assets match the built digests through both `codesignal-sim web` and
                 `python -m codesignal_practice_simulator web` (loopback only)
    fixture      installed fixture driver prepared 7 synthetic records
    browser      199 Playwright journeys passed against the installed package with
                 SIMULATOR_DENY_EXTERNAL_NETWORK=1 and SIMULATOR_REQUIRE_ISOLATION=1
    cleanup      temporary wheel, venv, fixtures, attempts and traces removed; exit 0

The archive inspection (`inspect_archives`) accepted exactly the six
candidate-facing files plus `content-manifest.json` per bundled exercise
(14 members under `resources/assessments/`) and found no `_reference.py`,
`_solution.py`, `_oracle.py` or `oracles` member in either archive; the
development oracles under `tests/oracles/` are not distributed.

Two defects were found and fixed by running this check for the first time on
an installed wheel (both have unit tests and are part of this sequence's
commit):

1. `PackagedOriginalProvider` refused every installed original with
   `packaged_content_invalid` because pip byte-compiles the bundled `.py`
   files at install time and the resulting `__pycache__` directory counted as
   an unexpected packaged entry. The provider now tolerates exactly a real
   directory of that name (never read, never staged) and still refuses any
   other extra entry, a file or a symlink wearing the name
   (`tests/test_input_providers.py::test_installed_bytecode_cache_is_tolerated_but_never_staged_or_widened`).
   Before the fix the installed catalog reported the originals as "Setup
   required" and `POST /api/attempts` returned 404 for them.
2. `just check wheel` could not run without the `build` distribution.
   `scripts/packaging_support.py::discover_builder` now prefers `python -m
   build --no-isolation` and falls back to calling `setuptools.build_meta`
   directly (the same backend, in-process) when setuptools >= 61, wheel, pip
   and venv are present; the summary reports `build_mode`
   (`tests/test_packaging_support.py`, three new tests). Nothing is downloaded
   in either mode.

## Originals offline, File Storage setup-gated

- Installed wheel, no fetch cache: catalog lists `account_ledger` and
  `in_memory_records` as available (`provider_kind: packaged-original`) and
  `file_storage` as `setup: fetch_required`; the installed browser suite
  starts, practices, restarts, ends, lists and reviews original attempts
  (199 journeys above).
- Source checkout, console entry point, no fetch cache:
  `tests/test_end_to_end.py::test_original_exercise_console_lifecycle_restart_history_review_and_end`
  starts Account Ledger, runs `test`, restarts (and replays the same
  operation), lists, reviews and ends attempts with `.cache/` never created.
- Fetch path: exercised with a synthetic `--source` tree by the end-to-end
  suite (`_fetch`), which verifies the seven pinned files land in
  `.cache/codesignal-fixtures/synthetic` with the manifest's hashes. The real
  upstream fetch over the network was not run (not authorized in this
  environment); the setup steps are documented in the README ("Practice →
  The library").

## Documentation updated (with real transcripts)

- `README.md`: library and readiness table (originals offline, File Storage
  fetch-gated), catalog/start transcripts, "During an attempt: Reset source,
  End attempt, Restart" with transcripts for `stale_revision` (exit 4),
  restart, identical replay (`replayed: true`), `operation_conflict` (exit 4)
  and `live_selection` (exit 4); "History and review" with `candidate_failure`
  (exit 5), filtered history, review of an ended attempt, `session_unavailable`
  (exit 3) and a cursor/filter mismatch (`invalid_input`, exit 2); "Record
  compatibility" (reads v1, writes v2, old binaries need not read v2, mixed
  writers unsupported, no downgrade-safety claim); offline wheel install
  outside the checkout with the `__pycache__` note; workspace tree with
  `review.json`, `.restart-journal/`, `.restart-completed/`; troubleshooting
  rows for `packaged_content_invalid`, `live_selection`, `stale_revision`,
  `recovery_pending`, `operation_conflict`, legacy-unbound review and
  unavailable records; contributor commands including `just check content`,
  `just check browser`, `just check wheel` and its prerequisites/fallback.
- `docs/cli-contract.md`: `__pycache__` tolerance and the wheel-check build
  modes in "Input providers"; earlier sections from 003–005 already document
  every new action, route and screen.
- `docs/agent-safety.md`: End attempt and Restart are the candidate's explicit
  decisions; agents must not use `abandon`/`restart` to work around a live
  selection.
- `tests/test_documentation.py` passes (6 OK) on the rewritten README.

## Known gaps and limitations

- `verify_manifest.py --scope fixture-cache` and the real upstream fetch need
  the third-party File Storage cache; not executed here. `just verify` therefore
  fails at that scope on this machine; its other steps (unit suite, end-to-end
  suite, whitespace) pass and are reported individually.
- The `build` distribution is absent on this machine; the wheel was built by
  the PEP 517 hook path. `python -m build --no-isolation` calls the same
  backend but was not itself exercised here.
- Transcripts in the README abbreviate long JSON documents with `…`; the full
  documents are the CLI's `--json` output (schema `cli/v1`).
