---
fest_type: task
fest_id: 02_review_screen.md
fest_name: review_screen
fest_parent: 02_history_and_review
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-11T14:32:19.009153-06:00
fest_updated: 2026-09-12T22:42:53.265009-06:00
fest_tracking: true
---


# Task: review_screen

## Objective

Display read-only submitted source, result summary, safe per-level outcomes, and timing/version metadata; distinguish legacy-unbound, expired, and abandoned work; implement Retry with version-change notice and live-attempt conflict resolution.

## Requirements

- [ ] Read and apply **D002_submission_review.md** (review display, legacy warnings) and **D004_history_api_and_ux.md** (review screen flows, retry behavior).
- [ ] Fetch GET `/api/attempts/{uuid}/review` only on explicit review route; render read-only editor/viewer for bound source.
- [ ] Show score summary, per-level outcomes, profile, timing, assessment version; label legacy-unbound source explicitly.
- [ ] Expired/abandoned attempts show saved work/last practice score honestly—not fabricated submission results.
- [ ] Retry uses current catalog version with visible version-change notice; live-attempt conflict routes through resume-or-abandon confirmation.
- [ ] Browser/API tests prove no old mutation/rescore, active selection unchanged, and meaningful errors for missing data.

## Implementation

1. **Review route** — `/history/review/:id` loads review payload; Back preserves history filters from task 01.
2. **Read-only source pane** — Disable editing; show digest/version footer when available.
3. **Legacy banner** — When `submitted-source binding unavailable`, show D002 label and still render stored scores.
4. **Retry action** — Start new attempt via POST start with current catalog version; if version differs from attempt metadata, show notice before confirm.
5. **Live conflict modal** — If another attempt active, present resume-or-abandon choices—no silent replacement (D004).
6. **Tests** — Browser tests reviewing old submission while different attempt active; API mocks assert no POST mutate/rescore; missing review bytes shows error state.

### Affected files

- `webui/src/app.ts` and review view module(s)
- `webui/tests/` review specs

### Negative cases to prove

- Review screen cannot edit or submit scored source.
- Retry does not change active selection until user confirms conflict resolution.
- Removed catalog version still shows stored metadata with unavailable setup message.
- Tampered/unavailable review payload surfaces error, not empty success UI.

### Commands and evidence

```bash
just check browser
```

## Done When

- [ ] All requirements met
- [ ] Review screen is read-only with honest legacy/expired/abandoned presentation and safe Retry
- [ ] Browser/API tests confirm no mutation, rescoring, or active-selection side effects
