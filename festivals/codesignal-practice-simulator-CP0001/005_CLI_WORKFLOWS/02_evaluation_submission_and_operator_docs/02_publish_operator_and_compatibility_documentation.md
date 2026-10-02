---
fest_type: task
fest_id: 02_publish_operator_and_compatibility_documentation.md
fest_name: publish_operator_and_compatibility_documentation
fest_parent: 02_evaluation_submission_and_operator_docs
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-08T16:23:47.632065-06:00
fest_updated: 2026-09-08T22:37:55.627908-06:00
fest_tracking: true
---


# Task: 005.02.02 — Publish Operator and Compatibility Documentation

## Objective

Document the CLI as the stable interface and keep Just/legacy material as accurately labeled compatibility support.

## File anchors

Existing anchors: `/workspace/campaign/projects/codesignal-practice-simulator/{README.md,AGENTS.md,justfile,justfiles/{practice.just,verify.just},notes/**}`, `docs/{cli-contract.md,drill-profiles.md,agent-safety.md}`, and the completed CLI. Update those same files.

## Ordered implementation steps

1. Document installation, console/module equivalence, full and named drill
   use, selector precedence, workspace location, JSON envelopes, all exit
   codes, and the no-license FETCH_ONLY setup command/cache boundary.
2. Document exact expiry behavior: status/time persist and show expired state; expired resume/test exit 4; expired submit finalizes once; submitted repeat submit returns stored result without mutation.
3. Adapt Just recipes to invoke the CLI as optional shortcuts. Preserve meaningful legacy verification recipes and label deprecated behavior.
4. Document agent boundaries, explicit candidate approval, post-attempt learning, and the Level-4 compatibility/spec distinction without exposing walkthrough guidance in live command examples.
5. Run every example command on a temporary workspace and correct only documentation/recipe defects found.

## Error paths

If an example tracks/writes vendor content, writes cache, structured state, or
candidate source unexpectedly; claims a sandbox; or disagrees with CLI output,
fix the documentation/recipe before completion.

## Do-not-mutate boundaries

Do not change lifecycle/scoring implementation, fetched-cache/reference files,
active user attempts, or unrelated campaign content.

## Verification and evidence

Run from the directory named in the commands. Save complete output and exit codes to `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/005_CLI_WORKFLOWS/02_evaluation_submission_and_operator_docs/results/02_publish_operator_and_compatibility_documentation.md`; a nonzero exit is blocking unless stated below.

```sh
PROJECT="/workspace/campaign/projects/codesignal-practice-simulator"
EVIDENCE="/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/005_CLI_WORKFLOWS/02_evaluation_submission_and_operator_docs/results/02_publish_operator_and_compatibility_documentation.md"
mkdir -p "$(dirname "$EVIDENCE")"
set -e
set -o pipefail
{
cd "$PROJECT"
codesignal-sim --help
python3 -m codesignal_practice_simulator --help
just --list
just verify
python3 -m unittest tests.test_cli -v
git diff --check
git status --short
} 2>&1 | tee "$EVIDENCE"
```

Expected result: the commands produce the stated success output and `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/005_CLI_WORKFLOWS/02_evaluation_submission_and_operator_docs/results/02_publish_operator_and_compatibility_documentation.md` records it.

## Definition of done

- [ ] Documentation matches implemented commands, errors, expiry, and idempotency.
- [ ] A user can use every command without Just.
- [ ] Just is an accurate optional shortcut.
- [ ] Documentation examples and CLI tests pass.
