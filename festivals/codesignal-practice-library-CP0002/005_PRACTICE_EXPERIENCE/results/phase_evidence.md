# Phase 005_PRACTICE_EXPERIENCE — deliverable inventory and evidence

Recorded 2026-09-12 for the implementation phase gate. Every path below is in
the linked worktree `projects/worktrees/codesignal-practice-simulator/
cp0002-practice-library` at commit `3409bd2` (branch `cp0002-practice-library`),
which contains the two sequence commits:

    3409bd2 feat: attempt history and read-only review screens with safe retry
    c72c8ab feat: routed practice library with catalog readiness and End/Restart/Reset attempt controls

Nothing is pushed; no PR exists. The audit checkout was not modified. The
worktree is clean after the second commit.

## Deliverable 1 — library and attempt routes (R10)

- `webui/src/router.ts` (96 lines): `parseRoute` :17 accepts exactly `/`,
  `/attempt/<uuid>`, `/history`, `/history/review/<uuid>`; everything else is
  `unknown`. `navigateTo` :82 pushes/replaces the path and keeps only the
  non-secret fragment; `installRouter` :64 routes `popstate`;
  `registerAttemptOpener` :55 / `openAttempt` :59 let attempt-level code open
  an explicitly chosen attempt.
- `webui/src/app.ts` (350 lines): `showRoute` :84 dispatches by route with a
  generation counter; `showLibrary` :137; `showAttemptRoute` :195 renders the
  metadata-only continue screen (bootstrap session or `GET /api/time` for a
  non-selected UUID); `reconnect` :260 is the only path that reads source;
  `openChosenAttempt` :71 opens a restart replacement or a retried attempt;
  `showHistoryRoute` :293 and `showReviewRoute` :310 mount the screens below.
- `webui/src/library_view.ts` (463 lines): `renderLibrary` :34 (exercise cards
  with readiness from the bootstrap catalog, primary first, one start form,
  confirmation dialog, selected-session summary, History entry) and
  `renderAttemptEntry` :140 (continue screen).
- Server: `web/routes.py::is_shell_path` :413 serves `index.html` for `/`,
  `/index.html` and every query-less path under `/attempt` or `/history`
  (`_APP_ROUTE` :410); `web/server.py` :370 applies the shell CSP to the same
  set. The path never selects a file.
- Browser status `abandoned` and its labels: `attempt_state.ts`,
  `attempt_state_normalization.ts`, `attempt_dom.ts`, `attempt_results.ts`.

Tests: `webui/tests/library_routes.spec.mjs` (6): catalog readiness and
primary-first selection; zero mutations until "Confirm and start"; back →
library, forward → continue screen, explicit reconnect performs one source
request; direct attempt address never starts a timer (bootstrap session and
deadline unchanged); unknown UUID → "Attempt not found", malformed → "Page not
found", both back to library; history/review shells never select an attempt;
bootstrap failure → safe error with reload.
`tests/test_web_server_static.py::test_browser_routes_serve_the_shell_without_touching_assets`:
route prefixes serve identical shell bytes with CSP and HEAD parity;
`/attempt/../app.js`, `/attempts`, `/histories`, query-bearing routes stay 404.

## Deliverable 2 — End / Restart / Reset controls (R3/R4)

- `webui/src/attempt_lifecycle_actions.ts` (232 lines): `endAttempt` :38 and
  `restartAttempt` :49 open confirmation dialogs; `performEnd` :69 and
  `performRestart` :101 run under the `lifecycle` operation lease
  (`attempt_operation_lock.ts`), flush the editor first
  (`flushForTransition` :172) and require an explicit "Discard unsaved edits"
  choice when the latest text cannot be saved; `currentRevision` :200 reads the
  revision from a fresh `/api/time` and refreshes into the terminal view if the
  attempt is no longer active. Restart mints one `crypto.randomUUID()` per
  attempt (`AttemptRuntime.restartOperationId`), reuses it on every retry and
  drops it only after `stale_revision`/`lifecycle_locked`; on success the
  replacement opens through `openAttempt`.
- `webui/src/attempt_panes.ts::createActionBar`: "Reset source", "End
  attempt", "Restart", "Submit" as mutation controls; header "Back to library".
- `webui/src/api.ts`: `abandonAttempt`, `restartAttempt`,
  `describeLifecycleError` (fixed copy for `stale_revision`,
  `operation_conflict`, `recovery_pending`, `lifecycle_locked`, unreachable).
- `docs/cli-contract.md` "Attempt actions in the browser and their CLI
  equivalents" (End = `abandon --expected-revision`, Restart = `restart
  --expected-revision [--operation-id]`, Reset source has no CLI command).

Tests: `webui/tests/restart_end.spec.mjs` (6): restart keeps the old
`simulation.py` bytes and records `abandoned`/`restarted` while the
replacement is active with the same profile; duplicate clicks impossible under
the lock, a synthetic `recovery_pending` then a real fixture process restart
retried with the same operation ID yields one replacement and its completion
receipt; unsaved text is gated behind the discard dialog and the stored source
keeps only the saved marker; a held submit disables Restart/End/Reset and Reset
keeps ID, status and deadline; End records `abandoned`/`ended` with `score:
null` and read-only saved work; `stale_revision` refreshes and mints a new
operation ID.

## Deliverable 3 — history and review screens (R5–R7/R10)

- `webui/src/history_state.ts` (287 lines): `readHistoryFragment` :79 (shape
  validation, notices for malformed values), `historyRequestPath`,
  `normalizeHistoryPage` :142 (rows with unreadable records carry `status:
  null`, `available: false`; practice results only on ended rows).
- `webui/src/history_view.ts` (398 lines): `renderHistory` :69 — filters,
  rows per page, Refresh, warnings, error banner with Retry / Show newest,
  table with status, format, start, result, review availability, Unavailable
  badge with issue codes, Review and selected-attempt Resume, Newest/Older with
  the refresh note on older pages.
- `webui/src/history_screen.ts` (120 lines): `mountHistory` :29 — listing and
  bootstrap fetched together, generation-guarded, fragment rewritten on
  filter/page changes, focus carried across re-renders.
- `webui/src/review_state.ts` (196 lines): `normalizeReview` :50 — identity
  equal to the route UUID, pinned records need version and digest, binding and
  source view must agree in both directions, `practice_score` only on ended
  attempts.
- `webui/src/review_view.ts` (430 lines): `retryPlan` :58 (catalog lookup,
  blocked reasons, version notice, live attempt) and `renderReview` :94
  (metadata, legacy banners, "Final result" vs "Last practice result", source
  pane naming its binding, Retry section with the conflict or confirm dialog).
- `webui/src/review_screen.ts` (161 lines): `mountReview` :33 — review read,
  saved work for never-submitted attempts via `/api/source?attempt_id=`,
  `startRetry` (abandon at a fresh revision only when the user chose "End it
  and start", then start; `busy` guard).
- Server: `attempt_reviews.py::AttemptReview.practice_score` :122, assembled
  from `adapted.practice_score` :257; documented in `docs/cli-contract.md`
  ("Submission review record").

Tests: `webui/tests/history_screen.spec.mjs` (5): empty history, keyboard
order; newest-first paging with a growing dataset, status and exercise
filters, fragment preserved through review and browser back, `active.json`
unchanged, Resume for the selected active attempt; skipped and corrupt entries
reported without hiding safe rows; malformed fragment and server-rejected
cursor recover; listing failure with a path in server text shows safe copy and
Retry. `webui/tests/review_screen.spec.mjs` (5): submission reviewed while
another attempt is live with read-only source and unchanged `review.json`,
conflict dialog Cancel/Resume/End-and-start (one abandon, one start); ended
attempt shows saved work and last practice result and retries without a live
conflict; legacy record banners and version-change notice; removed and
setup-required catalog versions block Retry with the reason; missing, pending
and tampered payloads are errors. `tests/test_attempt_reviews.py::
test_ended_attempt_reports_its_last_practice_result_not_a_submission`.

## Verification (final code)

    just check frontend                                        passed
    just build assets / assets-check                           rebuilt; manifest verified
    just check unit                                            455 tests OK (1 skipped)
    just check browser (locked privacy reporters)              197 passed, 0 failed
    python3 -m unittest tests.test_web_server_static           8 OK
    python3 -m unittest tests.test_attempt_reviews             16 OK
    python3 scripts/verify_manifest.py --scope tracked / git-boundary   passed
    python3 -m unittest tests.test_documentation               OK
    git diff --check                                           clean

Not run, with reasons: `just check wheel` and the `just verify` fixture-cache
scope (no packaging interpreter; no fetched cache; network fetch not
authorized) — owned by 006/01. No TypeScript type-checker is in the locked
toolchain; the esbuild bundle and the browser journeys are the verification.

## Review dispositions

| Sequence | Finding | Disposition |
|---|---|---|
| 01 | F1: restart success announcement dropped by live-region disposal | Fixed (05_iterate): announcement removed; reconnect screen announces |
| 01 | F2 nit: fragment kept across routes | Left, deliberately: non-secret view state; preserving it restores level/tab on "Back to library → Reconnect" (asserted by navigation.spec) |
| 01 | Coordinator nit: nested dialog reuse | Checked safe by both reviewers; no change |
| 02 | F1 blocking: binding/source agreement checked in one direction | Fixed (05_iterate): both directions enforced; tampered-payload test extended |
| 02 | F2: stale bootstrap assigned before generation check | Fixed (05_iterate) |
| 02 | F3: focus dropped when the focused control re-rendered disabled | Fixed (05_iterate): heading fallback; asserted in history_screen.spec |
| 02 | F4 nit: docs rows-per-page range | Fixed (05_iterate) |
| 02 | F5 nit: practice_score/status not cross-checked in history rows | Fixed (05_iterate) |

## Carried to 006/007

- `WorkspaceManager.recover_restarts()` at server startup; orphan staging
  housekeeping; `just check wheel` / outside-checkout wheel proof (006/01).
- Full-suite flake observed once (shell_lifecycle live-region timing test);
  passes alone and in every later full run; no code change made.
