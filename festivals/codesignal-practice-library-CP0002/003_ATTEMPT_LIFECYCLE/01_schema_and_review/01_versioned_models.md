---
fest_type: task
fest_id: 01_versioned_models.md
fest_name: versioned_models
fest_parent: 01_schema_and_review
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-11T14:32:19.009153-06:00
fest_updated: 2026-09-11T14:44:55.635837-06:00
fest_tracking: true
---


# Task: versioned_models

## Objective

Extend attempt/event/review persistence with strict session/v2 and event/v2 models, v1 adapters, explicit abandonment and content-identity fields, and safe unknown-version rejection without read-triggered upgrades.

## Requirements

- [ ] Read and apply **D001_attempt_lifecycle.md** (versioned attempts, abandoned state, content identity) and **D002_submission_review.md** (review record shape, legacy read boundary).
- [ ] Extend `src/codesignal_practice_simulator/models.py` near `:338` (attempt/session records) and `:521` (events/review-related records) with session/v2 and event/v2 types plus strict v1 adapters that normalize legacy records in memory only.
- [ ] Extend `src/codesignal_practice_simulator/persistence.py` near `:86` (read/validate paths) and `:172` (write/serialize paths) to dispatch on `schema_version`, reject unknown versions with safe issue codes before mutation, and never upgrade records on read.
- [ ] Add explicit abandonment metadata (`ended_at`, `reason`, practice-score labeling) and pinned assessment/content identity on new records per D001/D003 contracts.
- [ ] Preserve already-valid v1 records in memory; malformed or unknown-version inputs fail closed with deterministic domain errors.
- [ ] Add focused tests: synthetic v1/v2 round-trip serialization, invariants, malformed JSON/fields, missing definitions, and unknown-version rejection.

## Implementation

Follow these steps in order from a dedicated project worktree (not the audit checkout):

1. **Revalidate anchors** — Confirm `models.py:338`, `models.py:521`, `persistence.py:86`, and `persistence.py:172` still host attempt/event persistence before editing; adjust line references in commit notes if the baseline moved.
2. **Define v2 record types** — Add immutable dataclasses or typed records for session/v2 and event/v2 including: attempt UUID, schema_version, status (active/submitted/expired/abandoned), assessment id/version/digest, profile, timestamps, abandonment fields, and content identity. Keep v1 reader adapters separate from v2 writers.
3. **Version dispatch** — In persistence readers, inspect `schema_version` first; route v1 through adapters, v2 through strict validators, unknown versions to a `UnsupportedSchemaVersion` (or equivalent) error with a safe client message—no partial parsing or silent defaults.
4. **No read-triggered migration** — Ensure GET/list/review code paths never rewrite disk state or emit upgraded files; only explicit lifecycle mutations may upgrade v1 through a recoverable transaction (handled in later tasks).
5. **Write paths** — New mutations create v2 records with checksum-friendly serialization matching existing atomic write helpers; preserve existing lock boundaries.
6. **Tests** — Add `tests/test_attempt_models_v2.py` (or extend existing model tests) covering: v1 fixture loads unchanged, v2 round-trip, missing required fields, wrong enum/status, unknown schema_version, abandonment metadata presence, and content-identity pinning.

### Affected files

- `src/codesignal_practice_simulator/models.py`
- `src/codesignal_practice_simulator/persistence.py`
- `tests/test_attempt_models_v2.py` (new or equivalent focused module)

### Negative cases to prove

- Unknown `schema_version` returns safe error before any field interpretation.
- Corrupt JSON, oversize payloads, and invalid UUIDs reject without writing side effects.
- v1 records load with honest unavailable fields; no silent v2 rewrite on read.
- Missing assessment definition at read time surfaces unavailable metadata, not fabricated defaults.

### Commands and evidence

```bash
# From project worktree root after edits
python3 -m unittest tests.test_attempt_models_v2 -v
python3 -m unittest tests.test_models tests.test_persistence -v
```

Record passing test output and note any anchor line drift from baseline `7833def`.

## Done When

- [ ] All requirements met
- [ ] v1 and v2 records deserialize deterministically; unknown versions fail closed with documented issue codes
- [ ] No read path performs disk upgrades or baseline creation
- [ ] Focused model/persistence tests pass in the worktree with captured command output in sequence results
