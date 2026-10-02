# Sequence testing gate — 003/03_attempt_history_api

Covers 01_metadata_listing and 02_history_and_review_routes. Per-task evidence
and mutation checks are in the sibling results files.

## Commands run and results (final code, 2026-09-12)

    python3 -m unittest tests.test_attempt_history            11 tests, OK
    python3 -m unittest tests.test_history_review_routes      7 tests, OK
    just check unit                                           424 tests, OK (1 skipped)
    just check browser                                        175 passed, 0 failed
    just check frontend                                       passed
    python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope tracked        passed
    python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary   passed
    python3 -m unittest tests.test_documentation              OK
    git diff --check                                          clean

The browser suite ran alone after the unit suite (sequentially, same command),
so no load-related flakiness appeared this time. All tests use synthetic
first-party workspaces; no real attempt data was read.

## Read-only proof

- Listing: a read-spy filesystem records every `read_bytes`/`read_bytes_limited`
  call; assertions require no reads of `simulation.py`, `review.json`,
  `events.jsonl`, `test_simulation.py` or any `level*.md`, and whole-tree
  snapshots plus `active.json` bytes are unchanged across listing calls,
  including with a pending restart journal present (recovery is not run).
- Review route: tree snapshot, active pointer, bootstrap-reported selection and
  scorer-call count are unchanged when a submitted attempt is reviewed while a
  different attempt is live.

## Failure and boundary cases exercised

Pagination (three pages, creation-time tie broken by UUID, cursor replay,
records added and removed between pages), cursor issued for other filters,
five malformed cursors, five bad limits, unknown filter key, unknown status,
malformed assessment id; corrupt session, missing session, wrong record
identity, symlinked and non-UUID entries, staging directory and stray file;
pending restart journal (rows flagged, byte-identical repeat, normal after
`recover_restarts()`), unreadable journal (aggregate warning), pending
finalization markers, symlinked or file `attempts` directory. HTTP: bad
queries at 400 and 422 with the CLI's message, unsafe IDs and unknown actions
before filesystem access, 401/403 with nothing changed or echoed, stale
revision 409, operation conflict 409, terminal 423, nine invalid action bodies
at 422, restart 201 then replay 200. CLI: `history` pagination/filters,
`review` with and without source, missing `--attempt`, bad cursor with the same
message as HTTP.

Mutation checks: pending rows forced `available` fail two listing tests;
disabling the cursor boundary fails three (the pagination test is bounded so a
non-advancing cursor fails rather than loops).

## Not run here, with reasons

- `just verify` stops at the fixture-cache scope (no fetched cache; fetching
  third-party content over the network is not authorized). Its other two
  scopes passed and `just check unit` runs the same test suite.
- `just check wheel`: no interpreter with packaging prerequisites (006 owns it).
- `just build assets` / `assets-check`: no frontend source changed.
