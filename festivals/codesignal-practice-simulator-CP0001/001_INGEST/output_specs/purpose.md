# Purpose: CodeSignal Practice Simulator

## Outcome

Create a durable, private Python repository at
`lancekrogers/codesignal-practice-simulator`, integrated into the JobSearch
campaign as `projects/codesignal-practice-simulator`. It will preserve the
existing `file_storage` Industry Coding Framework practice material while
turning its ad-hoc scripts into a reusable, local simulator for timed
candidate attempts.

The simulator must make a candidate's state visible and recoverable without
changing their solution: every attempt has a fixed assessment copy, a
machine-readable lifecycle record, an append-only audit trail, a generated
human/agent status view, and a separate coaching surface. A full run mirrors
the documented 90-minute assessment; an accelerated drill shortens the clock
while retaining level-by-level feedback.

## Why This Matters

The current explore artifact already contains a strong single-assessment
harness, but its command interface is fragmented and its state is mostly
ephemeral. `new_attempt.py` creates `attempts/<timestamp>[_<name>]/attempt.json` once, while
`scorecard.py --json` prints results without persisting a resumable session
model. As a result, an interrupted candidate or terminal agent has no
authoritative status, safe collaboration boundary, or lifecycle history.

A private, self-contained project converts the preparation material into an
asset that can be reused before future assessments rather than reconstructed
from one-off scripts. It preserves the assessment's instructional value:
partial credit rewards completed levels, visible tests are distinguished from
the written specification, and coaching never contaminates the candidate's
workspace.

## Success Criteria

1. The private repository contains the complete meaningful source inventory
   from `workflow/explore/codesignal-industry-coding-framework`, with
   assessment provenance preserved and generated environments, caches, and
   personal attempts excluded.
2. A candidate can use documented `start`, `resume`, `status`, `time`,
   `task`, `test`, and `submit` commands for isolated full and drill sessions.
3. Each attempt persists validated state, appends structured events, reports
   per-level and contiguous-reach partial credit, and produces a generated
   `STATUS.md` plus machine-readable context output.
4. `COACHING.md` and `AGENTS.md` give terminal agents a candidate-safe working
   surface; the simulator never reads coaching material as candidate code or
   writes to the candidate solution.
5. Unit, integration, migration-regression, and command-level end-to-end tests
   pass from a clean clone, and the JobSearch superproject records the new
   private repository as a submodule.
