# Iteration on review findings — 003/03_attempt_history_api

All three accepted findings from results/review.md are done; the nits that
called for a change (docs cross-reference) are done too.

## F1 — listing failures name the listing

`RouteHandler._list_attempts` maps `SessionUnavailableError` (an unsafe or
unreadable `attempts/` directory) to 404 `history_unavailable`, "attempt
history is unavailable", instead of the single-attempt message. Documented in
the `GET /api/attempts` row. Test: the new route test symlinks `attempts/`
and asserts the code and that no path appears in the body.

## F2 — 503 mapping exercised end to end

New test `test_pending_states_are_503_over_http_and_retry_replays`: a pending
finalization marker makes `GET .../review` answer 503 `review_pending`; an
injected pointer failure makes `POST .../restart` answer 503 `recovery_pending`
naming the operation ID, and the same operation ID then replays with 200 and
the pointer on the replacement.

## F3 — filters versus pending-restart rows

`test_pending_restart_rows_are_reported_and_never_recovered_by_listing` now
applies a status filter while the journal is pending and asserts both pending
rows are hidden and counted in `unavailable_records_excluded_by_filter`, with
the tree still unchanged.

## Verification after iteration

    python3 -m unittest tests.test_history_review_routes tests.test_attempt_history   19 tests, OK
    just check unit                                                                  425 tests, OK (1 skipped)
    python3 -m unittest tests.test_documentation                                     OK
    git diff --check                                                                 clean

Browser and frontend suites were not rerun: no browser asset or frontend file
changed in this iteration (a route error mapping, docs and tests).
