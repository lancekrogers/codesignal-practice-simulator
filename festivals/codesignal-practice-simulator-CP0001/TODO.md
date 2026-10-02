# Festival TODO - codesignal-practice-simulator

**Goal**: Plan a private, reusable CodeSignal Industry Coding Framework
simulator that safely migrates the existing `file_storage` practice project
and provides durable full/drill candidate sessions.
**Status**: Planning — source and requirements ingest in progress

---

## Festival Progress Overview

### Phase Completion Status

- [ ] 001_INGEST — Complete requirements, constraints, purpose, and
      source-anchor specifications from the approved objective and inspection.
- [ ] 002_PLAN — Finalize decisions, task hierarchy, command/state contracts,
      test strategy, and execution plan.
- [ ] 003_BOOTSTRAP_MIGRATE — Later create the private repository, migrate
      verified sources, and register the campaign submodule.
- [ ] 004_SESSION_RUNTIME — Later implement isolated attempt state, events,
      timing, status/context, and coaching boundaries.
- [ ] 005_CLI_WORKFLOWS — Later implement and document candidate/agent
      commands and lifecycle errors.
- [ ] 006_VERIFICATION — Later add migration, unit, integration, and
      end-to-end verification.
- [ ] 007_REVIEW_RELEASE — Later perform quality, provenance/privacy,
      usability, and campaign release review.

### Current Work Status

```
Active Phase: 001_INGEST
Active Sequences: N/A — ingest uses a workflow
Blockers: None — scope, repository identity, migration boundary, and
five-phase delivery/review shape are approved
```

---

## Phase Progress

### 001_INGEST — Source and Requirement Ingest

**Status**: In Progress

#### Sequences

- [ ] Read approved objective and all input materials
- [ ] Extract purpose, requirements, constraints, and source context
- [ ] Create and review structured output specifications
- [ ] Record the approval and transition to architecture planning

---

## Blockers

None currently.

---

## Decision Log

- The first release is a private Python 3.10+ `file_storage` simulator with a
  standard-library runtime; existing fixture dependencies remain explicit.
- Full mode is a real 90-minute session; drill mode is an explicit,
  persisted accelerated profile rather than a relabeled full assessment.
- `session.json` is authoritative, `events.jsonl` is append-only history, and
  `STATUS.md`/context are derived views.
- Candidate evaluation is isolated from non-executable `COACHING.md`; live
  terminal-agent limits are documented in `AGENTS.md`.

---

*Detailed progress available via `fest status`*
