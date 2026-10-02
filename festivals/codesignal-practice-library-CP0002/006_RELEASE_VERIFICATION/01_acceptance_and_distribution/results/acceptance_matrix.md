# Acceptance matrix — R1–R11 against executed evidence

Recorded 2026-09-13 in the linked worktree
`projects/worktrees/codesignal-practice-simulator/cp0002-practice-library`.
Every row names the command or spec that produced the evidence, the
environment it ran in, and the observable outcome. Synthetic workspaces and
the locked Playwright privacy reporters only; no real candidate work, cache or
reference material was read.

Environment: macOS, Python 3.14 (`python3`) for unit and end-to-end suites;
Chromium via Playwright 1.63 for browser journeys; the packaged check builds
the wheel with the setuptools PEP 517 hooks on Python 3.11 (see row R11-1) and
installs it into a fresh venv under a temporary directory with network denied.

## Added for this matrix

- `tests/test_end_to_end.py::test_original_exercise_console_lifecycle_restart_history_review_and_end`
  (console entry point, packaged original, no fetch cache): catalog readiness,
  start → test (exit 5, `candidate_failure`) → restart with an explicit
  operation ID and its replay → history → review of the ended attempt →
  stale then valid abandon → refused submit → filtered two-page history and a
  cursor/filter mismatch.
- `webui/tests/acceptance_matrix.spec.mjs`: a stale second tab cannot restart
  an attempt another tab already restarted (one replacement, old bytes
  unchanged, no POST from the stale tab); a real `session/v1` record written to
  the workspace is listed and reviewed honestly and never upgraded.
- Two defects surfaced and fixed while executing the matrix:
  `PackagedOriginalProvider` refused an installed package because pip's
  `__pycache__` sat beside the bundled files (R11 blocker, only visible on an
  installed wheel); `just check wheel` could not run without the `build`
  distribution and now falls back to the setuptools PEP 517 hooks
  (`scripts/packaging_support.py::discover_builder`). Both have unit tests.

## Matrix

| ID | Requirement / scenario | Evidence (command or spec) | Environment | Outcome |
|---|---|---|---|---|
| R1-1 | Library lists every installed exercise with readiness; primary first | `webui/tests/library_routes.spec.mjs` "library lists catalog readiness…" | browser, source | pass: three cards Ready, File Storage first and selected |
| R1-2 | Catalog readiness from CLI/HTTP, setup reasons, no side effects | `tests/test_catalog_distribution.py` (9) | unit | pass |
| R1-3 | Original exercise starts offline without the fetched cache | `tests/test_input_providers.py::test_original_starts_offline_without_the_fetched_cache`; e2e console lifecycle (catalog shows File Storage `fetch_required`, Account Ledger available; `.cache` never created) | unit + e2e subprocess | pass |
| R2-1 | Four-level correctness of each original with deterministic packaged tests | `tests/test_original_content.py` (7, nine mutants caught); `just check content` | unit | pass |
| R2-2 | Bundled content is exactly the six candidate files + manifest | `tests/test_input_providers.py` tampered/stray cases; `tests/test_packaging_support.py` archive allowlist; `test_installed_bytecode_cache_is_tolerated_but_never_staged_or_widened` | unit | pass |
| R3-1 | Restart creates one replacement, old bytes unchanged, timer only in the new attempt | `webui/tests/restart_end.spec.mjs` "restart keeps the old attempt's saved bytes…"; e2e console lifecycle (`simulation.py`/prompts byte-identical, only `session.json`, `events.jsonl`, `STATUS.md` change) | browser + e2e | pass |
| R3-2 | Duplicate restart (same tab, lost response, real server restart) yields one replacement | `restart_end.spec.mjs` "duplicate restart clicks and a retry after a lost response reuse one operation" | browser, fixture process killed and relaunched | pass |
| R3-3 | Stale tab duplicate restart | `acceptance_matrix.spec.mjs` "a stale tab cannot restart…" | browser, two tabs | pass: stale tab refreshes to Ended, zero POST, listing shows exactly old+replacement |
| R3-4 | Same operation ID replayed by the CLI | e2e console lifecycle (`restart --operation-id` twice → `replayed: true`, same replacement) | e2e | pass |
| R4-1 | End attempt records `abandoned` without a score, saved work readable | `restart_end.spec.mjs` "end attempt records an ended attempt…"; e2e console lifecycle (`abandon --expected-revision`, stale revision → exit 4 `stale_revision`) | browser + e2e | pass |
| R4-2 | Unsaved editor text gated behind explicit discard | `restart_end.spec.mjs` "restart with unsaved text is blocked…" | browser | pass |
| R4-3 | Reset source keeps ID, status and timer; conflicting transitions blocked while a submit is in flight | `restart_end.spec.mjs` "a submission in flight blocks restart and end…" | browser | pass |
| R4-4 | Live selection never displaced by plain start/resume | `tests/test_lifecycle_actions.py` (18, incl. cross-process flock); `webui/tests/editor.spec.mjs` 423 message | unit + browser | pass |
| R5-1 | History lists metadata only, newest first, bounded pages, cursor bound to filters | `webui/tests/history_screen.spec.mjs` (5); `tests/test_attempt_history.py` (11); e2e console lifecycle (`--limit 1` two pages, cursor with other filter → exit 2 `invalid_input`) | browser + unit + e2e | pass |
| R5-2 | Growing collection while paginating shows refresh guidance | `history_screen.spec.mjs` "pages newest-first…" (attempt created on an older page; Newest shows it; older-page note) | browser | pass |
| R5-3 | Corrupt, unsafe and missing entries shown honestly | `history_screen.spec.mjs` "skipped and corrupt entries…" (symlink + non-UUID counted; corrupt row Unavailable, Review disabled) | browser | pass |
| R6-1 | Review never rescored, never selects, review bytes immutable | `webui/tests/review_screen.spec.mjs` "reviews a submission while another attempt is live…"; `tests/test_attempt_reviews.py` (16); `tests/test_history_review_routes.py` | browser + unit | pass |
| R6-2 | Retry with a live attempt: resume or explicit end-and-start, never silent | `review_screen.spec.mjs` (Cancel, Resume, End it and start → exactly one abandon + one start) | browser | pass |
| R6-3 | Retry announces content-version difference; blocked when exercise missing or needs setup | `review_screen.spec.mjs` "legacy records are labelled…", "a removed catalog version keeps the stored review readable…" | browser (synthetic catalog/review payloads) | pass |
| R7-1 | Expired/ended attempts show saved work and last practice result, not a fabricated submission | `review_screen.spec.mjs` "an ended attempt shows its saved work…"; e2e console lifecycle (`review` of the ended attempt: `score: null`, `practice_score`, `not_applicable`) | browser + e2e | pass |
| R7-2 | Tampered/missing/pending review payloads are errors, never empty success | `review_screen.spec.mjs` "missing, pending and tampered reviews…" | browser | pass |
| R8-1 | Real `session/v1` record listed and reviewed without upgrade; legacy-unbound labels | `acceptance_matrix.spec.mjs` "a real legacy session/v1 record…" (bytes of `session.json`, `simulation.py`, `events.jsonl` identical after listing and review; no `active.json` created) | browser | pass |
| R8-2 | v1 reads, v2 writes, honest unavailable identity | `tests/test_attempt_models_v2.py`, `tests/test_creation_identity.py`, `tests/test_attempt_reviews.py` legacy cases | unit | pass |
| R8-3 | Stored results readable after a content version is removed | `tests/test_input_providers.py::test_stored_results_stay_readable_when_the_definition_is_gone`; `review_screen.spec.mjs` removed-catalog case | unit + browser | pass |
| R9-1 | Restart journal: crash before/after commit point, roll-forward, receipts, identical replay, changed-args conflict | `tests/test_restart_journal.py` (24) | unit, injected failures at each boundary | pass |
| R9-2 | Submission WAL recovery without rescoring | `tests/test_cli.py::test_submit_cli_recovers_a_failed_event_append_without_rescoring_or_touching_neighbors`; `tests/test_submission_capture.py` | unit | pass |
| R9-3 | Cross-process contention and races | `tests/test_lifecycle_actions.py` two-process and flock tests; `tests/test_workspace_pointer_recovery.py` | unit | pass |
| R9-4 | Recovery-pending surfaced and retried by the UI with the same operation | `restart_end.spec.mjs` "duplicate restart clicks and a retry after a lost response…" | browser | pass |
| R10-1 | Keyboard, focus to headings, dialogs trap/restore | `library_routes.spec.mjs`, `history_screen.spec.mjs`, `review_screen.spec.mjs`, `webui/tests/shell_layout.spec.mjs` | browser | pass |
| R10-2 | Reload, back, forward reconstruct library/attempt/history/review; no accidental timer start | `library_routes.spec.mjs` (6); `history_screen.spec.mjs` back through review | browser | pass |
| R10-3 | Server restart mid-flow | `restart_end.spec.mjs` (fixture relaunched between failed restart and retry); `webui/tests/actions.spec.mjs` submitted reconnect after a real process restart | browser | pass |
| R10-4 | Save conflict and stale tab | `webui/tests/source_save.spec.mjs`, `webui/tests/navigation.spec.mjs`; `acceptance_matrix.spec.mjs` stale tab | browser | pass |
| R11-1 | Wheel + sdist build and install outside the checkout, network denied, assets and originals served from the installed package | `just check wheel` (`scripts/run_packaged_browser.py`, build mode `pep517-hooks`) | temp venv outside checkout, `--no-index`, `SIMULATOR_DENY_EXTERNAL_NETWORK=1` | pass (exit 0): wheel 67 members, sdist 127, static 14; installed into `…/environment` under a temp root; 13 assets served by console and module entry points with matching digests; 199 browser journeys passed against the installed package (build_mode `pep517-hooks`, builder `python3.11`); temp root removed |
| R11-2 | Archive allowlist: only candidate-facing bundled files, no oracles | `tests/test_packaging_support.py` (8), `scripts/run_packaged_browser.py::inspect_archives` during R11-1 | unit + packaged check | pass |
| R11-3 | Security rejection: unauthorized origin, unsafe UUID, oversize/unsafe paths | `tests/test_web_server_safety.py`, `tests/test_web_server_static.py`, `tests/test_history_review_routes.py`, `webui/tests/accessibility_security_offline.spec.mjs` | unit + browser | pass |
| R11-4 | Deterministic bundled resources | `just build assets-check`; `scripts/check_content.py` manifest hashes (`just check content`) | local | pass |

## Suite totals (final code)

    just check unit                                            459 tests OK (1 skipped)
    just check browser (locked privacy reporters, source)      199 passed, 0 failed
    just check wheel (installed wheel, temp venv, no network)  199 passed, 0 failed; exit 0
    python3 -m unittest tests.test_end_to_end (new lifecycle test)   OK
    just check frontend                                        passed
    just build assets / assets-check                           rebuilt twice, identical manifest hash (21384695…)
    just check content                                         account_ledger ledger-1 (7 files), in_memory_records records-1 (7 files)
    verify_manifest.py --scope tracked / git-boundary          passed
    verify_manifest.py --scope fixture-cache                   not executed: fixture cache absent (fetch not authorized)
    python3 -m unittest tests.test_documentation               OK
    git diff --check                                           clean

One presentation tweak (history rows show "Last practice" for an active or
expired attempt's stored practice score) was made after the full source-mode
browser run; the bundle was rebuilt and the three specs that render those rows
(history, review, acceptance matrix; 12 journeys) were rerun and pass. The
sequence testing gate reruns every suite on the final code.

## Unresolved rows and limitations

- `just verify` includes the `fixture-cache` manifest scope, which needs the
  fetched third-party File Storage cache; fetching over the network is not
  authorized in this environment, so that scope is not executed here (the
  `tracked` and `git-boundary` scopes are). File Storage is proven only through
  the synthetic fixture cache used by every suite.
- Failure injection at WAL/journal boundaries is unit-level (R9-1/R9-2); the
  browser proves the retry path against a real killed-and-relaunched fixture
  process but not a crash injected inside the server's write sequence.
- No TypeScript type-checker is in the locked toolchain.
