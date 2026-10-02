---
fest_type: task
fest_id: 01_define_validated_models_clock_and_error_taxonomy.md
fest_name: define_validated_models_clock_and_error_taxonomy
fest_parent: 01_session_state_and_workspaces
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-08T16:23:47.572085-06:00
fest_updated: 2026-09-08T19:30:48.452002-06:00
fest_tracking: true
fest_dependencies:
  - ../../003_BOOTSTRAP_MIGRATE/02_content_transfer_and_campaign/06_fest_commit
---


# Task: 004.01.01 — Define Validated Models, Clock, and Error Taxonomy

## Objective

Create a single validated owner for durable session data, injected time, and stable domain errors.

## File anchors

Existing legacy anchors: `/workspace/campaign/projects/codesignal-practice-simulator/scripts/new_attempt.py` (creates static metadata at `attempts/<timestamp>[_<name>]/attempt.json`, not a project-root metadata file) and D002/D003. Create `/workspace/campaign/projects/codesignal-practice-simulator/src/codesignal_practice_simulator/{models.py,clock.py,errors.py}`, `docs/cli-contract.md`, and `tests/test_models.py`.

## Ordered implementation steps

1. Define immutable typed models for assessment metadata, mode/profile, score summary, session state, events, and active pointer. Validate schema version, IDs, revision, UTC timestamps, deadline ordering, four-level results, and lifecycle-specific submission fields.
2. Define a Clock protocol and UTC production clock; services must accept it so tests use a fake clock.
3. In `errors.py`, centralize safe errors and exit mapping: input 2, unavailable/corrupt 3, illegal lifecycle/lock 4, failed candidate groups 5.
4. In `docs/cli-contract.md`, define expiry precisely: status/time observes active expiry, atomically records `expired`, and succeeds; resume/test on expired return exit 4 and do not score or mutate again; submit may finalize expired work by recording `expired` first if necessary, then one submitted result; repeat submit returns the stored result with no revision/event change.
5. Test valid and invalid schemas without filesystem writes.

## Error paths

Reject unsupported versions, naïve/non-UTC timestamps, negative durations, malformed IDs/scores, unknown profile, and illegal lifecycle/submission combinations before a write. Do not hide errors with a CLI traceback.

## Do-not-mutate boundaries

Do not create workspaces, read/write fixture files, migrate legacy `attempt.json`, parse Markdown as state, or change candidate code/campaign state.

## Verification and evidence

Run from the directory named in the commands. Save complete output and exit codes to `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/004_SESSION_RUNTIME/01_session_state_and_workspaces/results/01_define_validated_models_clock_and_error_taxonomy.md`; a nonzero exit is blocking unless stated below.

```sh
PROJECT="/workspace/campaign/projects/codesignal-practice-simulator"
EVIDENCE="/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/004_SESSION_RUNTIME/01_session_state_and_workspaces/results/01_define_validated_models_clock_and_error_taxonomy.md"
mkdir -p "$(dirname "$EVIDENCE")"
set -e
set -o pipefail
{
cd "$PROJECT"
python3 -m unittest tests.test_models -v
python3 -m unittest discover -s tests -p 'test_models.py' -v
git diff --check
git status --short
} 2>&1 | tee "$EVIDENCE"
```

Expected result: the commands produce the stated success output and `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/004_SESSION_RUNTIME/01_session_state_and_workspaces/results/01_define_validated_models_clock_and_error_taxonomy.md` records it.

## Definition of done

- [ ] Models have one validated schema owner and injected clock.
- [ ] The documented four-command expired-session behavior is exact and testable.
- [ ] Invalid input maps to stable safe errors before writes.
- [ ] Model tests pass.
