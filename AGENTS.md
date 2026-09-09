# Timed-attempt agent policy

For a timed attempt, inspect `codesignal-sim context` or the generated
`STATUS.md` first.

- Edit the candidate-owned, non-executable `COACHING.md` by default.
- Read or edit candidate code only after an explicit candidate request.
- Never manually edit structured or generated state: `session.json`,
  `events.jsonl`, locks, `active.json`, or `STATUS.md`.
- Never use assessment reference, solution, stages, walkthrough, or study
  answers during a timed session. An explicit request to edit candidate code
  does not permit consulting those materials.

This is an operational policy, not a security sandbox. A process running as the
same user can bypass these workflow controls.

After submission or an explicit end to timed work, the candidate may opt into
the educational material described in `docs/agent-safety.md`.
