---
fest_type: task
fest_id: 01_full_acceptance_matrix.md
fest_name: full_acceptance_matrix
fest_parent: 01_acceptance_and_distribution
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-11T14:32:19.009153-06:00
fest_updated: 2026-09-12T23:59:36.55266-06:00
fest_tracking: true
---


# Task: full_acceptance_matrix

## Objective

Run synthetic CLI/browser flows covering every accepted exercise and lifecycle outcome—including legacy review, crash/restart, cross-process races, save conflicts, stale tabs, pagination, missing content, and security rejection—using locked Playwright privacy reporters and no real candidate work.

## Requirements

- [ ] Map evidence to **R1–R11** per IMPLEMENTATION_PLAN requirement table; all decisions D001–D005 reflected in scenarios where applicable.
- [ ] Exercise each accepted original assessment through start → practice → submit/abandon/restart → history → review → retry paths.
- [ ] Include legacy v1 review/read paths, crash mid-restart journal, concurrent CLI/browser processes, save conflict, stale tab duplicate restart, history pagination with changing records, missing catalog content, symlink/unsafe ID rejection.
- [ ] Reuse existing locked Playwright privacy reporters; no real candidate/cache/reference data.
- [ ] Record matrix rows with command, environment, pass/fail, and artifact paths in sequence `results/acceptance_matrix.md`.

## Implementation

1. **Build matrix** — Table rows: requirement ID, scenario description, CLI command or browser spec name, expected observable outcome.
2. **CLI suite** — Extend the existing unittest integration harness invoking list/start/abandon/restart/submit/review/history with synthetic workspaces.
3. **Browser suite** — Extend Playwright specs for library/history/review/restart journeys including server restart mid-flow.
4. **Failure injection** — Use test hooks to interrupt WAL/journal at least once per critical boundary (reference 003 proof obligations).
5. **Security cases** — Unauthorized origin, unsafe UUID, oversize path attempts rejected with safe errors.
6. **Execute and record** — Run focused then full matrix; capture logs under `results/` without candidate content.

### Affected files

- `tests/integration/` or existing acceptance harness
- `webui/tests/` Playwright specs
- `006_RELEASE_VERIFICATION/01_acceptance_and_distribution/results/acceptance_matrix.md`

### Negative cases to prove

- Every R3/R4 scenario shows unique replacement ID and unchanged old bytes/timer.
- Every R5/R6 listing/review scenario shows no source load on list and no rescore on review.
- R9 recovery scenarios fail closed at injected boundaries without data loss.
- R10 covers keyboard/back/forward/reload for primary screens.

### Commands and evidence

```bash
just verify
just check frontend
just check browser
just build assets
just build assets-check
just check unit
```

## Done When

- [ ] All requirements met
- [ ] Acceptance matrix document lists every R1–R11 scenario with executed evidence or explicit unresolved row
- [ ] CLI and browser suites pass in worktree with privacy reporters unchanged
