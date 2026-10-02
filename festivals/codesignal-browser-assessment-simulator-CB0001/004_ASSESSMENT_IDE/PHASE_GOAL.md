---
fest_type: phase
fest_id: 004_ASSESSMENT_IDE
fest_name: ASSESSMENT_IDE
fest_parent: codesignal-browser-assessment-simulator-CB0001
fest_order: 4
fest_status: completed
fest_created: 2026-09-09T03:12:58.60366-06:00
fest_phase_type: implementation
fest_tracking: true
---

# Phase Goal: Assessment IDE

**Phase:** 004_ASSESSMENT_IDE | **Status:** Completed | **Type:** Implementation

## Phase Objective

**Primary Goal:** Build the offline browser candidate experience on the phase-003 contracts: explicit entry, server-authoritative timed shell, bundled Monaco Python editing, source recovery/history, assessment actions, accessibility, and safe terminal-agent continuity.

**Context:** This phase consumes the public application and fixed API without duplicating lifecycle or scoring logic. It produces the feature-complete UI that phase 005 can exercise in a real browser, while keeping editor preferences client-local and keeping coaching outside the candidate screen.

## Required Outcomes

Deliverables this phase must produce:

- [x] A locked `webui/` build workspace that produces self-hosted Monaco and worker assets, records MIT provenance, and copies only generated browser assets into the Python package.
- [x] Entry and shell modules that render bootstrap metadata, explicit full/drill start, top-bar timer/save state, four-level navigation, prompt tabs, editor/output panes, actions, and recoverable error/final screens.
- [x] Editor/action modules that implement Python Monaco settings, debounced ETag autosave, conflict recovery, source history/restore/reset, prompt tabs, test output, submit confirmation, expiry locking, and final-result rendering.
- [x] Accessibility and continuity behavior verified through keyboard paths, focus/live-region behavior, responsive layout, and refreshed safe `STATUS.md`/context surfaces.

## Quality Standards

Quality criteria for all work in this phase:

- [x] The client treats server session/time/score snapshots as authoritative and never pauses, extends, resets, or manufactures lifecycle state.
- [x] All candidate mutations preserve the source ETag conflict contract; no save, test, or submit silently overwrites an intervening edit.
- [x] Runtime assets load from package resources with no CDN or network request, and UI text distinguishes local practice checks from official hidden tests.
- [x] Keyboard access, visible focus, dialog focus containment, reduced motion, responsive narrow-laptop layout, and bounded error rendering are tested.

## Sequence Alignment

| Sequence | Goal | Key Deliverable |
|----------|------|-----------------|
| 01_editor_assets | Build reproducible, licensed, packageable Monaco assets for offline runtime. | `webui/package-lock.json`, build outputs, provenance notice, package-data manifest |
| 02_entry_and_shell | Establish entry/start semantics and the responsive assessment shell. | `webui/src/app.ts`, shell views/styles, loading/error/final states |
| 03_editor_and_assessment_actions | Connect editing, source history, prompts, tests, navigation, submit, and expiry to the API. | editor/action/state modules and interaction tests |
| 04_agent_continuity | Keep safe terminal surfaces aligned with browser actions and document the coaching boundary. | rendering/agent guidance updates and continuity verification |

## Pre-Phase Checklist

Before starting implementation:

- [x] Phase 003 API schemas, source CAS behavior, and loopback security tests pass
- [x] D003 Monaco 0.56.0, its license, worker strategy, and package-data boundary are accepted
- [x] Node/npm and the locked browser build toolchain are available for asset generation
- [x] UI work uses synthetic or copied candidate-facing prompts only; no FETCH_ONLY bytes enter `webui/`

## Phase Progress

### Sequence Completion

- [x] 01_editor_assets — reproducible offline Monaco bundle
- [x] 02_entry_and_shell — entry flow and responsive shell
- [x] 03_editor_and_assessment_actions — editor and assessment actions
- [x] 04_agent_continuity — terminal coaching continuity

## Notes

Planned frontend paths are `webui/src/app.ts`, `webui/src/api.ts`, `webui/src/state.ts`, `webui/src/editor.ts`, `webui/src/views.ts`, `webui/src/a11y.ts`, and `webui/src/styles.css`; generated runtime files land under `src/codesignal_practice_simulator/web/static/`. The UI may use local storage only for non-authoritative editor preferences. It must not copy CodeSignal branding, page source, assets, hidden-test claims, candidate source into coaching, or assessment reference material into static assets.

---
