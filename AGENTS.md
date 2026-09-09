# Timed-attempt agent policy

For a timed attempt, inspect safe generated context first: run
`codesignal-sim context --workspace-root PATH` or read that attempt's
generated `STATUS.md`. These views are non-authoritative; do not manually
update them.

- Edit the candidate-owned, non-executable `COACHING.md` by default.
- Read or edit candidate code only after explicit candidate permission.
- Never manually edit structured or generated state: `session.json`,
  `events.jsonl`, locks, `active.json`, or `STATUS.md`.
- Never use assessment reference, solution, stages, walkthrough, or study
  answers during a timed session. An explicit request to edit candidate code
  does not permit consulting those materials.

This is an operational policy, not a sandbox or access-control boundary. A
process running as the same user can bypass these workflow controls.

After submission or an explicit end to timed work, the candidate may opt into
the post-attempt educational and legacy compatibility material described in
`docs/agent-safety.md`.
