# Timed-attempt agent policy

For a timed attempt, read only derived context first:
`codesignal-sim context --workspace-root PATH`, or the attempt's generated
`STATUS.md`. These views are non-authoritative; never manually update them.

- Use candidate-owned, non-executable `COACHING.md` for candidate-approved
  goals, questions, and high-level hints. Do not put source, history, test
  output, answers, or hidden-test claims there.
- Ask explicit permission before reading candidate source or source history;
  ask separately before editing source. A source request never permits access
  to protected assessment material.
- During timed work, never read or use reference, solution, stages,
  walkthrough, study, vendor, fixture cache, copied tests, or hidden-test
  material. Never import or execute coaching in `simulation.py`.
- Never manually edit `session.json`, `events.jsonl`, `STATUS.md`, locks, or
  `active.json`.

## Live browser/terminal sequence

1. In a fetched workspace, launch the loopback browser with
   `codesignal-sim web --workspace-root "$workspace" --port 0 --no-open`.
   Open the newly printed complete loopback URL locally; its `#...` fragment
   is a private per-launch capability and must not be retained or shared. The
   browser removes it from the URL and uses it only in a same-loopback-origin
   `X-Simulator-Token` header, which can appear in request diagnostics.
2. After the browser starts the attempt, inspect
   `codesignal-sim context --workspace-root "$workspace"` and `STATUS.md`.
3. Write only candidate-approved notes to `COACHING.md`; ask before source or
   history access.
4. Verify browser state through its server response and the CLI
   `status`, `time`, `context`, `test`, or `submit` commands.

The browser UI and direct CLI are separate transports for one attempt. The
server-authoritative timer, scoring, and lifecycle own the result; candidate
source/history belong to the candidate, while `session.json` and events belong
to the simulator. This is operational policy, not a security sandbox: another
same-user process can bypass it.

Browser confirmation starts the timer immediately and cannot pause, extend, or
reset it. The browser makes an expired or submitted attempt read-only; its
**Submit** button is disabled after expiry. The CLI `submit` command may
finalize an expired attempt once with `--workspace-root "$workspace"`, after
which refresh or reconnect shows the stored result. No local result is
equivalent to official hidden tests.

After submission or an explicit end, post-attempt learning is opt-in as
described in `docs/agent-safety.md`.
