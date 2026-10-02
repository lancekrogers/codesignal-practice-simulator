# Sequence testing gate — 005/02_history_and_review

Covers 01_history_screen and 02_review_screen. Per-task evidence, negative
cases and deliberate decisions are in the sibling results files.

## Commands run and results (final code, 2026-09-12)

    just check frontend                                        passed
    just build assets                                          rebuilt bundle (esbuild)
    just build assets-check                                    manifest hash verified
    python3 -m unittest tests.test_attempt_reviews             16 tests, OK (practice_score test new)
    python3 -m unittest tests.test_history_review_routes tests.test_documentation   OK
    just check unit                                            455 tests, OK (1 skipped)
    npx playwright test history_screen.spec.mjs --reporter=list     5 passed
    npx playwright test review_screen.spec.mjs --reporter=list      5 passed
    just check browser (locked privacy reporters)              197 passed, 0 failed
    git diff --check                                           clean

An earlier full run during 01_history_screen failed once on shell_lifecycle
"coalesces duplicate live announcements and disposes pending frames" (a
pre-existing live-region timing test); it passes alone and in the two full runs
since. No code change was made for it.

## Acceptance criteria demonstrated

- **Metadata-only history** (`history_screen.spec.mjs`): the history screen
  requests only `GET /api/bootstrap` and `GET /api/attempts?…`; never source,
  review or a mutation. Filters (exercise, status), rows per page and the
  cursor live in the fragment; newest-first pages walk with Newest/Older and
  the D004 refresh note; a dataset that grows while browsing appears on Newest.
- **Navigation state preserved**: Review keeps the fragment, Back to history
  and browser back restore filters and page; opening a review leaves
  `attempts/active.json` byte-identical.
- **Partial errors**: skipped unsafe entries are counted in a banner; a corrupt
  record is a visible Unavailable row with its issue code and a disabled Review;
  malformed fragment values fall back with notices; a server-rejected cursor
  and an unreadable attempts folder show safe, actionable errors.
- **Read-only review** (`review_screen.spec.mjs`): stored metadata, pinned
  version or legacy label, "Final result" only for submissions, "Last practice
  result" for ended/expired attempts, source with its binding named and a
  read-only viewer that ignores typing; only GET requests; `review.json` and
  the active pointer unchanged.
- **Honest legacy presentation**: `submitted_source_binding_unavailable` and
  content-identity banners, "Current file (not proven submitted)" with digest.
- **Safe Retry**: disabled with the reason when the exercise is not installed
  or needs setup; the confirmation names mode and exercise and announces a
  content-version difference; with a live attempt the choice is Resume / End
  and start / Cancel, and "End and start" issues exactly one abandon and one
  start; no rescoring, no old-attempt mutation.
- **Errors, not empty success**: unknown UUID, `review_pending`, and a tampered
  payload each render an error state with no metadata and no Retry; retrying
  after the fault clears renders the real review.

## Failure boundaries exercised

- History: 404 `history_unavailable` with a path in server text; 422 for a
  rejected cursor; fragment values with illegal shapes; symlinked and non-UUID
  entries; unparsable `session.json`.
- Review: 404 unknown attempt; 503 `review_pending` with a path; payload with
  a non-object score and a `captured` source under a `not_applicable` binding;
  catalog without the reviewed exercise; catalog entry marked setup-required;
  legacy record without identity or binding.
- Server: an ended attempt's review carries `practice_score` and no `score`;
  a submitted review never carries `practice_score`
  (`tests.test_attempt_reviews`).

## Not run here, with reasons

- `just check wheel` and the `just verify` fixture-cache scope: unchanged
  prerequisites gaps (no packaging interpreter; no fetched cache; network
  fetch not authorized). Owned by 006/01.
- TypeScript type checking: no `tsc` in the locked toolchain; the esbuild
  bundle and the browser journeys are the verification.
