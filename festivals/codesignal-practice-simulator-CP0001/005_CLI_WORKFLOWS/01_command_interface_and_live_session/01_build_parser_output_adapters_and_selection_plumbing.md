---
fest_type: task
fest_id: 01_build_parser_output_adapters_and_selection_plumbing.md
fest_name: build_parser_output_adapters_and_selection_plumbing
fest_parent: 01_command_interface_and_live_session
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-08T16:23:47.612096-06:00
fest_updated: 2026-09-08T20:45:49.767896-06:00
fest_tracking: true
fest_dependencies:
  - ../../004_SESSION_RUNTIME/02_assessment_scoring_and_agent_surfaces/06_fest_commit
---


# Task: 005.01.01 — Build Parser, Output Adapters, and Selection Plumbing

## Objective

Create one argparse command surface with consistent human/JSON envelopes and no domain logic in handlers.

## File anchors

Existing anchors: `/workspace/campaign/projects/codesignal-practice-simulator/src/codesignal_practice_simulator/{cli.py,__main__.py}`, 004 services, and `justfiles/practice.just`. Update `docs/cli-contract.md` and `tests/test_cli.py`.

## Ordered implementation steps

1. Define argparse subparsers once for `start`, `resume`, `status`, `time`, `task`, `test`, `submit`, and `context`; add common `--json`, `--workspace-root`, and `--attempt` where applicable.
2. Centralize output envelopes with a version plus result or structured error; map domain errors to exits 2–5.
3. Make handlers construct/select services and serialize typed results only; handlers must not read/write JSON, locks, fixtures, or tests.
4. Define selector precedence: explicit `--attempt` first, otherwise valid active pointer; no timestamp guessing.
5. Test console/module parity, help, JSON, input errors, and no partial mutation.

## Error paths

Missing command, bad option combination/path, malformed selector, or serializer failure returns safe structured error (input exit 2 where appropriate) with no traceback or state mutation.

## Do-not-mutate boundaries

Do not duplicate lifecycle/persistence/scoring logic in CLI or modify candidate/fixture/reference/campaign files.

## Verification and evidence

Run from the directory named in the commands. Save complete output and exit codes to `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/005_CLI_WORKFLOWS/01_command_interface_and_live_session/results/01_build_parser_output_adapters_and_selection_plumbing.md`; a nonzero exit is blocking unless stated below.

```sh
PROJECT="/workspace/campaign/projects/codesignal-practice-simulator"
EVIDENCE="/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/005_CLI_WORKFLOWS/01_command_interface_and_live_session/results/01_build_parser_output_adapters_and_selection_plumbing.md"
mkdir -p "$(dirname "$EVIDENCE")"
set -e
set -o pipefail
{
cd "$PROJECT"
python3 -m unittest tests.test_cli -v
codesignal-sim --help
python3 -m codesignal_practice_simulator --help
git diff --check
git status --short
} 2>&1 | tee "$EVIDENCE"
```

Expected result: the commands produce the stated success output and `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/005_CLI_WORKFLOWS/01_command_interface_and_live_session/results/01_build_parser_output_adapters_and_selection_plumbing.md` records it.

## Definition of done

- [ ] Console and module interfaces have identical help/output semantics.
- [ ] All errors use stable JSON/human envelopes and documented exits.
- [ ] No handler owns state or scoring logic.
- [ ] CLI tests pass.
