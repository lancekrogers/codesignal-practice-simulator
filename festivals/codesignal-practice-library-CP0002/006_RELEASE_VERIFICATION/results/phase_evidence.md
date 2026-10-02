# Phase 006_RELEASE_VERIFICATION — deliverable inventory and evidence

Recorded 2026-09-13 for the implementation phase gate. Every path below is in
the linked worktree `projects/worktrees/codesignal-practice-simulator/
cp0002-practice-library` at commit `7de41d3` (branch `cp0002-practice-library`),
the single sequence commit of this phase:

    7de41d3 test: release verification matrix, installed-package fixes and operating docs

Nothing is pushed; no PR exists. The audit checkout was not modified. The
worktree is clean after the commit.

## Deliverable 1 — acceptance matrix (R1–R10)

`006_RELEASE_VERIFICATION/01_acceptance_and_distribution/results/acceptance_matrix.md`:
35 rows (R1-1 … R11-4) mapping each requirement scenario to a command or spec,
its environment and the observed outcome, plus an "Unresolved rows and
limitations" section.

New executed evidence written for the matrix:

- `tests/test_end_to_end.py::test_original_exercise_console_lifecycle_restart_history_review_and_end`
  (console entry point, packaged original Account Ledger, no fetch cache):
  `catalog` readiness (File Storage `fetch_required`, originals available);
  `start --assessment account_ledger --mode drill --drill-duration-seconds 120`;
  `test` exit 5 `candidate_failure` with the practice score visible in
  `status`; `restart --expected-revision 1 --operation-id …` then the same
  command again → `replayed: true`, same replacement; candidate files
  byte-identical, only `session.json`, `events.jsonl`, `STATUS.md` changed;
  `history` (two rows, statuses, `practice_score`, `review_available: false`);
  `review --attempt <old>` (`abandoned`, `score: null`, `practice_score`,
  `not_applicable`, `content_identity: pinned`, tree unchanged, pointer
  unchanged); `abandon --expected-revision 7` → exit 4 `stale_revision`, then
  `--expected-revision 0` → `newly_abandoned: true`; `submit` → exit 4
  `illegal_lifecycle`; `history --status abandoned --limit 1` across two
  pages; cursor reused with another filter → exit 2 `invalid_input`.
- `webui/tests/acceptance_matrix.spec.mjs` (2): a stale second tab (own
  capability capture from the fragment) cannot restart an attempt another tab
  already restarted — its restart finds the attempt ended, refreshes to the
  read-only view, sends zero POST/PUT; `active.json` names the single
  replacement, the listing has exactly old+replacement, old `simulation.py`
  bytes unchanged. A real `session/v1` record written into `attempts/` is
  listed (Submitted, `Final: 2 of 4 levels`, "No submission review stored")
  and reviewed with both legacy banners, `session/v1`, "Current file (not
  proven submitted)"; `session.json`, `simulation.py`, `events.jsonl`
  byte-identical afterwards and no `active.json` created.

Existing suites the rows cite (all rerun on the final code): unit 459 OK,
browser 199 passed, wheel 199 passed.

## Deliverable 2 — offline distribution and operating docs (R11)

`006_RELEASE_VERIFICATION/01_acceptance_and_distribution/results/offline_and_docs.md`.

- `just check wheel` (`scripts/run_packaged_browser.py::main` :387,
  `verify_installed_package` :420, `build_archives` :471): sdist and wheel
  built from the checkout, installed with `pip install --no-index --no-deps`
  into `python -m venv` under a temporary root, import origins proven inside
  the venv and outside the checkout, 13 served assets digest-matched through
  both entry points, 7 synthetic records prepared, 199 browser journeys with
  `SIMULATOR_DENY_EXTERNAL_NETWORK=1`; summary `{"archives": {"sdist_members":
  127, "static_members": 14, "wheel_members": 67}, "build_mode":
  "pep517-hooks", "builder": ".../python3.11", "browser": {"status":
  "passed"}}`; exit 0; temp root removed.
- `scripts/packaging_support.py::discover_builder` :(new) with
  `BUILD_MODE_FRONTEND`/`BUILD_MODE_HOOKS`, `_probe_setuptools_floor`
  (setuptools >= 61); `packaging_prerequisite_error` names the fallback.
  Tests: `tests/test_packaging_support.py::test_builder_prefers_the_build_frontend_and_falls_back_to_hooks`,
  `::test_build_archives_hook_mode_calls_setuptools_in_the_checkout`,
  extended `::test_missing_prerequisite_error_names_wheel_and_remediation`.
- `src/codesignal_practice_simulator/input_providers.py::PackagedOriginalProvider.validate`
  tolerates exactly a real `__pycache__` directory (`_is_bytecode_cache`),
  never reads or stages it, refuses every other extra entry. Test:
  `tests/test_input_providers.py::test_installed_bytecode_cache_is_tolerated_but_never_staged_or_widened`
  (installed layout starts; stray file, plain-file `__pycache__` and
  symlinked `__pycache__` refused). Before this fix an installed wheel
  reported both originals `packaged_content_invalid`.
- Assets rebuilt twice: identical `manifest.json` hash
  `21384695d98280be4b22a6d311912b54c02f0de7d37719869b01eb604da26e12`, same
  file set; `just check content`: 2 exercises × 7 files.
- Docs: `README.md` (library readiness table; catalog/start transcripts;
  "During an attempt: Reset source, End attempt, Restart" with
  `stale_revision`, restart, replay, `operation_conflict`, `live_selection`
  transcripts; "History and review" with `candidate_failure`, filtered
  history, review, `session_unavailable`, cursor mismatch transcripts;
  "Record compatibility"; offline wheel install; workspace tree;
  troubleshooting rows; contributor commands and `just check wheel`
  prerequisites), `docs/cli-contract.md` (`__pycache__` tolerance, build
  modes), `docs/agent-safety.md` (End/Restart are the candidate's decisions).
  `tests/test_documentation.py` 6 OK.

## Verification (final code)

    just check unit                                            459 tests OK (1 skipped)
    just check browser (locked privacy reporters, source)      199 passed, 0 failed
    just check wheel (installed wheel, temp venv, no network)  199 passed, exit 0
    just check frontend                                        passed
    just build assets ×2 / assets-check                        identical manifest hash; verified
    just check content                                         OK
    verify_manifest.py --scope tracked / git-boundary          passed
    verify_manifest.py --scope fixture-cache                   not executed (cache absent; fetch not authorized)
    python3 -m unittest tests.test_documentation               OK
    git diff --check                                           clean

## Review dispositions

| Finding | Disposition |
|---|---|
| Reviewer: no blocking, no non-blocking findings | — |
| Nit: README replayed-restart transcript omitted `abandoned_session: null` | Fixed (05_iterate); docs tests OK |

## Unresolved, carried to 007

- Fixture-cache manifest scope and the real upstream fetch need the
  third-party cache (network fetch not authorized here).
- `python -m build --no-isolation` was not itself exercised (no `build`
  distribution); the hook path calls the same backend and is what produced the
  verified archives.
- `WorkspaceManager.recover_restarts()` at server startup remains a
  follow-up; the retry path is proven with a real process restart.
