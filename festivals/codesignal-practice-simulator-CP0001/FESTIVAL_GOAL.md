---
fest_type: festival
fest_id: CP0001
fest_name: codesignal-practice-simulator
fest_status: completed
fest_created: 2026-09-08T14:45:08.807621-06:00
fest_updated: 2026-09-09T02:42:37.785583-06:00
fest_tracking: true
---




# codesignal-practice-simulator

**Status:** Planned | **Created:** 2026-09-08T14:45:08-06:00

## Festival Objective

**Primary Goal:** Establish and plan a durable private CodeSignal practice
simulator repository that migrates the existing file-storage framework and
adds reliable, agent-safe timed-session workflows.

**Vision:** A candidate can start a realistic 90-minute assessment or an
accelerated drill from a clean clone, work only in a private attempt
workspace, and receive partial-credit feedback by level. Authoritative JSON
state and append-only events make a live session resumable, while derived
status/context documents and separate coaching guidance let terminal agents
help without editing the candidate's solution. The project remains private,
provenance-aware, independently testable, and discoverable through the
JobSearch campaign submodule.

## Success Criteria

### Functional Success

- [ ] The private repository is created at
      `lancekrogers/codesignal-practice-simulator`, contains the verified
      meaningful source migration, and is registered as
      `projects/codesignal-practice-simulator`.
- [ ] `codesignal-sim start`, `resume`, `status`, `time`, `task`, `test`, and
      `submit` run full and drill attempts with deterministic human and JSON
      output.
- [ ] Every attempt isolates candidate files, persists a validated
      `session.json`, appends `events.jsonl`, renders `STATUS.md`, and reports
      individual level results plus contiguous reach.
- [ ] `COACHING.md`, `AGENTS.md`, and `context` establish the operational
      collaboration boundary without affecting candidate evaluation.

### Quality Success

- [ ] All migrated legacy tests plus new unit, CLI integration, and
      end-to-end lifecycle tests pass from a clean checkout; fixture integrity
      and migration-manifest checks have zero mismatches.
- [ ] `fest validate` reports no unfilled markers and every implementation
      sequence contains customized testing, review, iteration, and commit
      gates.

## Progress Tracking

### Phase Completion

- [ ] 001_INGEST: Convert the approved objective and inspected source into
      requirements, constraints, purpose, and source-anchor specifications.
- [ ] 002_PLAN: Decide architecture and publish executable migration,
      simulator, command, test, and review task specifications.
- [ ] 003_BOOTSTRAP_MIGRATE: Create the private repository later, migrate the
      verified source, and integrate the campaign submodule.
- [ ] 004_SESSION_RUNTIME: Implement isolated stateful full/drill sessions,
      event history, status/context, and collaboration boundaries.
- [ ] 005_CLI_WORKFLOWS: Deliver and document the candidate/agent command
      interface with durable lifecycle semantics.
- [ ] 006_VERIFICATION: Add regression, unit, integration, and end-to-end
      evidence for source fidelity and simulator behavior.
- [ ] 007_REVIEW_RELEASE: Review provenance, privacy, usability, quality,
      campaign integration, and release readiness.

## Complete When

- [ ] All phases completed
- [ ] The new private repository and its JobSearch submodule have passed
      clean-clone verification, all review findings are resolved or accepted,
      and the former exploration location is retired only after checksum-based
      transfer verification.
