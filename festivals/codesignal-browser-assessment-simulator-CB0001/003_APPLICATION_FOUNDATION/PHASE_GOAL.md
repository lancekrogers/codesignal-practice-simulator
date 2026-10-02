---
fest_type: phase
fest_id: 003_APPLICATION_FOUNDATION
fest_name: APPLICATION_FOUNDATION
fest_parent: codesignal-browser-assessment-simulator-CB0001
fest_order: 3
fest_status: completed
fest_created: 2026-09-09T03:12:58.575944-06:00
fest_updated: 2026-09-09T05:50:36.417714-06:00
fest_phase_type: implementation
fest_tracking: true
---


# Phase Goal: Application Foundation

**Phase:** 003_APPLICATION_FOUNDATION | **Status:** Completed | **Type:** Implementation

## Phase Objective

**Primary Goal:** Deliver the trusted Python application boundary that shares the existing simulator services with the browser, owns candidate source revisions, and exposes only a capability-scoped loopback API.

**Context:** This phase turns the accepted D001, D002, and D004 decisions into executable backend contracts. It must finish before browser UI work because the IDE, timer, source editor, and final actions all depend on one authoritative application graph and one safe candidate-document owner.

## Required Outcomes

Deliverables this phase must produce:

- [x] A public `RuntimeApplication` and `create_application()` in `src/codesignal_practice_simulator/application.py`, with `cli.py` using it without changing existing command envelopes or exit codes.
- [x] A dedicated `src/codesignal_practice_simulator/candidate_documents.py` service that resolves only the registered `simulation.py`, uses SHA-256 ETags and CAS writes, atomically records bounded predecessor history, and implements safe reset/restore.
- [x] A `src/codesignal_practice_simulator/web/` server and fixed JSON API that binds to `127.0.0.1`, requires the per-launch capability, validates mutation Origin, serves packaged resources, and never accepts paths or commands from the browser.
- [x] Unit and HTTP tests covering composition, document invariants, lifecycle races, security headers, request limits, and live-attempt content isolation.

## Quality Standards

Quality criteria for all work in this phase:

- [ ] Existing lifecycle, scoring, prompt, persistence, workspace, and derived-status policies remain authoritative; handlers contain parsing and serialization only.
- [ ] All writes use the existing lock order and atomic primitives, and every new boundary has error cases tested before happy paths.
- [ ] API responses are bounded, deterministic, schema-versioned, and free of filesystem paths, scorer internals, reference bytes, and candidate source unless the fixed source route explicitly requests it.
- [ ] Python 3.10+ and the standard-library runtime remain supported, with no new runtime web framework dependency.

## Sequence Alignment

| Sequence | Goal | Key Deliverable |
|----------|------|-----------------|
| 01_runtime_composition | Share one dependency-injected production graph between CLI and web transports. | `src/codesignal_practice_simulator/application.py` container/factory and CLI regression coverage |
| 02_candidate_documents | Make candidate source, CAS revisions, history, reset, and restore one locked service contract. | `src/codesignal_practice_simulator/candidate_documents.py` plus domain and failure-injection tests |
| 03_local_web_api | Expose the safe application operations through a loopback, capability-scoped HTTP adapter. | `web/` server, fixed routes, static resource loader, and HTTP security tests |

## Pre-Phase Checklist

Before starting implementation:

- [ ] 002_PLAN is accepted, including D001-D005 and `plan/IMPLEMENTATION_PLAN.md`
- [ ] The project baseline and current test commands are known: `python3 -m unittest discover -s tests -v` and `just verify`
- [ ] A synthetic seven-record fixture builder and temporary workspace strategy are available for new tests
- [ ] Implementation uses the existing project worktree; unrelated campaign changes remain untouched

## Phase Progress

### Sequence Completion

- [x] 01_runtime_composition — public application graph and CLI compatibility
- [x] 02_candidate_documents — locked candidate source and recovery service
- [x] 03_local_web_api — capability-scoped loopback API

## Notes

The browser must call service methods rather than shelling out for each action or editing `session.json`, `events.jsonl`, `active.json`, `STATUS.md`, or lock files. Candidate writes are allowed only for selected active, unexpired attempts. The API may expose copied prompts and bounded score data, but never fixture-cache, study, solution, vendor, raw test, or arbitrary filesystem content. Do not add phase quality-gate records yet; keep all implementation and verification work pending until executed.

---
