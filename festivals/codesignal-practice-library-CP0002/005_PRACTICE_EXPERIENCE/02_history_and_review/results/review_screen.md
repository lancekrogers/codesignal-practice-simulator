# Review screen

Implemented by the coordinator directly on 2026-09-12 in the linked
cp0002-practice-library worktree. Uncommitted pending 06_fest_commit.

## What changed

- `webui/src/review_state.ts` (new): `normalizeReview` validates every field
  of the stored review (identity equal to the route's UUID, status enum,
  pinned records must carry version and digest, source digest shape, bounded
  content, `not_applicable` never carries source, a `captured` source only
  under a `captured` binding). Anything else is an error screen, never an
  empty success.
- `webui/src/review_view.ts` (new): heading "Attempt review: <exercise>" with
  focus target, Back to history (fragment preserved, so the history filters
  and page come back) and Back to library, one `role=status` line ("Read-only
  review of a submitted/an ended/an expired attempt…"), legacy banners
  (`submitted_source_binding_unavailable`, `submitted_source_was_unreadable`,
  `legacy_source_unavailable`, content identity unavailable), a metadata list
  (exercise, pinned content version or "unavailable (legacy record)", status,
  format, started, deadline, submitted, record version), the result section
  labelled "Final result" only for a submission and "Last practice result"
  otherwise (from `score` for expired, `practice_score` for ended attempts,
  with the "not a final result" sentence), the source pane naming its binding
  ("Submitted source" with exact-bytes digest, "Current file (not proven
  submitted)", or "Saved work (not a submission)") as a read-only textarea,
  and the Retry section. `retryPlan` resolves the catalog entry: missing →
  disabled with "not installed" reason; setup required → disabled with the
  catalog's safe setup message; version notice when the pinned version differs
  from the library's or the record has no identity; live attempt → the
  conflict dialog "Resume active attempt" / "End it and start a new attempt" /
  Cancel; otherwise "Start a new attempt?" with the mode and exercise named.
- `webui/src/review_screen.ts` (new): controller. Loads
  `GET /api/attempts/{uuid}/review?include_source=true`; for a never-submitted
  attempt also `GET /api/source?attempt_id=` and shows it as saved work (a
  failure there is a note, not a fatal error). Retry posts `/api/attempts`
  with the reviewed profile's mode (and drill duration); "End it and start"
  first reads the live attempt's revision from `/api/time` and posts abandon,
  then starts. Failures use the fixed lifecycle/start copy and refresh the
  bootstrap so the next Retry reflects the current live selection.
- `src/codesignal_practice_simulator/attempt_reviews.py`: `AttemptReview.
  practice_score` (the ended attempt's last local practice result, null for
  every other status) so the screen never has to guess; documented in
  `docs/cli-contract.md` ("Submission review record") and covered by
  `test_ended_attempt_reports_its_last_practice_result_not_a_submission`.
- `webui/src/api.ts`: `describeApiError(…, "review")` maps
  `session_unavailable` → "Attempt not found" (no retry), `review_pending` →
  retryable, `invalid_input` → invalid address, unreachable → retryable, and
  any invalid payload → "could not be read safely… nothing was changed".
- `webui/src/app.ts`: the review route mounts the screen; opening the live
  attempt or the retried one goes through the explicit `openChosenAttempt`.
- `webui/tests/network_guard.mjs`: `/api/attempts/<uuid>/review` documented.
- `webui/tests/library_routes.spec.mjs`: the review-route shell assertion now
  declares the 404 the real review read returns for an unknown UUID.
- `docs/cli-contract.md`: `/history/review/{uuid}` row rewritten.

## Deliberate decisions

- Saved work of never-submitted attempts is read through the existing source
  route by explicit attempt ID and always labelled "not a submission": D002's
  three source-binding axes stay exactly as defined, and the review boundary
  keeps serving stored metadata only.
- Retry reuses the reviewed attempt's mode and drill duration; a different
  format is a new start from the library. The dialog names the mode so the
  choice is visible.
- Ending the live attempt on Retry uses the same abandon API as the attempt
  screen's End control, with the revision read immediately before.

## Negative cases proven (`webui/tests/review_screen.spec.mjs`, 5 journeys)

- Submitted attempt reviewed while another attempt is live: metadata, pinned
  version, final result, read-only source equal to the submitted bytes (typing
  into it changes nothing), no Submit/Run/Save controls, only GET requests,
  `active.json` and `review.json` byte-identical. Retry → conflict dialog;
  Cancel changes nothing and restores focus; "Resume active attempt" opens the
  live attempt with zero mutations; "End it and start a new attempt" issues
  exactly one abandon (live attempt now `abandoned`, revision advanced) and
  one start (same exercise and mode), opens the replacement, and leaves the
  reviewed record and its review bytes unchanged.
- Ended attempt: "Last practice result" from the recorded `test` run, "ended
  without a submission", no "Final result" text, saved work shown read-only
  from the source route, Retry (no live attempt) confirms with the mode and
  starts once.
- Legacy record (synthetic payload): both banners, "unavailable (legacy
  record)", `session/v1`, stored score rendered, current file labelled "not
  proven submitted" with its digest; Retry dialog announces that the version
  is not recorded and names the library version; a pinned record with a
  different version gets the "differs from" notice.
- Removed catalog version: stored metadata and result readable, Retry disabled
  with the "not installed" description; a setup-required exercise is disabled
  with the catalog's safe setup message.
- Unknown UUID → "Attempt not found" without a retry button, Back to history
  works; `review_pending` (with a path in server text) → safe retryable alert;
  a tampered payload (score as text, contradictory binding) → "could not be
  read safely… nothing was changed" with no metadata or Retry rendered; Retry
  loading after the intercept is lifted renders the real review.

## Evidence

    just check frontend                                   metadata/lockfile/license OK
    just build assets                                     rebuilt
    just build assets-check                               manifest verified
    python3 -m unittest tests.test_attempt_reviews tests.test_documentation   OK
    npx playwright test review_screen.spec.mjs --reporter=list    5 passed
    npx playwright test history_screen.spec.mjs --reporter=list   5 passed (aligned with the real review screen)
    just check browser (locked privacy reporters)         197 passed, 0 failed
    just check unit                                       455 tests OK (1 skipped)
    git diff --check                                      clean
