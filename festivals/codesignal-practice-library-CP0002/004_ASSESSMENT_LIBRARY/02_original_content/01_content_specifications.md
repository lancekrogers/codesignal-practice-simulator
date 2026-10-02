---
fest_type: task
fest_id: 01_content_specifications.md
fest_name: content_specifications
fest_parent: 02_original_content
fest_order: 1
fest_status: completed
fest_autonomy: low
fest_created: 2026-09-11T14:32:19.009153-06:00
fest_updated: 2026-09-12T20:24:20.349966-06:00
fest_tracking: true
---


# Task: content_specifications

## Objective

Record the user's topic/count decision from D005, then write original exercise specifications with exact signatures, timing/ordering rules, return values, level dependencies, examples, and edge cases—without copying protected content or substituting festival IDs for exercise IDs.

## Requirements

- [ ] **Prerequisite (blocking):** Read **D005_content_scope.md** and record the user's confirmed topic/count choice in that decision record before any spec authoring. Status is currently *awaiting user preference*—do not proceed to implementation artifacts until the user response is captured in D005.
- [ ] Read and apply **D003_assessment_catalog.md** (four-level metadata, runner contract) once D005 is resolved.
- [ ] Write specification documents for each **accepted** track with stable assessment IDs distinct from festival ID `CP0002`.
- [ ] Proposed tracks (pending user confirmation): **In-Memory Records** and **Account Ledger**—each with four progressive levels, full 90-minute and drill profiles.
- [ ] Each spec must define: function/class signatures, return and error conventions, ordering guarantees, time units, level dependencies, worked examples, and deterministic correctness contracts.
- [ ] Review all four progressive levels per accepted exercise; no proprietary CodeSignal question copying.

## Implementation

1. **Stop if D005 unresolved** — If D005 still shows *awaiting user preference*, halt after documenting the blocker in sequence results; do not author prompts/starters/tests in this task.
2. **Capture user choice** — Update `002_PLAN/decisions/D005_content_scope.md` with explicit user confirmation (which tracks, count, naming). This edit is a decision-record update authorized by the prerequisite gate—not optional planning prose.
3. **Spec file layout** — Create specs under project docs or content spec directory (e.g. `docs/content/` or `content/specs/`) one file per assessment: metadata header (id, version placeholder, profiles), level sections L1–L4 with signatures and acceptance criteria.
4. **In-Memory Records draft contract** (if accepted) — Cover basic records/fields, deterministic filtering, expiry, time-consistent snapshots/restoration per D005 proposal.
5. **Account Ledger draft contract** (if accepted) — Cover accounts/transfers, aggregate rankings, scheduled operations, historical balances with explicit identity/time rules per D005 proposal.
6. **Cross-check** — Peer-review specs against D003 runner entry points (`test_simulation.TestSimulateCodingFramework.test_group_1..4` at `scoring.py:193`) before task 02 implementation.

### Affected files

- `002_PLAN/decisions/D005_content_scope.md` (user choice record—update only after user confirms)
- `docs/content/` or equivalent spec paths (new specification files per accepted track)

### Negative cases to prove

- No spec authored while D005 remains unresolved (task stays blocked with documented reason).
- Exercise IDs do not reuse `CP0002` or other festival identifiers.
- Specs contain no text reproduced from protected/vendor assessments.
- Each level lists explicit edge cases (empty input, boundary time, invalid references) not deferred to implementation.

### Commands and evidence

```bash
# Verification is documentary for this task
fest markers count 004_ASSESSMENT_LIBRARY/02_original_content/01_content_specifications.md
# After specs exist:
rg -l "CodeSignal" docs/content/  # must return no proprietary copies
```

## Done When

- [ ] All requirements met
- [ ] D005 records explicit user topic/count choice and each accepted track has a complete four-level specification
- [ ] Specs reviewed against D003 runner contract with signoff note in sequence results
- [ ] Task remains blocked with written blocker if user preference still absent
