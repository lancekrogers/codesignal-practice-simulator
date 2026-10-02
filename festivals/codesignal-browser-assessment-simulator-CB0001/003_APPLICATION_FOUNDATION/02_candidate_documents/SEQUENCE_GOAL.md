---
fest_type: sequence
fest_id: 02_candidate_documents
fest_name: candidate documents
fest_parent: 003_APPLICATION_FOUNDATION
fest_order: 2
fest_status: completed
fest_created: 2026-09-09T03:13:06.865454-06:00
fest_updated: 2026-09-09T04:58:20.077985-06:00
fest_tracking: true
---


# Sequence Goal: 02_CANDIDATE_DOCUMENTS

**Sequence:** 02_CANDIDATE_DOCUMENTS | **Phase:** 003_APPLICATION_FOUNDATION | **Status:** Pending

## Sequence Objective

**Primary Goal:** Make one locked file-backed service the sole owner of the registered candidate source, its SHA-256 CAS revisions, bounded predecessor history, reset baseline, and restore behavior.

**Contribution to Phase Goal:** This supplies safe durable source operations to API mutations and scoring while keeping lifecycle revisions/events independent from candidate-source revisions.

## Success Criteria

The sequence goal is achieved when:

### Required Deliverables

- [ ] **Candidate document contract**: `src/codesignal_practice_simulator/candidate_documents.py` defines immutable document/snapshot/history records and stable errors for conflict, unsafe files, invalid UTF-8, oversized content, and read-only attempts.
- [ ] **Atomic CAS service**: Reads and writes only the registry-derived `simulation.py` under `Persistence.attempt_lock`, with `If-Match`-equivalent ETags and predecessor snapshots.
- [ ] **Recovery and invariant tests**: Failure-injection, concurrency, symlink, expiry, submission, legacy-baseline, reset, and restore tests prove predecessor recoverability and bounded retention.

### Quality Standards

- [ ] **Source ownership**: No handler accepts a filesystem path or directly mutates candidate files.
- [ ] **Crash safety**: A successful replacement has a recoverable predecessor, and orphan snapshots are harmless and deduplicated.

### Completion Criteria

- [ ] All tasks in sequence completed successfully
- [ ] Focused verification tasks passed
- [ ] Independent review findings addressed
- [ ] Relevant documentation updated

## Task Alignment

| Task | Task Objective | Contribution to Sequence Goal |
|------|----------------|-------------------------------|
| 01_define_document_contracts_and_initial_source.md | Define records, errors, limits, and the reset baseline at attempt creation. | Fixes the service contract before mutation code. |
| 02_implement_candidate_read_and_cas_save.md | Implement locked read and optimistic-concurrency saves. | Provides safe autosave and scoring snapshots. |
| 03_implement_source_history_reset_and_restore.md | Add bounded history, preview, restore, and reset through the CAS path. | Completes recovery behavior for the IDE. |
| 04_verify_document_safety_and_recovery.md | Exercise races, interruption boundaries, malformed inputs, and final-state guards. | Proves candidate-source invariants before HTTP exposure. |

## Dependencies

### Prerequisites

- 01_RUNTIME_COMPOSITION public application graph

### Provides

- `CandidateDocumentService` used by `src/codesignal_practice_simulator/web/routes.py` for every source mutation

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Filesystem failure leaves source and history inconsistent | High | High | Use existing atomic filesystem/persistence primitives, write predecessor before replacement, inject failures at each boundary, and reconcile duplicate snapshots by hash. |

## Progress Tracking

### Milestones

- [ ] **Milestone 1**: Typed contract and initial-source baseline exist
- [ ] **Milestone 2**: CAS save and atomic predecessor history work
- [ ] **Milestone 3**: Reset/restore and failure-injection tests pass

## Quality Gates

### Testing and Verification

- [ ] Focused unit/API/browser tests pass
- [ ] Integration evidence is recorded
- [ ] Performance/resource impact is assessed where relevant

### Code Review

- [ ] Independent review is conducted
- [ ] Review feedback is addressed
- [ ] Festival rules and content boundaries are verified

### Iteration Decision

- [ ] Need another iteration? No; create targeted follow-up tasks only if execution evidence identifies a defect or unmet criterion.
- [ ] If yes, new tasks created: None at planning time; record exact task paths when evidence requires iteration.
