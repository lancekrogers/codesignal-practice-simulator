---
fest_type: task
fest_id: 04_readonly_review_service.md
fest_name: readonly_review_service
fest_parent: 01_schema_and_review
fest_order: 4
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-11T14:32:19.009153-06:00
fest_updated: 2026-09-11T16:28:04.647724-06:00
fest_tracking: true
---


# Task: readonly_review_service

## Objective

Add a proposed `attempt_reviews.py` read-only service using bounded non-repairing persistence readers that returns verified immutable review data for v2 submissions and honest legacy-unbound summaries for v1—without routing through `candidate_documents.py:52` or `workspace.py:239`.

## Requirements

- [ ] Read and apply **D002_submission_review.md** (legacy readonly reads, no side effects, digest-checked immutability) and **D001_attempt_lifecycle.md** (terminal state semantics).
- [ ] Create `src/codesignal_practice_simulator/attempt_reviews.py` as the review read boundary; do **not** reuse `candidate_documents.py:52` or `workspace.py:239` mutation/repair paths.
- [ ] Report the three D002 review axes independently (amendment 2026-09-11):
  `stored_metadata` (always from the session: assessment id/name/levels, profile,
  status, timestamps, score); `content_identity` (`pinned` with version/digest for
  v2, `unavailable` for v1; never looked up from the current registry); and
  `source_binding` (`captured` when a verified `review.json` exists, `not_captured`
  otherwise, `not_applicable` before any submission).
- [ ] Submitted records with a verified review member return its immutable source bytes, score summary, per-level outcomes and timing (v2 attempts and v1 attempts submitted by this release).
- [ ] Legacy submissions without a review member return stored score/timestamps with explicit “submitted-source binding unavailable”. The current `simulation.py` may be offered only as separately labeled legacy source, bounded and read without baseline creation; it is never presented as the submitted bytes.
- [ ] Enforce byte limits, symlink/traversal rejection, and record/directory identity match; changing records return retryable unavailability.
- [ ] Tests prove unchanged directory hashes after review GET, removed assessment handling, malformed IDs, oversized files, and symlink rejection.

## Implementation

1. **Service API** — Define `get_review(attempt_id) -> ReviewResponse` with the three axes as typed fields, issue codes, legacy warnings, and a source payload only when digest-verified (or explicitly labeled legacy source).
2. **Readers** — Use persistence helpers from task 01 with non-repairing, bounded reads; never touch `active.json`, journals, or source-history initialization on GET.
3. **Legacy path** — Load v1 state directly; surface unavailable fields honestly (not zero/failed placeholders); label unbound source explicitly per D002.
4. **Integrity** — Verify the review member against the submitted state (v2 `review_digest`; v1 attempt_id/revision/submitted_at/score); reject mixed generations; tampered bytes → corruption error. A pending submission WAL means retryable unavailability, not repair on GET.
5. **Tests** — Add `tests/test_attempt_reviews.py` with directory hash snapshots before/after review calls, removed catalog fixture, bad UUID, oversize review file, symlink attempt directory, and concurrent active attempt unchanged.

### Affected files

- `src/codesignal_practice_simulator/attempt_reviews.py` (new)
- `tests/test_attempt_reviews.py`

### Negative cases to prove

- Review GET never mutates disk (hash unchanged).
- No rescore calls during review (mock scorer unused).
- Missing legacy source → summary only with explicit unbound label.
- Invalid/symlink/oversized paths → safe errors without path leakage.

### Commands and evidence

```bash
python3 -m unittest tests.test_attempt_reviews -v
```

## Done When

- [ ] All requirements met
- [ ] Review service returns immutable v2 data and honest legacy fallbacks with no disk side effects
- [ ] Hash-unchanged and negative-path tests pass with evidence recorded
