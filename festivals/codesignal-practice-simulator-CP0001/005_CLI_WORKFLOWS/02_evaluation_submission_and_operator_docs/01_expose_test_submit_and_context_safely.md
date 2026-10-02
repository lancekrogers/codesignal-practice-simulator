---
fest_type: task
fest_id: 01_expose_test_submit_and_context_safely.md
fest_name: expose_test_submit_and_context_safely
fest_parent: 02_evaluation_submission_and_operator_docs
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-08T16:23:47.631738-06:00
fest_updated: 2026-09-08T22:20:16.659408-06:00
fest_tracking: true
fest_dependencies:
  - ../01_command_interface_and_live_session/06_fest_commit
---


# Task: 005.02.01 — Expose Test, Submit, and Context Safely

## Objective

Wire evaluation and finality commands with explicit expired-session semantics and idempotent submission.

## File anchors

Existing anchors: `/workspace/campaign/projects/codesignal-practice-simulator/src/codesignal_practice_simulator/cli.py`, 004 scoring/lifecycle/rendering services, `scripts/scorecard.py`, `docs/cli-contract.md`, and `tests/test_cli.py`. Selected-state anchors are `attempts/<attempt-id>/{session.json,events.jsonl,simulation.py}`.

## Ordered implementation steps

1. Wire `test` only to an active selected session. Persist per-level results/event through services, return exit 0 for all pass and exit 5 for one or more failed groups.
2. If `test` observes expiry, persist `expired` once and return exit 4 without running tests; later expired tests return exit 4 with no new write.
3. Wire `submit` to score and finalize active or expired work. An overdue active submission first records expiry, then stores exactly one final score/submission event and returns exit 0. A submitted attempt returns the exact stored result on every repeat submit—no runner invocation, revision change, event, or timestamp change.
4. Wire `context --format markdown|json` to safe renderer output only; status/context remain readable after expiry/submission.
5. Test failed groups, subprocess evidence, all final states, JSON envelopes, and repeat-submit byte equality.

## Error paths

Candidate test failures are scored exit 5, not crashes. Missing/corrupt selection is exit 3; invalid format/input is exit 2; lock/lifecycle denial is exit 4. A scoring/submit failure must not partially mark submitted.

## Do-not-mutate boundaries

Never inspect candidate source or education material for context, mutate fixture/reference files, run tests after expiry, or write a second submission event/result.

## Verification and evidence

Run from the directory named in the commands. Save complete output and exit codes to `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/005_CLI_WORKFLOWS/02_evaluation_submission_and_operator_docs/results/01_expose_test_submit_and_context_safely.md`; a nonzero exit is blocking unless stated below.

```sh
PROJECT="/workspace/campaign/projects/codesignal-practice-simulator"
EVIDENCE="/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/005_CLI_WORKFLOWS/02_evaluation_submission_and_operator_docs/results/01_expose_test_submit_and_context_safely.md"
mkdir -p "$(dirname "$EVIDENCE")"
set -e
set -o pipefail
{
cd "$PROJECT"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
codesignal-sim start --workspace-root "$tmp" --mode drill --json
codesignal-sim context --json --workspace-root "$tmp"
if codesignal-sim test --workspace-root "$tmp"; then exit 1; else test "$?" -eq 5; fi
codesignal-sim submit --workspace-root "$tmp" --json
codesignal-sim submit --workspace-root "$tmp" --json
python3 -m unittest tests.test_cli -v
git diff --check
git status --short
} 2>&1 | tee "$EVIDENCE"
```

Expected result: the commands produce the stated success output and `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/005_CLI_WORKFLOWS/02_evaluation_submission_and_operator_docs/results/01_expose_test_submit_and_context_safely.md` records it.

## Definition of done

- [ ] Test exits 0/5 only for active sessions and preserves per-level evidence.
- [ ] Expired submit finalizes once; repeated submit is stored-result idempotent.
- [ ] Status/context remain safe reads after finality.
- [ ] CLI tests cover all documented error paths.
