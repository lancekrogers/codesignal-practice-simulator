# History screen

Implemented by the coordinator directly on 2026-09-12 in the linked
cp0002-practice-library worktree. Uncommitted pending 06_fest_commit.

## What changed

- `webui/src/history_state.ts` (new): the `/history` screen state. Filters
  (`status`, `assessment_id`), the page `cursor` and `limit` live in the URL
  fragment (never a query string, which the server refuses for shell routes,
  and never source or a token). `readHistoryFragment` validates each value by
  shape (status enum, `[a-z0-9_]+` exercise id, base64url cursor up to 4096
  chars, integer limit 1–100) and reports each malformed value as an issue that
  falls back to the default. `normalizeHistoryPage` validates every field of
  the 003/03 listing document (items, `next_cursor`, warnings, limit; rows
  whose record could not be read carry `status: null` and `available: false`).
- `webui/src/history_view.ts` (new): heading with focus target, Back to
  library, exercise/status/rows-per-page filters (10/25/50/100, default 25),
  Refresh, one `role=status` line, fragment-issue notices, aggregate warning
  banners (`unsafe_entries_skipped`, `unavailable_records_excluded_by_filter`,
  `restart_journals_unreadable`), an error banner with Retry and Show newest,
  a table of rows (exercise and content version, effective status with a "not
  yet recorded" note when it differs from the persisted one, format, start
  time, result: final score / last practice score / none, review availability,
  Unavailable badge with issue labels), Review per row (disabled when
  unavailable) and Resume only for the selected active attempt, Newest/Older
  paging with the D004 refresh note on older pages.
- `webui/src/history_screen.ts` (new): controller. Each load fetches the
  listing and the bootstrap together (so Resume reflects the attempt selected
  now); superseded requests are dropped by a request generation and the route
  generation; filter changes reset the cursor and rewrite the fragment;
  keyboard focus is carried across re-renders by element id (heading first,
  then the control the user was on).
- `webui/src/api.ts`: `describeApiError(…, "history")` maps `invalid_input` /
  `invalid_query` (rejected cursor or filters) to "Show newest",
  `history_unavailable` and unreachable server to Retry, all with fixed copy.
- `webui/src/app.ts`: the history route mounts the screen; Review navigates
  to `/history/review/<uuid>` keeping the fragment; Resume opens the selected
  attempt through the same explicit path as the library.
- `docs/cli-contract.md`: `/history` row in "Browser routes".
- `webui/src/styles/base.css`: filters, table, notices, pagination.

## Deliberate decisions

- Fragment, not query string, for history state: the server serves the shell
  only for query-less routes, the fragment is never sent to the server, and the
  existing attempt view state already uses it. Because `navigateTo` preserves
  the fragment, Review and "Back to history" (and browser back) return to the
  same filters and page without extra plumbing.
- Resume is offered only for the currently selected active attempt: resuming
  another active record would have to displace the live selection, which D001
  reserves for explicit end/restart flows.
- Rows per page is a visible control (10–100) rather than a hidden constant so
  the D004 bound is user-facing; the API still enforces 1–100.

## Negative cases proven (`webui/tests/history_screen.spec.mjs`, 5 journeys)

- Empty collection: explanatory status, disabled paging, only `GET
  /api/bootstrap` and `GET /api/attempts` requested (no source, review or
  mutation), keyboard order heading → Back to library → three filters →
  Refresh.
- Growing collection with `limit=2`: newest-first order by creation time
  (fixture clock advanced per attempt), Older/Newest walk with the cursor in
  the fragment and the refresh note on the older page, an attempt created
  while on the older page appears on Newest; status filter then exercise
  filter narrow the rows and rewrite the fragment; Review keeps the fragment,
  Back to history restores both filters, browser back twice returns to the
  filtered list; `attempts/active.json` is byte-identical after the review; no
  mutation, source or review request from the screen; after a live attempt is
  started, Refresh shows it with Resume and Resume opens the editor.
- Skipped and corrupt entries: a non-UUID directory and a symlink are counted
  in the warning banner; a UUID directory with unparsable `session.json` is a
  row marked Unavailable / Record corrupt / Unknown exercise with Review
  disabled, while the good row stays reviewable; no path text in the DOM.
- Malformed fragment (`cursor=%%%`, `limit=abc`): notices, defaults applied,
  fragment cleaned, no request with the bad values; a well-shaped cursor the
  server rejects (422) shows the alert and "Show newest" recovers.
- Listing failure (`history_unavailable` with a path in the server text): safe
  alert without the path, status line, Retry recovers.

## Evidence

    just check frontend                                   metadata/lockfile/license OK
    just build assets                                     rebuilt
    just build assets-check                               manifest verified
    npx playwright test history_screen.spec.mjs library_routes.spec.mjs --reporter=list   11 passed
    just check browser (locked privacy reporters)         189 passed, 1 failed, 2 skipped
      → the failure was shell_lifecycle "coalesces duplicate live announcements
        and disposes pending frames" (a pre-existing live-region timing test;
        its two serial siblings were skipped); the spec passes 11/11 alone.
        The whole suite is rerun at the sequence testing gate.
    python3 -m unittest tests.test_documentation          OK
    git diff --check                                      clean

Server change made alongside (used by the review screen next): `AttemptReview`
now carries `practice_score` (the ended attempt's last local practice result,
null otherwise); `tests.test_attempt_reviews` gains
`test_ended_attempt_reports_its_last_practice_result_not_a_submission`
(30 review/route/doc tests OK) and `docs/cli-contract.md` documents how
never-submitted attempts read.

## Carried forward

- The review route still shows the shell from 005/01; 02_review_screen
  replaces it and keeps the fragment contract for Back to history.
