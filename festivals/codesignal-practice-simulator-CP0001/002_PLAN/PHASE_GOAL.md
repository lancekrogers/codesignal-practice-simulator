---
fest_type: phase
fest_id: 002_PLAN
fest_name: PLAN
fest_parent: codesignal-practice-simulator-CP0001
fest_order: 2
fest_status: completed
fest_created: 2026-09-08T14:45:08.826175-06:00
fest_updated: 2026-09-08T17:55:47.943343-06:00
fest_phase_type: planning
fest_tracking: true
---


# Phase Goal: Architecture and Executable Delivery Plan

**Phase:** 002_PLAN | **Status:** Pending | **Type:** Planning

## Phase Objective

**Primary Goal:** Plan architecture, design decisions, and task breakdown

**Context:** The target moves a single-assessment explore artifact into a
private campaign project and adds durable session semantics. Planning is
required to enforce the no-license FETCH_ONLY boundary, migrate only
non-verbatim user-authored material, define candidate/agent boundaries, and
give implementation workers executable tasks with unambiguous verification.

## Exploration Topics

What areas need to be explored during this phase:

- Repository bootstrap, private GitHub creation, source provenance, checksum
  verification, and JobSearch submodule registration
- Python package/CLI layout, assessment registry seam, and compatibility with
  existing Just recipes and fixture dependencies
- Attempt filesystem layout, lifecycle state machine, atomic JSON persistence,
  append-only events, locking, current-attempt selection, and clock injection
- Full versus drill profiles, per-level independent test execution, partial
  credit, contiguous reach, submit finality, and error/exit-code contracts
- Generated `STATUS.md`, Markdown/JSON context, `COACHING.md`, and live-session
  `AGENTS.md` boundaries that never alter candidate evaluation
- Regression, unit, integration, end-to-end, provenance/privacy, and
  clean-clone review evidence

## Key Questions to Answer

Questions that must be answered before this phase is complete:

- How can fetch-only fixture fidelity and candidate-safe coaching coexist?
  Keep the validated ignored cache and candidate files isolated from
  reference/study material;
  generate status from structured state; make coaching non-executable and
  operationally scoped in `AGENTS.md`.
- How should an interrupted session resume safely? Make per-attempt
  `session.json` authoritative, update it atomically behind a lock, use an
  explicit active-session pointer, and append immutable command outcome events.
- How should the source's rollback contradiction be treated? Retain the
  bundled fixture behavior for candidate scoring and preserve the
  specification-correct reference tests as a separate documented validation
  profile.

## Expected Documents

Documents that will be produced during this phase:

- `plan/STRUCTURE.md` — dependency-aware phase, sequence, task, and gate
  hierarchy with source anchors and ownership boundaries
- `plan/IMPLEMENTATION_PLAN.md` — tutorial-grade execution order, contracts,
  verification commands, migration safety steps, and completion evidence
- `decisions/D001_repository_and_campaign_integration.md` — private remote,
  provenance, migration, and submodule decision
- `decisions/D002_python_package_and_cli.md` — package layout, commands,
  compatibility, and dependency decision
- `decisions/D003_session_state_and_agent_boundary.md` — state/events,
  workspace/lifecycle, status/coaching, and safety decision
- `decisions/D004_agent_safe_coaching.md` — agent-safe coaching and evaluation
  boundary

## Success Criteria

This planning phase is complete when:

- [ ] Every approved requirement is traceable to an executable implementation
      task, acceptance test, migration check, or review criterion.
- [ ] Every phase, sequence, task, and quality gate has a concrete purpose,
      dependencies, source anchors, commands, failure cases, and definition
      of done; no unresolved boilerplate remains.
- [ ] Implementation can begin without creating ambiguity about source
      ownership, candidate/agent permissions, persistence authority, testing,
      repository privacy, or campaign integration.

## Notes

The approved first release remains focused on `file_storage`; a registry seam
is planned but no new assessment is invented. The canonical command is
`codesignal-sim`, with `python -m` equivalence; Just recipes are compatibility
shortcuts. Full mode is exactly 90 minutes and drill mode defaults to 30
minutes while recording its duration. The external repository and product code
remain untouched until planning is complete.

The factual operator approval record is
[`inputs/operator_approval.md`](inputs/operator_approval.md). It records the
approved repository, campaign destination, full migration scope, five-phase
plan, completion directive, checkpoint delegation, and the incorporation of
subsequent judge-feedback remediation passes.

## Approved phase order

1. `001_INGEST` establishes requirements and migration constraints.
2. `002_PLAN` records architecture, dependencies, and executable tasks.
3. `003_BOOTSTRAP_MIGRATE` creates and verifies the private project.
4. `004_SESSION_RUNTIME` builds durable attempt state and scoring.
5. `005_CLI_WORKFLOWS` exposes candidate and terminal-agent commands.
6. `006_VERIFICATION` proves lifecycle and clean-clone behavior.
7. `007_REVIEW_RELEASE` performs final readiness review.

The command results and goal alignment for this ordering are recorded in
[`plan/validation-evidence.md`](plan/validation-evidence.md).
