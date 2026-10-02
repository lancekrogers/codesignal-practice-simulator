---
fest_type: task
fest_id: 03_implement_lifecycle_application_services.md
fest_name: implement_lifecycle_application_services
fest_parent: 01_session_state_and_workspaces
fest_order: 3
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-08T16:23:47.572604-06:00
fest_updated: 2026-09-08T19:44:27.649371-06:00
fest_tracking: true
---


# Task: 004.01.03 — Implement Lifecycle Application Services

## Objective

Implement deterministic lifecycle transitions outside the CLI, including final idempotent submission.

## File anchors

Existing anchors: 004.01.01 models/errors/clock, 004.01.02 persistence/workspace, and `/workspace/campaign/projects/codesignal-practice-simulator/scripts/{new_attempt.py,scorecard.py}`. Create `/workspace/campaign/projects/codesignal-practice-simulator/src/codesignal_practice_simulator/lifecycle.py` and `tests/test_lifecycle.py`.

## Ordered implementation steps

1. Implement start, selection, resume, expiry observation, test-result recording, and submit services; start creates a pointer, explicit active resume may replace it.
2. Under the selected-attempt lock and injected clock, the first observer of an overdue active attempt writes `active -> expired` plus one event. `status` and `time` return the expired view successfully after that observation.
3. Refuse `resume` and `test` for expired or submitted attempts with exit-class 4, with no new score, revision, or event.
4. Let `submit` finalize either active or expired attempts. If deadline elapsed while submit begins, first persist expiry/event, then score and persist `submitted`/submission metadata/event. A submit of already-submitted state returns the exact stored final result and creates no write, revision, or event.
5. Test all transitions with fake clocks, revision recovery, and lock contention.

## Error paths

Illegal active-to-active, submitted-to-anything, expired-to-resume/test, lock contention, and corrupt selection must return the documented error and leave valid neighboring attempts byte-identical. Do not make expiration a read-only inference.

## Do-not-mutate boundaries

Do not put state logic in CLI, write fixture/candidate code, score reference material, alter other attempts, or modify campaign state.

## Verification and evidence

Run from the directory named in the commands. Save complete output and exit codes to `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/004_SESSION_RUNTIME/01_session_state_and_workspaces/results/03_implement_lifecycle_application_services.md`; a nonzero exit is blocking unless stated below.

```sh
PROJECT="/workspace/campaign/projects/codesignal-practice-simulator"
EVIDENCE="/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/004_SESSION_RUNTIME/01_session_state_and_workspaces/results/03_implement_lifecycle_application_services.md"
mkdir -p "$(dirname "$EVIDENCE")"
set -e
set -o pipefail
{
cd "$PROJECT"
python3 -m unittest tests.test_lifecycle -v
python3 -m unittest discover -s tests -p 'test_lifecycle.py' -v
git diff --check
git status --short
} 2>&1 | tee "$EVIDENCE"
```

Expected result: the commands produce the stated success output and `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/004_SESSION_RUNTIME/01_session_state_and_workspaces/results/03_implement_lifecycle_application_services.md` records it.

## Definition of done

- [ ] Expiry is persisted once and status/time remain safe reads.
- [ ] Expired resume/test are exit 4 without mutation.
- [ ] Expired submit finalizes once; repeat submit is byte-for-byte idempotent.
- [ ] Lifecycle tests pass deterministically.
