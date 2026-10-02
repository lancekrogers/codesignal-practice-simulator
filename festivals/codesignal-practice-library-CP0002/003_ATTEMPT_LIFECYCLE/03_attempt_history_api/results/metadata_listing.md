# Metadata listing (attempt_history.py)

Implemented by the coordinator directly on 2026-09-12 in the linked
cp0002-practice-library worktree. Uncommitted pending this sequence's
06_fest_commit gate.

## What changed

- `src/codesignal_practice_simulator/attempt_history.py` (new):
  `AttemptHistoryService.list_attempts(filters, cursor, limit) -> HistoryPage`.
  - Streams `attempts/` entries; dot-prefixed machinery and stray files are
    ignored, symlinked or non-UUID directories are counted in the aggregate
    `unsafe_entries_skipped` warning.
  - Per row it reads only the bounded `session.json` through
    `Persistence.read_session`, checks the two pending-marker paths and the
    `review.json` path for presence (never content), and reads nothing else.
  - Pending restart intents are detected by reading (not recovering) the
    journals in `attempts/.restart-journal/`; the old and replacement rows they
    name are shown with their current metadata but `available: false` and
    `restart_pending`. Pending finalization markers give `finalization_pending`.
    An unreadable journal is the aggregate `restart_journals_unreadable`.
  - Effective status: an overdue active record displays `expired` while
    `persisted_status` stays `active`; nothing is written.
  - Ordering: creation time then UUID, both descending. Undated rows
    (`record_unavailable`, `record_corrupt`) sort last.
  - Pagination: `heapq.nlargest(limit + 1)` keeps at most one page plus a
    witness in memory; default 25, max 100. `HistoryCursor` is base64url JSON
    (`history-cursor/v1`) carrying the boundary and the filters' SHA-256
    fingerprint; malformed or mismatched cursors and unknown filters are
    `InvalidInputError` (exit 2), never an empty misleading page.
  - Filters: `assessment_id`, effective `status`. Unavailable rows are hidden
    by an active filter and counted in `unavailable_records_excluded_by_filter`.
  - Rows carry attempt ID, schema version, both statuses, assessment metadata
    with content identity/version/digest when pinned, profile, timestamps,
    `ended_at`, revision, summary `score` and `practice_score`,
    `review_available`, safe issue codes. Never source, paths or tokens.
- `application.py`: `self.history` service at the composition boundary and
  `list_attempts(...)` under the action lock; the registry is never consulted.
- `docs/cli-contract.md`: new "Attempt history listing" section.

## Deliberate decisions

- The journal read for pending detection uses the same checksummed parser as
  recovery, so a tampered journal is reported as a warning rather than trusted;
  the listing cannot name the affected rows in that case and says so.
- A pending row keeps its metadata visible (status, timestamps) because that
  is honest stored state; `available: false` tells the UI not to offer actions
  on it until a lifecycle command completes the operation.
- Effective status is computed from the injected clock so the CLI, web and
  tests agree; the listing never persists the expiry it displays.

## Negative cases proven (tests/test_attempt_history.py, 11 tests)

- Missing/empty directory lists nothing and creates nothing.
- Mixed v1/v2 records (legacy, submitted with review, abandoned by restart,
  overdue active): field-level assertions, ordering, effective vs persisted
  status, no forbidden reads (read-spy filesystem), pointer and tree unchanged.
- Pagination: three pages over ten records with a tie on creation time,
  cursor replay determinism, cursor issued for other filters, five malformed
  cursors, five bad limits, unknown filter key, unknown status, malformed
  assessment id.
- Records created or removed between pages: refresh semantics, no exception.
- Filters by assessment and effective status.
- Corrupt session, missing session, wrong record identity → unavailable rows
  sorted last; symlink and non-UUID entries → warning; staging dir and stray
  file ignored; filter hides unavailable rows with a count.
- Pending restart (journal left by an injected pointer failure): rows flagged,
  listing twice is byte-identical and recovers nothing; `recover_restarts()`
  then normalizes the rows.
- Unreadable journal → aggregate warning only; pending finalization markers →
  unavailable rows; symlinked or file `attempts` → `SessionCorruptError`.
- Application boundary: listing after abandon/start, cursor round trip, JSON
  serializable page, active selection unchanged.

Mutation checks: making pending rows `available` fails two tests; disabling the
cursor boundary fails three (the pagination test is bounded so a non-advancing
cursor fails instead of looping).

## Evidence

    python3 -m unittest tests.test_attempt_history   11 tests OK
    just check unit                                  417 tests OK (1 skipped)
    python3 -m unittest tests.test_documentation     OK
    git diff --check                                 clean

Browser and frontend suites unchanged by this task (no web or frontend file
touched); they run at the sequence testing gate.

## Follow-ups

- 003/03/02 exposes this through `GET /api/attempts` and a CLI `history`
  command, and maps `InvalidInputError` from cursors/filters to 400-class
  responses.
