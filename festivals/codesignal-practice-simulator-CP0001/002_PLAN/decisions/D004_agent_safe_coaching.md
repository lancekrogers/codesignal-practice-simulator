# D004: Agent-Safe Coaching and Evaluation Boundary

**Status:** accepted<br>
**Date:** 2026-09-08

## Context

The simulator is intended to support terminal-agent collaboration without
turning a timed practice session into an uncontrolled reference-solution
surface. The source contains walkthroughs, staged solutions, a reference
implementation, and a documented Level-4 fixture/specification discrepancy.
Those materials are valuable for study, but exposing them during an active
attempt compromises the practice signal.

An agent running under the same user account can technically read or overwrite
any writable file. File permissions and instructions cannot create a security
sandbox. The product can instead provide a reliable operational boundary:
state and scoring have clear owners, coaching is isolated from evaluation, and
the expected agent behavior is explicit and testable.

## Options

### Option A: Treat all files in an attempt as an unrestricted agent workspace
- **Pros:** No additional documents or policy to maintain.
- **Cons:** Agents can accidentally overwrite `simulation.py`, mutate session
  records, or consult answers during timed work; the candidate cannot
  distinguish evaluated work from collaborative notes.

### Option B: Provide a dedicated coaching surface and explicit live-session instructions
- **Pros:** Gives agents a narrow default write target; keeps coaching
  non-executable and outside scoring; makes candidate consent and forbidden
  source material visible; can be verified with fixture and scoring tests.
- **Cons:** Depends on cooperating agents and users rather than operating
  system isolation; adds generated/status and instruction documents to keep
  current.

### Option C: Prevent agent access through a separate hosted or sandboxed environment
- **Pros:** Could provide stronger technical isolation.
- **Cons:** Requires account, process, or remote-environment controls outside
  a private local CLI; adds complexity without being required for the first
  release.

## Decision

Choose Option B. Every candidate workspace includes `COACHING.md` as a
candidate-owned, plain-text collaboration log. It is not imported, executed,
copied into a test subprocess, parsed as session state, or included in score
calculation. It is the only file an agent may edit by default. The simulator
may generate `STATUS.md` from structured state but agents must not manually
edit it. `context` returns the same derived information in Markdown or JSON;
neither rendering is an authority.

Root and attempt `AGENTS.md` documents must require an agent to inspect
`codesignal-sim context` or generated status before acting. They state these
default boundaries:

| Area | Agent rule during an active attempt |
| --- | --- |
| `COACHING.md` | May add candidate-approved goals, questions, and high-level hints. |
| `simulation.py` and copied prompts/tests | Read or edit only after an explicit candidate request; never change them implicitly while coaching. |
| `session.json`, `events.jsonl`, active pointer, locks, `STATUS.md` | Never edit; use the CLI for session actions and let it generate derived views. |
| `assessment/`, `solution/`, `study/`, walkthroughs, and staged answers | Never use as a source of hints or expose their contents during a timed attempt. |

An explicit request for assistance permits only the requested candidate-file
interaction and does not authorize consulting reference, staged, walkthrough,
or study-answer material. The agent must disclose that local workflow controls
cannot prevent a same-user process from bypassing this policy. After
submission or an explicit end to the timed attempt, the candidate may opt into
the educational material and a comparison/review workflow.

## Consequences

- Fixture copies, test commands, and the scorer must use an explicit allowlist
  of evaluated candidate inputs; `COACHING.md`, `STATUS.md`, and `AGENTS.md`
  are excluded.
- Every scoring subprocess launches exactly as
  `<absolute-interpreter> -I -S <attempt>/.scoring/run_group.py <group>` with
  the selected attempt as its working directory. The copied attempt-local
  runner validates its location and admits only copied candidate/test paths
  plus interpreter standard-library paths; it admits no global/user site,
  project, editable-install, cache, solution, study, reference, or
  environment-derived path. Its minimal environment omits `PYTHONPATH` and
  Python site/configuration variables. Tests prove installed editable-project,
  hostile-`PYTHONPATH`, and loose-reference sentinels cannot import or affect
  a score.
- Tests must prove that changes to coaching and regenerated status do not
  modify `simulation.py`, change imported-fixture checksums, or change score
  output.
- Generated context must expose only safe paths, lifecycle, clock, selected
  assessment/mode, score summary, and next legal commands—not candidate
  source or reference content.
- Documentation must distinguish operational agent safety from a security
  boundary and must keep the Level-4 discrepancy available only in the
  post-attempt educational path.
