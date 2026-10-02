---
fest_type: task
fest_id: 01_generalize_assessment_lookup_and_score_isolated_attempts.md
fest_name: generalize_assessment_lookup_and_score_isolated_attempts
fest_parent: 02_assessment_scoring_and_agent_surfaces
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-08T16:23:47.591543-06:00
fest_updated: 2026-09-08T20:03:32.635845-06:00
fest_tracking: true
fest_dependencies:
  - ../01_session_state_and_workspaces/07_fest_commit
---


# Task: 004.02.01 — Generalize Assessment Lookup and Score Isolated Attempts

## Objective

Register only the file-storage assessment and produce independent, persisted partial-credit results from copied candidate inputs.

## File anchors

Existing anchors: user-authored scoring logic, a validated local cache's
`test_simulation.py`, `solution/test_spec.py`, and 004.01 lifecycle/persistence.
Create assessment/scoring modules, tests, and provenance documentation.

## Ordered implementation steps

1. Define a registry interface and register only `file_storage`, identifying
   validated-cache source files, copied candidate inputs, level groups 1–4,
   and supported profiles.
2. Run each group as exactly
   `<absolute-interpreter> -I -S <attempt>/.scoring/run_group.py <group>`,
   with the selected attempt as `cwd`. Copy the runner/bootstrap into each
   attempt; it validates its own path and replaces application `sys.path` with
   only the copied attempt candidate/test directory plus interpreter
   standard-library paths. It must add no project, editable-install, user-site,
   cache, solution, study, reference, or environment-derived path. Pass a
   minimal child environment that omits `PYTHONPATH` and Python
   site/configuration variables. Capture safe output and continue after a group
   fails or crashes.
3. Compute per-level outcomes, passed-level count, and highest contiguous pass; persist through lifecycle services rather than scorer filesystem writes.
4. Exclude `COACHING.md`, `STATUS.md`, `AGENTS.md`, `solution/`, `study/`, and
   cache-root content from subprocess input and scoring. Document the
   fetch-only Level-4 compatibility profile and separate prose-correct profile.
5. Test success, failure, crash, timeout, missing inputs, non-interference,
   setup-required behavior, and cache hashes. Install the project editable with
   an importable sentinel, inject a hostile `PYTHONPATH` sentinel, and place a
   loose reference sentinel outside the attempt. Prove the `-I -S` child cannot
   import or observe any sentinel and the score remains candidate-only.

## Error paths

Unknown assessment, missing/invalid cache, missing copied prompt/test, invalid
level group, launch failure, timeout, attempted project/reference import, and
hostile inherited environment become explicit evidence while later groups
still run. A runner outside the attempt or any non-standard-library path in
the child `sys.path` is an isolation failure. Never run tests in place against
the cache.

## Do-not-mutate boundaries

Do not add another assessment, modify the cache/reference/study files, score
coaching/status, write state directly, or touch other attempts/campaign state.

## Verification and evidence

Run from the directory named in the commands. Save complete output and exit codes to `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/004_SESSION_RUNTIME/02_assessment_scoring_and_agent_surfaces/results/01_generalize_assessment_lookup_and_score_isolated_attempts.md`; a nonzero exit is blocking unless stated below.

```sh
PROJECT="/workspace/campaign/projects/codesignal-practice-simulator"
EVIDENCE="/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/004_SESSION_RUNTIME/02_assessment_scoring_and_agent_surfaces/results/01_generalize_assessment_lookup_and_score_isolated_attempts.md"
mkdir -p "$(dirname "$EVIDENCE")"
set -e
set -o pipefail
{
cd "$PROJECT"
python3 -m unittest tests.test_scoring -v
python3 -m unittest tests.test_migration -v
python3 solution/test_spec.py
git diff --check
git status --short
} 2>&1 | tee "$EVIDENCE"
```

Expected result: the commands produce the stated success output and `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/004_SESSION_RUNTIME/02_assessment_scoring_and_agent_surfaces/results/01_generalize_assessment_lookup_and_score_isolated_attempts.md` records it.

## Definition of done

- [ ] Four independently executed outcomes, pass count, and contiguous reach are persisted.
- [ ] Failures/crashes do not skip later groups.
- [ ] Coaching/status cannot affect score or validated-cache hashes.
- [ ] The exact `-I -S` attempt-local child launch and bootstrap path policy
  prevent installed editable-project, inherited `PYTHONPATH`, and loose
  reference sentinels from importing into candidate evaluation.
- [ ] Scoring and legacy profile tests pass.
