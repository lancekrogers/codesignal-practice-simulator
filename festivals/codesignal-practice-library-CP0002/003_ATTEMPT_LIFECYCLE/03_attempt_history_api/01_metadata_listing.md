---
fest_type: task
fest_id: 01_metadata_listing.md
fest_name: metadata_listing
fest_parent: 03_attempt_history_api
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-11T14:32:19.009153-06:00
fest_updated: 2026-09-12T19:11:50.777846-06:00
fest_tracking: true
---


# Task: metadata_listing

## Objective

Add a proposed `attempt_history.py` reader at the application boundary enumerating validated UUID attempt directories with metadata-only bounded pagination—no source/events/prompt reads and no operational `status()`/`time()` repair-on-read.

## Requirements

- [ ] Detect incomplete restart intents through bounded metadata reads, expose
  affected rows as pending/unavailable, and never recover them on GET. Prove
  directory hashes and active selection remain unchanged by listing.

- [ ] Read and apply **D004_history_api_and_ux.md** (listing limits, cursor/filter contract) and **D002_submission_review.md** (metadata-only boundary).
- [ ] Create `src/codesignal_practice_simulator/attempt_history.py` and wire listing entry at `application.py:174` boundary without loading source.
- [ ] Enumerate validated UUID directories; bound each record read and page size (default 25, max 100); deterministic sort by creation time then UUID descending.
- [ ] Cursor encodes validated ordering boundary and filter identity; reject malformed/mismatched cursors and unknown filters.
- [ ] Skip unsafe entries (symlinks, traversal) with aggregate safe warning; represent corrupt valid-ID records as unavailable without source load.
- [ ] No retention cap, no eager source loading, no `active.json` mutation during listing.

## Implementation

1. **Reader API** — `list_attempts(filters, cursor, limit) -> {items, next_cursor, warnings}` with fields: attempt ID, status, profile, timestamps, summary score, review availability, assessment metadata/version if present, safe issue codes—never source, paths, or capability tokens.
2. **Scan strategy** — Stream directory entries; retain bounded page candidate set in memory; do not build secondary index DB.
3. **Non-repairing reads** — Use persistence readers from 003/01; do not invoke lifecycle repair or journal reconciliation on GET listing.
4. **Effective status** — Overdue active may display effective expired with persisted status documented separately (D002/D004).
5. **Tests** — Add `tests/test_attempt_history.py` for empty list, mixed v1/v2 schemas, partial corruption, symlinks, moving pages during pagination, unknown filters, and proof that source/event files are never opened (mock/spy).

### Affected files

- `src/codesignal_practice_simulator/attempt_history.py` (new)
- `src/codesignal_practice_simulator/application.py`
- `tests/test_attempt_history.py`

### Negative cases to prove

- Listing never reads `simulation.py`, review bytes, or prompt files.
- Malformed cursor → 400-class safe error, not empty misleading page.
- Concurrent new attempt during pagination → documented refresh behavior, not snapshot guarantee.
- `active.json` hash unchanged after listing calls.

### Commands and evidence

```bash
python3 -m unittest tests.test_attempt_history -v
```

## Done When

- [ ] All requirements met
- [ ] Metadata listing is bounded, deterministic, and read-only on disk
- [ ] Pagination and corruption tests pass with evidence recorded
