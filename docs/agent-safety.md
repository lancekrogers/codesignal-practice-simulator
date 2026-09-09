# Agent safety during timed attempts

Timed attempts use an operational collaboration policy, not a security
boundary. An agent or other process running as the same user can read or alter
local files despite these instructions.

## Scoring process containment

The scorer starts each level in its own process group. Its attempt-local Python
audit hook rejects Python APIs that create or launch child processes, and
timeout cleanup snapshots current descendants before killing them deepest-first
and then killing the original group. This is defense-in-depth process
containment so a Python candidate cannot intentionally retain a descendant
outside the scoring group; it is not a general security sandbox.

## Live-session boundary

Before acting, inspect generated `STATUS.md`.
Those views are derived from validated `session.json` and `events.jsonl`; they
are non-authoritative and never contain candidate source, answer-bearing test
output, or reference content.

During a timed session:

- Treat `COACHING.md` as candidate-owned, non-executable text and edit it by
  default.
- Read or edit candidate code only when the candidate explicitly asks.
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
also belongs only to this post-submission educational path, never live context.
