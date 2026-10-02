---
fest_type: sequence
fest_id: 01_runtime_composition
fest_name: runtime composition
fest_parent: 003_APPLICATION_FOUNDATION
fest_order: 1
fest_status: completed
fest_created: 2026-09-09T03:13:06.733371-06:00
fest_updated: 2026-09-09T03:52:01.029633-06:00
fest_tracking: true
---


# Sequence Goal: 01_RUNTIME_COMPOSITION

**Sequence:** 01_RUNTIME_COMPOSITION | **Phase:** 003_APPLICATION_FOUNDATION | **Status:** Pending

## Sequence Objective

**Primary Goal:** Expose one public, dependency-injected runtime application graph that both the existing CLI and the future web adapter can call without behavior or exit-code drift.

**Contribution to Phase Goal:** This establishes the trusted composition boundary required by the candidate-document service and HTTP adapter; later layers depend on its registry, workspace, clock, lifecycle, evaluation, prompts, context, derived status, and scorer collaborators.

## Success Criteria

The sequence goal is achieved when:

### Required Deliverables

- [ ] **Public application container**: `src/codesignal_practice_simulator/application.py` defines `RuntimeApplication` and `create_application()` with injectable workspace root, clock, registry, filesystem/persistence seams, and scorer construction.
- [ ] **Thin CLI integration**: `cli.py` imports the public factory, keeps `CommandApplication`, parsing, serialization, dispatch, and existing command behavior intact.
- [ ] **Compatibility evidence**: Composition and real-process tests prove the current commands, envelopes, exits, selected attempts, derived status, and scorer wiring remain stable.

### Quality Standards

- [ ] **Single authority**: No browser or CLI adapter duplicates lifecycle, prompt, scoring, persistence, or workspace policy.
- [ ] **Testable dependencies**: Temporary workspaces, fake clocks, registries, and scorer seams can be injected without global state.

### Completion Criteria

- [ ] All tasks in sequence completed successfully
- [ ] Focused verification tasks passed
- [ ] Independent review findings addressed
- [ ] Relevant documentation updated

## Task Alignment

| Task | Task Objective | Contribution to Sequence Goal |
|------|----------------|-------------------------------|
| 01_characterize_runtime_composition.md | Record the current object graph, adapter contract, and behavior before extraction. | Defines the regression surface for the public container. |
| 02_extract_public_application_container.md | Move composition into `src/codesignal_practice_simulator/application.py` and update the CLI to use it. | Creates the shared backend foundation. |
| 03_verify_cli_compatibility.md | Run focused and baseline compatibility checks across supported entry points. | Proves extraction did not alter the trusted CLI. |

## Dependencies

### Prerequisites

- 002_PLAN accepted D001 and the existing CLI/service tests

### Provides

- A public runtime factory used by candidate documents and `src/codesignal_practice_simulator/web/server.py`

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Private CLI dependencies are missed during extraction | Medium | High | Characterize imports and behavior first; keep CLI dispatch thin and run baseline process tests immediately. |

## Progress Tracking

### Milestones

- [ ] **Milestone 1**: Dependency graph and regression matrix recorded
- [ ] **Milestone 2**: Public container and factory imported by CLI
- [ ] **Milestone 3**: Baseline suite and console/module smoke flows pass

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
