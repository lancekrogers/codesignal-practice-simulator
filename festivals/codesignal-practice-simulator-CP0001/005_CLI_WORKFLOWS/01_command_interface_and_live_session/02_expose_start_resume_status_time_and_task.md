---
fest_type: task
fest_id: 02_expose_start_resume_status_time_and_task.md
fest_name: expose_start_resume_status_time_and_task
fest_parent: 01_command_interface_and_live_session
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-08T16:23:47.61242-06:00
fest_updated: 2026-09-08T20:56:45.981229-06:00
fest_tracking: true
---


# Task: 005.01.02 — Expose Start, Resume, Status, Time, and Task

## Objective

Wire live-session commands to services with deterministic selection and exact expiration behavior.

## File anchors

Existing anchors: `src/codesignal_practice_simulator/cli.py`, 004 lifecycle/workspace/rendering/scoring services, `docs/cli-contract.md`, and `tests/test_cli.py`. Runtime anchors: `attempts/active.json` and selected `attempts/<attempt-id>/session.json`.

## Ordered implementation steps

1. Wire `start` to full and named drill profiles, persisting mode, effective
   duration, start, and deadline only after validated fixture setup.
2. Wire `resume`, `status`, and `time` through selection/lifecycle services. Status/time observe an overdue active session, atomically persist `expired` once, then return a successful expired view.
3. On expired/submitted sessions, `resume` exits 4 with no mutation. `task` is a safe read of the copied selected prompt; it never reads root fixture, solution, or study content.
4. Add coverage for absent/invalid cache producing an actionable
   setup-required error with no attempt, plus no/bad pointer, invalid selector,
   unavailable level, JSON output, expired state, submitted state, and
   explicit-selector precedence.
5. Document repair actions without reference leakage.

## Error paths

Missing fixture setup is a documented nonzero setup-required error; no
selected/corrupt attempt is exit 3; invalid level/selector syntax is exit 2;
final-session resume is exit 4. Do not score or mutate candidate source or the
cache during status/time/task.

## Do-not-mutate boundaries

Do not select newest directory, read solution/study content, mutate cached
vendor/candidate code, or alter a nonselected attempt/campaign state.

## Verification and evidence

Run from the directory named in the commands. Save complete output and exit codes to `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/005_CLI_WORKFLOWS/01_command_interface_and_live_session/results/02_expose_start_resume_status_time_and_task.md`; a nonzero exit is blocking unless stated below.

```sh
PROJECT="/workspace/campaign/projects/codesignal-practice-simulator"
EVIDENCE="/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/005_CLI_WORKFLOWS/01_command_interface_and_live_session/results/02_expose_start_resume_status_time_and_task.md"
mkdir -p "$(dirname "$EVIDENCE")"
set -e
set -o pipefail
{
cd "$PROJECT"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
codesignal-sim start --workspace-root "$tmp" --mode full --json
codesignal-sim status --workspace-root "$tmp" --json
codesignal-sim time --workspace-root "$tmp"
codesignal-sim task --workspace-root "$tmp" --level 1
python3 -m unittest tests.test_cli -v
git diff --check
git status --short
} 2>&1 | tee "$EVIDENCE"
```

Expected result: the commands produce the stated success output and `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/005_CLI_WORKFLOWS/01_command_interface_and_live_session/results/02_expose_start_resume_status_time_and_task.md` records it.

## Definition of done

- [ ] Start/selection/lifecycle wiring works for JSON and human outputs.
- [ ] Expired status/time succeed after one persisted expiry; expired resume is exit 4.
- [ ] Task reads only copied prompt material.
- [ ] CLI tests pass without cache/candidate mutation and prove the
  setup-required path.
