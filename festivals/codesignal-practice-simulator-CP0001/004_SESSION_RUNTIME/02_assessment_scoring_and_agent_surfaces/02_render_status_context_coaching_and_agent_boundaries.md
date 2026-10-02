---
fest_type: task
fest_id: 02_render_status_context_coaching_and_agent_boundaries.md
fest_name: render_status_context_coaching_and_agent_boundaries
fest_parent: 02_assessment_scoring_and_agent_surfaces
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-08T16:23:47.5918-06:00
fest_updated: 2026-09-08T20:09:55.337765-06:00
fest_tracking: true
---


# Task: 004.02.02 — Render Status, Context, Coaching, and Agent Boundaries

## Objective

Produce derived safe views and explicit operational coaching instructions without creating a false security boundary.

## File anchors

Existing anchors: validated `session.json`/`events.jsonl`, `/workspace/campaign/projects/codesignal-practice-simulator/notes/{walkthrough.md,level4-rollback-discrepancy.md}`, and D004. Create `src/codesignal_practice_simulator/rendering.py`, root `AGENTS.md`, `docs/agent-safety.md`, attempt `COACHING.md`/`AGENTS.md`, generated attempt `STATUS.md`, and `tests/test_rendering.py`.

## Ordered implementation steps

1. Render Markdown/JSON only from selected validated state/events: safe paths, assessment/mode/profile, lifecycle, deadline, score summary, and next legal commands.
2. Generate/update `STATUS.md` solely through the renderer; create `COACHING.md` as candidate-owned non-executable text.
3. Write root and attempt AGENTS instructions: inspect context/status first; edit coaching by default; candidate code requires explicit request; structured/generated state is never edited manually; never use assessment reference, solution, stages, walkthrough, or study answers during timed work. State explicitly this is operational policy, not a sandbox.
4. Document post-submission education and Level-4 discrepancy outside live context.
5. Add invariance tests for rendering, coaching/status changes, validated-cache
   hashes, and candidate source.

## Error paths

Invalid state/events must return session-unavailable and must not generate a
misleading status. Renderer failures cannot mutate candidate code, state,
validated cache, or reference material.

## Do-not-mutate boundaries

Do not parse Markdown as state; do not include candidate code, test output with answers, solution/study/walkthrough content in context; do not claim security isolation.

## Verification and evidence

Run from the directory named in the commands. Save complete output and exit codes to `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/004_SESSION_RUNTIME/02_assessment_scoring_and_agent_surfaces/results/02_render_status_context_coaching_and_agent_boundaries.md`; a nonzero exit is blocking unless stated below.

```sh
PROJECT="/workspace/campaign/projects/codesignal-practice-simulator"
EVIDENCE="/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/004_SESSION_RUNTIME/02_assessment_scoring_and_agent_surfaces/results/02_render_status_context_coaching_and_agent_boundaries.md"
mkdir -p "$(dirname "$EVIDENCE")"
set -e
set -o pipefail
{
cd "$PROJECT"
python3 -m unittest tests.test_rendering -v
python3 -m unittest discover -s tests -p 'test_rendering.py' -v
git diff --check
git status --short
} 2>&1 | tee "$EVIDENCE"
```

Expected result: the commands produce the stated success output and `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/004_SESSION_RUNTIME/02_assessment_scoring_and_agent_surfaces/results/02_render_status_context_coaching_and_agent_boundaries.md` records it.

## Definition of done

- [ ] Status/context are derived, safe, and non-authoritative.
- [ ] Root and attempt guidance expose the exact boundaries.
- [ ] Rendering failure/invariance tests pass.
- [ ] No reference content leaks into a timed-attempt surface.
