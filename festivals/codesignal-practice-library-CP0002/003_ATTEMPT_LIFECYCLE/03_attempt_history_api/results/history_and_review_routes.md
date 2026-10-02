# History, review and action routes (web API + CLI parity)

Implemented by the coordinator directly on 2026-09-12 in the linked
cp0002-practice-library worktree. Uncommitted pending 06_fest_commit.

## What changed

- `web/routes.py`
  - `GET /api/attempts` → `_list_attempts`: allowed query keys `status`,
    `assessment_id`, `cursor`, `limit` (decimal). Unknown/empty keys and a
    non-decimal limit are 400 `invalid_query` (existing convention); the
    listing service's own `InvalidInputError`s (malformed cursor, cursor for
    other filters, unknown status, limit out of range) become 422
    `invalid_input` carrying the same safe message the CLI prints.
  - `/api/attempts/{uuid}/(review|abandon|restart)` → `_attempt_action`: the
    path must have exactly five segments and a known action (else 404); the
    UUID is canonicalized before anything touches the filesystem (422).
    `review` is GET with optional `include_source=true|false`; `abandon` and
    `restart` are POST with the existing Origin, JSON-body and exact-field
    discipline, and body validation for `expected_revision`, `operation_id`,
    `mode`, `drill_duration_seconds`. Restart answers 201 for a fresh
    operation and 200 with `replayed: true` for an identical repeat.
  - `_domain_failure`: specific codes map first: `stale_revision` and
    `operation_conflict` → 409, `recovery_pending` and `review_pending` → 503,
    each with the domain message. `LiveSelectionError` deliberately keeps the
    existing 423 `lifecycle_locked` contract the browser already handles.
- `application.py`: `self.reviews = AttemptReviewService(...)` and
  `review(attempt_id, include_source)`; `list_attempts` from task 01.
- `cli.py`: `history [--status] [--assessment] [--cursor] [--limit]` and
  `review --attempt UUID [--no-source]` (review refuses to resolve the active
  pointer: explicit by design). Results serialize through `to_dict`.
- `workspace.RestartResult.to_dict()` is now the one transport document for
  restart, shared by the CLI envelope and the web route.
- `errors.ReviewPendingError.code = "review_pending"`.
- `docs/cli-contract.md`: command tree, `history`/`review` semantics, and a
  "History, review and action routes (web API)" table with error mapping.

## Deliberate decisions

- Listing/cursor validation errors carry their message across HTTP because
  those messages are safe domain text with no paths, and the task requires the
  HTTP and CLI shapes to agree. Other `InvalidInputError`s keep the generic
  web message as before.
- Live selection stays 423 rather than 409: the accepted browser journeys and
  the D004 "resume-or-abandon confirmation" flow already key on
  `lifecycle_locked`; changing it would be a UI contract change for no gain.
  Stale revision and operation conflict are new and get 409 per D004.
- A decoded traversal in the ID segment produces extra path segments and is a
  404 before any ID is examined; a syntactically bad UUID is 422. Both happen
  before filesystem access.

## Negative cases proven (tests/test_history_review_routes.py, 7 tests)

- Listing: pages via `cursor`, status filter, `review_available`, no source
  content or path in any item; tree, pointer and scorer-call count unchanged.
- Bad queries: unknown filter, empty value, non-decimal limit → 400; limit
  101/0, unknown status, bad cursor → 422 with the exact CLI message; plain
  start while live → 423.
- Review of a submitted attempt while another is live: verified source and
  score returned; `include_source=false` omits source; unsubmitted attempt is
  `not_applicable`; tree, pointer, selection and scorer count unchanged.
- Unsafe IDs (non-UUID, uppercase, traversal), unknown action, extra segment,
  unknown attempt, bad `include_source`, wrong method → safe envelopes, no path
  leak, tree unchanged.
- Unauthorized: missing/wrong token → 401 on GET routes; missing/foreign Origin
  → 403 on both POST actions; nothing changed, no attempt ID echoed.
- Actions: stale revision 409 with message; four invalid abandon bodies → 422;
  abandon then idempotent repeat; restart 201 with drill replacement and
  pointer moved; identical repeat 200 `replayed`; changed arguments 409
  `operation_conflict`; terminal attempt 423; five invalid restart bodies → 422;
  exactly three attempt directories at the end.
- CLI parity: `history` pagination and filters, `review` with and without
  source, `review` without `--attempt` exit 2, bad cursor exit 2 with the same
  message as HTTP, unknown status exit 2; tree and pointer unchanged.

## Evidence

    python3 -m unittest tests.test_history_review_routes   7 tests OK
    just check unit                                        424 tests OK (1 skipped)
    python3 -m unittest tests.test_documentation           OK
    just check frontend                                    passed
    just check browser                                     175 passed
    git diff --check                                       clean

## Follow-ups

- 005 UI consumes `GET /api/attempts`, the review route and the two actions;
  the restart confirmation must mint and reuse `operation_id`.
- Server startup should call `WorkspaceManager.recover_restarts()` (carried).
