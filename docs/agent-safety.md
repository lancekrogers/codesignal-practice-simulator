# Agent safety during timed attempts

Timed attempts use an operational collaboration policy, not a security or
access-control boundary. This project does not claim to sandbox an agent or
other process running as the same user; such a process can read or alter local
files despite these instructions.

## Live-session boundary

Before acting, inspect safe generated context with
`codesignal-sim context --workspace-root PATH`, or read the selected attempt's
generated `STATUS.md`. Both are derived from validated `session.json` and
`events.jsonl`, are non-authoritative, and never contain candidate source,
answer-bearing test output, copied prompts, fixtures, or reference content.
`context --format json --json` provides the same safe context in the stable
CLI envelope for automation.

During a timed session:

- Treat `COACHING.md` as candidate-owned, non-executable text and edit it by
  default.
- Read or edit candidate code only when the candidate gives explicit
  permission. Permission to inspect candidate code does not extend to
  references or answers.
- Never manually edit structured or generated state: `session.json`,
  `events.jsonl`, locks, `active.json`, or `STATUS.md`.
- Never use or reveal assessment reference, solution, stages, walkthrough, or
  study answers. A request to edit candidate code does not authorize those
  sources.

## Post-submission education

After submission or an explicit end to timed work, the candidate can choose to
use the learning materials in [`study/`](../study/), the reference and staged
solutions in [`solution/`](../solution/), and the
[walkthrough](../notes/walkthrough.md). The [Level-4 discrepancy note](../notes/level4-rollback-discrepancy.md)
and deprecated compatibility recipes also belong only to this post-submission
educational path, never live context.
