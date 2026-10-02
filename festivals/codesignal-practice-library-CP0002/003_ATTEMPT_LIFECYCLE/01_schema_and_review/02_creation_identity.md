---
fest_type: task
fest_id: 02_creation_identity.md
fest_name: creation identity
fest_parent: 01_schema_and_review
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-11T15:13:43.877296-06:00
fest_updated: 2026-09-11T15:51:55.028786-06:00
fest_tracking: true
---


# Task: creation identity

## Objective

Pin real File Storage content identity at attempt creation, make every existing lifecycle path read and write both session/v1 (legacy adapter) and session/v2 (pinned identity), then activate v2 creation without fabricating identity for any existing v1 attempt.

## Requirements

- [ ] Read D001, D002 and D003 (including their 2026-09-11 execution amendments) and results/submission_dependency.md. Derive File Storage `content_version` (`upstream-<manifest commit>`) and `content_digest` only from the packaged manifest's declared file hashes plus the definition's fixed runner contract, and re-verify the staged candidate-facing bytes against those hashes before the attempt is published.
- [ ] Make lifecycle, workspace, persistence recovery (missing-state event and submission WAL), candidate documents, prompts, rendering, CLI and web serialization accept `SessionState` (v1, legacy metadata adapter) and `SessionStateV2` (pinned identity) alike, then switch new-attempt creation to session/v2 with event/v2. Existing v1 attempts stay v1 and keep v1 events and v1 WAL replay byte-for-byte compatible.

## Implementation

Anchors are project-relative under src/codesignal_practice_simulator/ in the linked cp0002-practice-library worktree, including the uncommitted 003/01/01 model changes. Revalidate each before editing.

1. **Revalidate anchors** — assessments.py:11 (AssessmentDefinition), :56 (FILE_STORAGE), :67 (AssessmentRegistry); workspace_cache.py:23 (ValidatedFixtureCache), :69 (_from_fetches), :96 (validate); workspace.py:116 (create_attempt), :136 (_validate_creation_state), :276/:310 (definition lookup), :329 (_populate_staging); lifecycle.py:107 (_start), :285 (_expire_if_overdue_locked), :295 (_persist_transition_locked), :315 (_persist_submission_locked), :335 (_read_validated_session_locked); persistence.py:217/:248 (submission WAL), :312 (missing-state recovery), :475 (initial_event); models.py:1073 (SubmissionRecovery); application.py:113 (_score_selected_attempt), :343 (_start_locked); cli.py:214 (isinstance SessionState serialization); rendering.py:31-35 (context requires SessionState); web/responses.py:74; prompts.py:47.

2. **Identity derivation** — Give AssessmentDefinition a declared `runner_contract` (only `unittest-groups-v1`, matching scoring.py:193's fixed test_simulation.TestSimulateCodingFramework.test_group_1..4 entry points). Parse the manifest `upstream.commit` (lowercase hex, 7-40 chars) into ValidatedFixtureCache as `content_version = "upstream-<commit>"`; reject missing/invalid commits as fixture-setup-required, never default. Add one pure function (assessments.py or a small content_identity.py) that returns a PinnedAssessment from (definition, cache): digest = SHA-256 of canonical JSON (sort_keys, compact separators, UTF-8) of {"schema_version": "assessment-content/v1", "assessment_id", "content_version", "runner_contract", "files": [{"path": copied filename, "sha256": declared hash} sorted by path]}. Inputs are only the six copied candidate-facing files, never vendor-readme.md. The manifest, not the cache directory, supplies the hashes, so identity is computable when the cache is absent.

3. **Verified staging** — In workspace._populate_staging, after copyfile, hash each staged copied file and compare with the declared manifest hash before writing the baseline, runner, session or event. Mismatch aborts through the existing rollback (FixtureSetupRequiredError), so a v2 identity never describes bytes that were not staged. _validate_creation_state must recompute the identity and require equality with state.assessment for v2 (callers cannot inject an identity).

4. **Creation activation** — lifecycle._start keeps its AssessmentMetadata-or-definition entry contract but builds SessionStateV2 with the workspace-computed PinnedAssessment; initial_event emits EventRecordV2 for v2 sessions. Add a single helper that builds the event record matching a session's schema family and use it in _persist_transition_locked, _persist_submission_locked, missing-state recovery and initial_event. Writes reject a v1/v2 family mismatch.

5. **Legacy adapter and pinned lookup** — definition_for_persisted_session accepts SessionRecord. v1: keep today's metadata/profile equality (the D003 legacy identity adapter); never attach a content version or digest. v2: registry id lookup, display/level/profile checks, and equality of the pinned identity with the installed identity; mismatch raises a safe, distinct error (content version not installed; stored results remain reviewable). Reads that do not need the definition (003/01/04 review, 003/03 history) must not call this lookup.

6. **Lifecycle over both schemas** — Replace SessionState annotations and isinstance checks with SessionRecord in lifecycle.py, evaluation.py, application.py, rendering.py, prompts.py, candidate_documents.py, cli.py:214 and web/responses.py. dataclasses.replace works for both types; keep abandonment None (003/02 owns abandonment). persistence.recover_missing_state_event_locked supports v2 via the event helper. Generalize SubmissionRecovery: v1 sessions keep schema submission-recovery/v1 unchanged; v2 sessions use submission-recovery/v2 with the same prior/state/event invariants and one schema family per record. 03_submission_capture adds the review member to submission-recovery/v2; that format is unreleased and may change there, but v1 WAL replay may not.

7. **Transports** — v2 session JSON adds assessment.content_version, assessment.content_digest and abandonment:null. Confirm webui/src/attempt_state_normalization.ts:167 tolerates the added fields and unchanged statuses; bootstrap, CLI JSON and STATUS.md render v2 without errors. No UI feature changes here.

8. **Tests** — Add tests/test_creation_identity.py: deterministic digest; any changed hash, commit, filename or runner contract changes it; invalid/missing commit rejected; cache tampered between validation and copy rejected before publish with no attempt directory or pointer change; new attempts are v2 with identity equal to the recomputed value; synthetic v1 attempts written with the v1 serializer complete status/time/test/submit/resume/expiry with v1 events, v1 WAL replay and no content identity; v2 test/submit/expiry/missing-event and submission WAL recovery at each durable boundary; pinned-identity mismatch blocks scoring with the safe error and leaves files unchanged. Update existing tests that asserted v1 creation, keeping their behavioral intent.

### Affected files

- src/codesignal_practice_simulator/assessments.py, workspace_cache.py, workspace.py
- src/codesignal_practice_simulator/lifecycle.py, persistence.py, models.py (SubmissionRecovery, event helper)
- src/codesignal_practice_simulator/application.py, evaluation.py, rendering.py, prompts.py, candidate_documents.py, cli.py, web/responses.py
- tests/test_creation_identity.py and existing tests that assumed v1 creation

### Negative cases to prove

- Staged bytes differing from declared hashes: no attempt, no pointer change.
- Missing or invalid manifest commit: fixture setup required, no defaulted version.
- Caller-supplied v2 identity that differs from the computed identity: rejected before staging.
- v1 attempt: every command works and nothing gains a content version or digest.
- Pinned identity not installed: scoring/mutation refused with a safe error; files unchanged.

### Commands and evidence

```bash
python3 -m unittest tests.test_creation_identity -v
python3 -m unittest tests.test_attempt_models_v2 tests.test_models tests.test_persistence tests.test_lifecycle tests.test_workspace tests.test_application tests.test_workspace_pointer_recovery tests.test_cli tests.test_web_server_lifecycle tests.test_web_server_evaluation -q
just check unit
```

Record actual commands, counts and any skips in results/creation_identity.md. If the fetched cache or locked browser is unavailable, say which journeys stayed unverified; do not claim browser proof from unit tests.

## Done When

- [ ] All requirements met
- [ ] New attempts persist session/v2 and event/v2 whose content identity is recomputable from the packaged manifest and was verified against staged bytes; synthetic legacy v1 attempts complete every existing command with unchanged v1 records; the full unit suite passes with results recorded in results/creation_identity.md.
