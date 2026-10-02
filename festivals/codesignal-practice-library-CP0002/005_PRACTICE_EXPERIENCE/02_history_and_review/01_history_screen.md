---
fest_type: task
fest_id: 01_history_screen.md
fest_name: history_screen
fest_parent: 02_history_and_review
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-11T14:32:19.009153-06:00
fest_updated: 2026-09-12T22:24:54.506352-06:00
fest_tracking: true
---


# Task: history_screen

## Objective

Implement assessment/status filters, bounded pagination, per-entry availability indicators, and safe partial-error display using 003/03 APIs while preserving filter/position through review/back navigation.

## Requirements

- [ ] Read and apply **D004_history_api_and_ux.md** (history screen, filters, pagination, no active selection change).
- [ ] Consume GET `/api/attempts` listing from 003/03/02 without requesting source or review payloads in list view.
- [ ] Provide assessment and status filters, cursor pagination (default 25, max 100), newest-first rows with resume/review actions.
- [ ] Display per-entry review availability and aggregate warnings for skipped unsafe/corrupt entries.
- [ ] Preserve filter state and scroll/page cursor when navigating to review and back.
- [ ] Test empty and growing collections, retries, keyboard navigation, and network failure recovery.

## Implementation

1. **History route** — Build `/history` view fetching listing with query-assembled filters and cursor.
2. **Filter controls** — Bind assessment id and status enums to API-supported filters; reset cursor on filter change.
3. **Row actions** — Resume (if active policy allows) and Review navigate without setting reviewed attempt as active.
4. **Partial errors** — Show banner for aggregate warnings; per-row unavailable badge with issue code tooltip/text.
5. **Back stack** — Serialize filter+cursor in session or URL query (no source); restore on return from review.
6. **Tests** — Browser tests for empty list, multi-page walk, filter change, corrupt entry warning display, keyboard focus order.

### Affected files

- `webui/src/app.ts` and history view module(s)
- `webui/tests/` history specs

### Negative cases to prove

- Listing network calls never include review/source endpoints.
- Malformed cursor from manual URL edit shows recovery UI, not crash.
- Opening review does not mutate active attempt selection (API spy or server-side hash check).
- Growing dataset while paginating shows refresh guidance per D004.

### Commands and evidence

```bash
just check browser
```

## Done When

- [ ] All requirements met
- [ ] History screen paginates and filters with metadata-only API usage and preserved navigation state
- [ ] Browser tests pass including keyboard navigation and partial-error display
