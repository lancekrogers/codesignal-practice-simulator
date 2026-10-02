---
fest_type: festival
fest_id: CP0002
fest_name: codesignal-practice-library
fest_status: completed
fest_created: 2026-09-11T13:06:52.928551-06:00
fest_updated: 2026-09-18T21:34:53.663733-06:00
fest_tracking: true
---




# CodeSignal Practice Library

Build a repeatable local practice product: multiple assessments, unlimited fresh
attempts, safe abandon/restart, and review of previous submissions.

## Success criteria

- [ ] Multiple distinct Python assessments with progressive levels are selectable.
- [ ] Restart creates a new attempt/deadline and preserves the previous attempt.
- [ ] History discovers attempts independently of the active pointer.
- [ ] Review displays saved submission source, score, per-level results, and timing.
- [ ] Existing attempts survive compatibility changes without destructive migration.
- [ ] Shared CLI/browser rules recover duplicate requests and interrupted writes.
- [ ] Synthetic tests prove select → practice → submit → review → retry.

## Phase progress

- [x] 001_INGEST: audit and requirements acceptance through configured local judges.
- [x] 002_PLAN: lifecycle/catalog/review design and executable tasks, gates passed.
- [ ] 003–006: implementation and acceptance verification.
- [ ] 007: independent release review and publication.

Complete only when the product flows and release checks pass with recorded
evidence. Festival creation or structural validation is not feature completion.
