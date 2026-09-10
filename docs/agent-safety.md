# Agent safety during timed attempts

This is an operational collaboration policy, not a security or access-control
boundary. It does not sandbox an agent or a same-user process; that process
can still read or alter local files. This is operational policy, not a security
sandbox.

## Live-session boundary

Use this sequence:

1. Launch the loopback browser from a fetched workspace:
   `codesignal-sim web --workspace-root "$workspace"`.
2. After the browser starts an attempt, inspect
   `codesignal-sim context --workspace-root "$workspace"` or the selected
   attempt's generated `STATUS.md`. For automation, use
   `codesignal-sim context --workspace-root "$workspace" --format json --json`.
3. Use candidate-owned `COACHING.md` for candidate-approved goals, questions,
   and high-level hints. Ask explicit permission before reading candidate
   source or source history, and ask separately before editing source.
4. Verify browser state through the server response and the CLI's `status`,
   `time`, `context`, `test`, or `submit` commands.

The browser UI and direct CLI are separate transports for the same attempt.
The server-authoritative timer, scoring, and lifecycle own the result.
Candidate source and source history belong to the candidate; `COACHING.md` is
candidate-owned non-executable text; `session.json` and `events.jsonl` are
simulator-owned authoritative state; `STATUS.md` is a generated view.

During timed work, never read or use reference, solution, stages, walkthrough,
study, vendor, fixture cache, copied tests, or hidden-test material. Never
import or execute coaching in `simulation.py`, make hidden-test claims, or
manually edit `session.json`, `events.jsonl`, `STATUS.md`, locks, or
`active.json`. Coaching permission does not authorize protected material.

## Post-attempt education

After submission or an explicit end to timed work, the candidate may opt into
the learning materials in [`study/`](../study/), reference and staged
solutions in [`solution/`](../solution/), the
[`walkthrough`](../notes/walkthrough.md), and deprecated compatibility
recipes. These remain outside live context; the Level-4 discrepancy note
belongs to this post-attempt path too.
