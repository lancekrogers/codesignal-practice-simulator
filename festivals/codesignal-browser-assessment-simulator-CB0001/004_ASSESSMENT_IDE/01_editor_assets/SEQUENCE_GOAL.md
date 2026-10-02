---
fest_type: sequence
fest_id: 01_editor_assets
fest_name: editor assets
fest_parent: 004_ASSESSMENT_IDE
fest_order: 1
fest_status: completed
fest_created: 2026-09-09T03:13:07.108523-06:00
fest_updated: 2026-09-09T09:50:50.328591-06:00
fest_tracking: true
---


# Sequence Goal: 01_EDITOR_ASSETS

**Sequence:** 01_EDITOR_ASSETS | **Phase:** 004_ASSESSMENT_IDE | **Status:** Completed

## Sequence Objective

**Primary Goal:** Build and package a reproducible, license-compatible Monaco Python editor bundle and workers that load from the wheel under the restrictive offline server policy.

**Contribution to Phase Goal:** The shell and editor actions cannot satisfy the IDE requirement until all runtime assets have a declared provenance, deterministic build, package-data inclusion, and same-origin worker strategy.

## Success Criteria

The sequence goal is achieved when:

### Required Deliverables

- [x] **Locked frontend workspace**: `webui/package.json` and `package-lock.json` lock Monaco 0.56.0, esbuild, and Playwright tooling with scripts and provenance.
- [x] **Generated package assets**: `webui/build.mjs` emits application/worker assets and an explicit manifest under `src/.../web/static/` without assessment bytes.
- [x] **Offline/package verification**: Build and wheel checks prove all assets, notices, CSP worker paths, and editable/wheel loading work without Node or network at runtime.

### Quality Standards

- [x] **Reproducibility**: A clean lockfile install rebuilds the declared asset manifest without undeclared inputs.
- [x] **License/content boundary**: MIT notices are shipped; FETCH_ONLY prompts/tests/vendor bytes never enter `webui/` or static output.

### Completion Criteria

- [x] All tasks in sequence completed successfully
- [x] Focused verification tasks passed
- [x] Independent review findings addressed
- [x] Relevant documentation updated

## Task Alignment

| Task | Task Objective | Contribution to Sequence Goal |
|------|----------------|-------------------------------|
| 01_lock_editor_toolchain_and_provenance.md | Create the locked build workspace and provenance record. | Makes asset inputs auditable. |
| 02_build_packaged_monaco_assets.md | Bundle Monaco, workers, application source, and package manifest. | Creates the offline runtime artifact. |
| 03_verify_offline_reproducible_assets.md | Check rebuild determinism, wheel contents, CSP, and network denial. | Proves assets are releasable. |

## Dependencies

### Prerequisites

- 003_LOCAL_WEB_API static-resource contract and D003

### Provides

- Packaged browser assets consumed by `src/codesignal_practice_simulator/web/resources.py` and `webui/src/editor.ts`

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Worker URLs or package-data rules differ between editable and wheel installs | Medium | High | Use fingerprinted manifest entries, wheel inspection, and a network-denied smoke load from both installation modes. |

## Progress Tracking

### Milestones

- [x] **Milestone 1**: Lockfile/provenance/license files committed
- [x] **Milestone 2**: Bundle and worker manifest generated
- [x] **Milestone 3**: Editable/wheel offline asset checks pass

## Quality Gates

### Testing and Verification

- [x] Focused unit/API/browser tests pass
- [x] Integration evidence is recorded
- [x] Performance/resource impact is assessed where relevant

### Code Review

- [x] Independent review is conducted
- [x] Review feedback is addressed
- [x] Festival rules and content boundaries are verified

### Iteration Decision

- [x] Need another iteration? No; all identified findings were resolved in the recorded iteration.
- [x] Follow-up tasks required: None.
