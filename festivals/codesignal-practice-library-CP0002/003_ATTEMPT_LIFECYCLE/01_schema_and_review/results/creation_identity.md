# Creation identity and v2 activation

Implemented by the coordinator directly (not delegated to Cursor) in the linked
cp0002-practice-library worktree. Task inserted by the 2026-09-11 dependency
repair; see results/submission_dependency.md.

## What changed

- `assessments.py`: `AssessmentDefinition.runner_contract` (only
  `unittest-groups-v1`, matching the fixed test_group_1..4 entry points) and
  `content_identity()`, which pins a definition to declared file hashes. The
  digest is SHA-256 over canonical JSON `assessment-content/v1`
  {assessment_id, content_version, runner_contract, sorted copied-file hashes}.
  Only the six candidate-facing files are covered; vendor-readme.md is not.
- `workspace_cache.py`: `content_version` parsed from the manifest's upstream
  commit as `upstream-<commit>` (lowercase hex, 7–40). A missing or malformed
  commit is fixture-setup-required, never defaulted. `pinned_assessment()` uses
  declared manifest hashes, so identity is computable without the cache present.
- `workspace.py`: `pinned_assessment()` for creation; `_validate_creation_state`
  accepts either schema and requires a v2 identity to equal the computed one;
  `_verify_staged_inputs` re-hashes every staged copy against its declared hash
  before the baseline, runner, session or event is written, closing the
  validate-to-copy gap for the bytes an identity describes;
  `_definition_for_pinned_session` requires the installed content version and
  digest for v2 and raises the new `AssessmentVersionUnavailableError`.
- `lifecycle.py`: `_start` builds `SessionStateV2` with the workspace-computed
  identity and resolves it before any mutation; all transitions build events
  through `models.session_event()`, which matches the session's schema family.
- `models.py`: `session_event()`; `SubmissionRecovery` now has
  `submission-recovery/v1` (session/v1 + event/v1, unchanged) and
  `submission-recovery/v2` (session/v2 + event/v2), with `for_submission()`
  choosing by family and `from_dict` dispatching. Mixed families are rejected.
- `persistence.py`: WAL and missing-state-event recovery work for both families;
  the v1-only guard on missing-state recovery is gone. `initial_event` follows
  the session family.
- Transports: `cli.serialize_result`, `rendering`, `web/responses`,
  `application`, `evaluation` accept `SessionRecord`.

## Deliberate decisions

- `create_attempt` still accepts session/v1 so tests can stage legacy fixtures;
  `LifecycleService` is the only production creator and always writes v2.
- The read-only `context` command no longer requires the installed definition
  for a v2 record (D002: stored metadata/results must not need the current
  catalog entry). Legacy v1 keeps its registry check, which is its only
  integrity reference. Scoring, prompts, source and status/time stay strict.
  The browser continuity journeys found this: the fixture server and the public
  CLI legitimately load different manifests.
- `03_submission_capture` may change the unreleased submission-recovery/v2
  format when it adds the review member; v1 replay may not change.

## Verification actually run

    python3 -m unittest tests.test_creation_identity -v        16 tests, OK
    just check unit                                            336 tests, OK (1 skipped)
    just check frontend                                        passed
    just check browser                                         175 passed, 0 failed
    git diff --check                                           clean

The skipped unit test is the archive build check, which needs an interpreter
with the optional build package.

Mutation check (each guard disabled in turn, then restored; every mutant was
killed by the named test): staged-byte verification, the creation-identity
equality check, and the pinned-lookup version/digest comparison.

Test fixtures that had to declare a pinned commit, because they build synthetic
manifests: tests/test_end_to_end.py, tests/test_cli.py (wheel runtime),
webui/tests/fixture_server.py, webui/tests/installed_fixture_server.py, and the
shared unit-test cache helpers. Product behavior did not change to accommodate
them.

## Not verified

- `just check wheel` did not run: no interpreter on this machine satisfies the
  packaging prerequisites (setuptools, pip, venv, wheel, build). Nothing was
  installed to work around it. The installed-wheel fixture server changed, so
  this must run at the 006 distribution gate or once a capable interpreter is
  configured.
- Real File Storage content was never fetched or scored here; every run used
  synthetic first-party fixtures. No real candidate attempt was read or changed.

## Follow-ups owned by later tasks

- D001 requires documenting that mixed-version writers are unsupported: an old
  binary cannot read session/v2. Docs are owned by 006/01/02_offline_and_docs.
- 003/02/01 must upgrade an abandoned or restarted v1 record to a v2
  legacy-identity variant; the v2 model has no such variant yet.
