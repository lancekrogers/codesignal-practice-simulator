# Sequence code review — 003/03_attempt_history_api

## Scope and reviewers

- Delegated reviewer: Cursor `claude-sonnet-5-thinking-high`, read-only plan
  mode, bounded to the uncommitted diff, the two new test modules and
  `docs/cli-contract.md`. It ran the focused modules (18 OK) and the full suite
  (424 OK, 1 skipped) itself. Transcript kept in the session scratchpad.
- Coordinator review: independent re-read of the route dispatch (ID validation
  order, Origin/body discipline, status mapping) and the listing scan.

A reviewer verdict is not runtime verification; evidence is in results/testing.md.

## Findings and dispositions

**Blocking:** none from either reviewer. No read path writes, locks, repairs,
creates baselines or touches `active.json`; no listing path opens source,
review, event or prompt files; memory is bounded; no cursor forgery or filter
bypass; IDs are validated before filesystem access; no path/token/source leak.

**F1 — non-blocking (reviewer). Unsafe `attempts/` gave the wrong message.**
`SessionCorruptError("attempts directory is unsafe")` from the listing fell
through to the generic 404 "selected session is unavailable". ACCEPTED in
05_iterate: `_list_attempts` maps it to 404 `history_unavailable` with a
listing-specific safe message; documented and tested.

**F2 — non-blocking (reviewer). 503 mapping not exercised end to end.**
`recovery_pending` and `review_pending` were proven only by code inspection
over HTTP. ACCEPTED in 05_iterate: a new route test drives a pending
finalization marker through `GET .../review` (503 `review_pending`) and an
injected pointer failure through `POST .../restart` (503 `recovery_pending`,
then the same operation ID replays with 200).

**F3 — non-blocking (reviewer). Filter interaction with `restart_pending` rows
untested.** ACCEPTED in 05_iterate: the pending-restart listing test now
applies a status filter and asserts both pending rows are hidden and counted.

**F4 — nits (reviewer).** `history_document` naming coincidence (pre-existing
source-history endpoint; left alone); review row in the docs now cross-
references the 404 for an unknown attempt; per-page cost is linear in the
attempt count by design (D004: metadata scan, no index, no cap) and is noted.

## Areas the reviewer checked and found clean

Read-only discipline (spy filesystem, tree snapshots, pointer unchanged);
forbidden reads never opened; bounded memory via `heapq.nlargest(page + 1)`;
cursor validation (schema, exact keys, canonical UUID, aware timestamp,
filters fingerprint); deterministic total order with no skips or duplicates;
unsafe entries counted, corrupt records unavailable, unreadable journals a
warning; route ID handling before filesystem access; no information leakage;
HTTP status/code mapping consistent with the docs, 423 preserved for live and
terminal lifecycle errors; D002 compliance of the review read.
