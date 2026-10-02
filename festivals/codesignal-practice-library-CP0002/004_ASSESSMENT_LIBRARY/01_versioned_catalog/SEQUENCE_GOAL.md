---
fest_type: sequence
fest_id: 01_versioned_catalog
fest_name: versioned_catalog
fest_parent: 004_ASSESSMENT_LIBRARY
fest_order: 1
fest_status: completed
fest_created: 2026-09-11T14:32:06.95712-06:00
fest_updated: 2026-09-12T20:20:31.083324-06:00
fest_tracking: true
fest_working_dir: projects/worktrees/codesignal-practice-simulator/cp0002-practice-library
---


# Sequence Goal: 01_versioned_catalog

**Sequence:** 01_versioned_catalog | **Phase:** 004_ASSESSMENT_LIBRARY | **Status:** Pending | **Created:** 2026-09-11T14:32:06-06:00

## Sequence Objective

**Primary Goal:** Extend assessment registry with validated input providers and registry-driven catalog/distribution replacing hardcoded enumeration.

**Contribution to Phase Goal:** Enables offline originals and honest review when definitions are removed (R1/R8/R11) before content authoring in 02.

## Success Criteria

The sequence goal is achieved when:

### Required Deliverables

- [ ] **Input providers:** pinned-fetched and packaged-original at `assessments.py:56/:88`, `workspace.py:116/:329`, `application.py:343`.
- [ ] **Catalog/distribution:** Replace `application.py:174` hardcoded list; extend `pyproject.toml` resources and packaging checks.

### Quality Standards

- [ ] **Validation before staging:** Missing/tampered resources rejected before attempt or restart commit intent.
- [ ] **Legacy unchanged:** File Storage cache validation behavior preserved for fetched assessments.

### Completion Criteria

- [ ] All tasks in sequence completed successfully
- [ ] Quality verification tasks passed
- [ ] Code review completed and issues addressed
- [ ] Documentation updated

## Task Alignment

| Task | Task Objective | Contribution to Sequence Goal |
|------|----------------|-------------------------------|
| 01_input_providers | Provider boundary and pinning | Safe attempt creation inputs |
| 02_catalog_and_distribution | Registry catalog and packaging | Discovery offline and via CLI/HTTP |

## Dependencies

### Prerequisites (from other sequences)

- **003/01_schema_and_review:** Content identity fields, File Storage identity derivation, and active v2 creation (003/01/02_creation_identity); this sequence generalizes them into providers.

### Provides (to other sequences)

- **Catalog and providers:** Used by 02_original_content and 005 library UI.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Oracle files shipped in wheel | Med | High | Allowlist scan in packaging tests |
| Broken legacy File Storage path | Low | High | Regression tests for fetched assessments |

## Progress Tracking

### Milestones

- [ ] **Milestone 1:** Both provider kinds validated in tests
- [ ] **Milestone 2:** Catalog routes/CLI listing readiness flags
- [ ] **Milestone 3:** Outside-checkout wheel discovery test

## Quality Gates

### Testing and Verification

- [ ] All unit tests pass
- [ ] Integration tests complete
- [ ] Performance benchmarks met

### Code Review

- [ ] Code review conducted
- [ ] Review feedback addressed
- [ ] Standards compliance verified

### Iteration Decision

- [ ] Need another iteration? No
- [ ] If yes, new tasks created: N/A
