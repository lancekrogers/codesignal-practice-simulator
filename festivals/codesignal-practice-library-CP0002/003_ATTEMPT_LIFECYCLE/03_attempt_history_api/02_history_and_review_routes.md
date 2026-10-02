---
fest_type: task
fest_id: 02_history_and_review_routes.md
fest_name: history_and_review_routes
fest_parent: 03_attempt_history_api
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-11T14:32:19.009153-06:00
fest_updated: 2026-09-12T19:24:38.909543-06:00
fest_tracking: true
---


# Task: history_and_review_routes

## Objective

Extend web routes and CLI commands so GET lists attempts metadata, POST still starts attempts, and explicit UUID review uses 003/01 review service—without active-pointer mutation, rescoring, or unsafe ID acceptance.

## Requirements

- [ ] Read and apply **D004_history_api_and_ux.md** (route set, error envelopes) and **D002_submission_review.md** (explicit review by UUID).
- [ ] Extend `src/codesignal_practice_simulator/web/routes.py` near `:120`, `:177`, and `:208` for GET `/api/attempts`, GET `/api/attempts/{uuid}/review`, and POST abandon/restart actions aligned with task 02/02.
- [ ] Wire review route to `attempt_reviews.py` from 003/01/04; wire listing to `attempt_history.py` from 003/03/01.
- [ ] Preserve existing capability/origin/query/error conventions; POST start unchanged except live-selection policy from D001.
- [ ] Document response fields and legacy warnings in `docs/cli-contract.md` or owning API docs.
- [ ] Test no active-pointer mutation, no rescore, invalid cursors, unsafe IDs, authorization failures, and safe error bodies.

## Implementation

1. **GET /api/attempts** — Delegate to application listing service; validate query params (filters, cursor, limit caps).
2. **GET /api/attempts/{uuid}/review** — Validate UUID; call review service; return immutable payload or legacy warnings; 404/503 distinctions for missing vs unavailable vs corrupt.
3. **POST actions** — Abandon/restart handlers share application services; include operation UUID and expected revision validation.
4. **CLI parity** — Equivalent list/review/abandon/restart commands call the same application methods.
5. **Docs** — Update API/CLI contract tables with field definitions, legacy warning strings, and cursor format.
6. **Tests** — Add route/integration tests proving directory hash unchanged, scorer not called on review GET, and active selection unchanged when reviewing old attempt while another is live.

### Affected files

- `src/codesignal_practice_simulator/web/routes.py`
- `src/codesignal_practice_simulator/application.py`
- `docs/cli-contract.md` (or equivalent API doc)
- CLI command module(s)
- `tests/test_history_review_routes.py`

### Negative cases to prove

- Unsafe ID/path patterns rejected before filesystem access.
- Unauthorized origin/capability → existing envelope, no data leak.
- Review of submitted attempt while different attempt active → both deadlines/selection unchanged.
- Invalid cursor on HTTP and CLI → same error class/message shape.

### Commands and evidence

```bash
python3 -m unittest tests.test_history_review_routes -v
```

## Done When

- [ ] All requirements met
- [ ] HTTP and CLI expose listing/review/actions with documented contracts and no side effects on read paths
- [ ] Integration tests pass with hash-unchanged and no-rescore evidence
