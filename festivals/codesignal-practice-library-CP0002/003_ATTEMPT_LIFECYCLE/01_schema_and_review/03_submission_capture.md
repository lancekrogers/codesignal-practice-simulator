---
fest_type: task
fest_id: 03_submission_capture.md
fest_name: submission_capture
fest_parent: 01_schema_and_review
fest_order: 3
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-11T14:32:19.009153-06:00
fest_updated: 2026-09-11T16:21:51.086312-06:00
fest_tracking: true
---


# Task: submission_capture

## Objective

Bind explicit attempt identity, saved revision, and exact scored bytes through the cross-process lock, extending the submission WAL with immutable review bytes/digests so recovery replays the recorded outcome without another scorer call.

## Prerequisite

02_creation_identity must be complete: new attempts are session/v2 with verified
pinned identity, every lifecycle path handles v1 and v2, and submission-recovery/v2
exists without a review member. Do not start this task on v1-only creation.

## Requirements

- [ ] Read and apply **D002_submission_review.md** including its 2026-09-11 amendment (identity and source-binding axes, legacy rules) and **D001_attempt_lifecycle.md** (attempt lock ordering).
- [ ] Extend `lifecycle.py` submit (revalidate; ~`:240`) and `_persist_submission_locked` (~`:315`) to capture the exact source bytes, score them and verify them unchanged under one attempt lock.
- [ ] Extend `application.py` `_submit_locked` (~`:371`) and `_save_before_evaluation` (~`:418`) to enforce the payload contract below instead of silently ignoring a source payload after expiry.
- [ ] Extend the ReviewRecord model and submission WAL with the immutable review member; recovery publishes exactly the recorded review, state and event and never calls the scorer.
- [ ] Record the three independent review axes (stored metadata, content identity, source binding); a v1 attempt submitted by this release gets captured bytes with content identity `unavailable`.
- [ ] Test save/submit races, duplicate submission, each durable write failure, missing/different/oversized review bytes, v1 and v2 attempts, and unchanged results after recovery.

## Contract

- **Review member** — `review.json` in the attempt directory, published once and never rewritten. Fields: schema_version `review/v1`; attempt_id; state_revision; `assessment` (v2: PinnedAssessment; v1: legacy AssessmentMetadata); `content_identity` (`pinned` or `unavailable`, matching the session schema, never inferred from the current registry); profile; started_at, deadline_at, submitted_at; score; `source` {filename `simulation.py`, sha256, content} or null. Enforce a byte limit sized for 256 KiB source after JSON escaping. The existing digest-only model from 003/01/01 changes to carry the source member; update its tests.
- **Unreadable source** — a missing, unsafe, oversized or non-UTF-8 source at submission must not block finalization (the deadline is authoritative). Capture then records `source: null`, and the review service reports that submission as not captured. Absence is not a hash mismatch.
- **State binding** — v2 submitted state carries `review_digest` (SHA-256 of the canonical review bytes); v1 state cannot change schema, so the review must match attempt_id, state_revision, submitted_at and score exactly. Any mismatch is corruption, never a reason to regenerate.
- **WAL** — `submission-recovery/v2` (v2 sessions) and a review-carrying variant for v1 sessions record prior_state, state, event and the complete review bytes. The publication order is review member, then state, then event. Recovery accepts an already-published review only if its bytes are identical. A pre-existing `submission-recovery/v1` file with no review still replays exactly as before, and its attempt stays `source binding: not captured`.
- **Scored bytes** — Under the attempt lock, read `simulation.py` bytes and digest them, run the scorer, then re-read them. If they differ, the edit raced the scoring run: commit nothing and raise a retryable conflict. CLI users edit the file directly, so this check is needed on top of browser ETags.
- **Payload rules** (revised 2026-09-11 against D002 and the accepted browser
  journeys, which already pin repeat-submit behavior) — active + payload: save
  with If-Match, then capture that revision. Expired or abandoned + a payload
  that would change the saved source: terminal/read-only error, nothing written
  and no finalization. Expired or abandoned + a payload identical to the saved
  source: not a mutation, so it is ignored and an expired submit still finalizes
  the saved revision once. Submitted: always return the committed result without
  saving or rescoring, whatever the payload. This closes the silent-drop
  ambiguity at `application.py:418` (a *changed* payload can no longer be
  ignored) while keeping `accepted_journeys` and `browser_continuity` valid.
  Document the change to the API/CLI contract.

## Implementation

1. **Revalidate anchors** — Re-confirm the submit and persistence anchors after 02_creation_identity lands; inspect `application.py` `_save_before_evaluation` for the expired payload early return.
2. **Models** — Extend ReviewRecord and SessionStateV2 (`review_digest` for submitted status only) per the contract; keep the v1 session schema byte-compatible.
3. **Capture** — Implement the scored-bytes sequence in lifecycle submit; build the review from the post-verification bytes and the exact score object persisted in state.
4. **WAL and recovery** — Extend persistence WAL writers and `recover_submission_locked` with the review member, byte-identity checks and bounded, symlink-rejecting reads.
5. **Transports** — Apply payload rules in the application layer so CLI and web share them; web submit/test routes map the new errors with existing conventions.
6. **Tests** — Add `tests/test_submission_capture.py` with scorer spies. Cover concurrent save/submit, duplicate submits with same/different/no payload, a source change during scoring, failure injection before and after each review/state/event/unlink/flush boundary, a tampered or oversized review member, v1 WAL replay without a review, v1 and v2 attempts, and repeated recovery with no further writes.

### Affected files

- `src/codesignal_practice_simulator/models.py` (ReviewRecord, SessionStateV2 review_digest, SubmissionRecovery)
- `src/codesignal_practice_simulator/persistence.py` (WAL, review member publication/verification)
- `src/codesignal_practice_simulator/lifecycle.py`
- `src/codesignal_practice_simulator/application.py`, `web/routes.py` error mapping if needed
- `tests/test_submission_capture.py`, `tests/test_attempt_models_v2.py`

### Negative cases to prove

- Expired submit with new source payload → terminal/read-only error (not silent ignore).
- Duplicate submitted request → same committed result, no rescoring.
- Recovery with mismatched review bytes or digest → fail closed, no regenerated score.
- Save/submit race loser → stale-state conflict, not double commit.
- Source changed during scoring → retryable conflict, nothing committed.
- v1 attempt review never claims pinned content identity.

### Commands and evidence

```bash
python3 -m unittest tests.test_submission_capture -v
just check unit
```

## Done When

- [ ] All requirements met
- [ ] Submission WAL recovery reproduces exact review bytes and summary without scorer calls
- [ ] Race, duplicate, and failure-injection tests pass with captured output in sequence results
