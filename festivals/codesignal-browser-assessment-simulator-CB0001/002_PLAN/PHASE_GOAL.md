---
fest_type: phase
fest_id: 002_PLAN
fest_name: PLAN
fest_parent: codesignal-browser-assessment-simulator-CB0001
fest_order: 2
fest_status: completed
fest_created: 2026-09-09T02:42:54.50554-06:00
fest_updated: 2026-09-09T03:27:10.041251-06:00
fest_phase_type: planning
fest_tracking: true
---


# Phase Goal: Browser Application Architecture and Execution Plan

**Phase:** 002_PLAN | **Status:** Completed | **Type:** Planning

## Phase Objective

**Primary Goal:** Plan architecture, design decisions, and task breakdown

**Context:** The existing CLI simulator is already durable and tested, but a
browser IDE adds source-edit concurrency, local HTTP security, frontend asset
packaging, asynchronous lifecycle interactions, and real-browser verification.
These boundaries must be settled before implementation begins.

## Exploration Topics

What areas need to be explored during this phase:

- Existing service composition and reusable lifecycle/scoring boundaries
- Candidate-source ownership, optimistic concurrency, history, and reset
- Loopback HTTP capability, route schemas, and content isolation
- Offline Monaco asset build, licensing, packaging, and CSP
- Browser state machine, accessibility, fidelity, and failure recovery
- Playwright, wheel, clean-clone, and terminal-agent verification

## Key Questions to Answer

Questions that must be answered before this phase is complete:

- How can CLI and browser share exactly one production application graph?
- Which service exclusively owns `simulation.py` and its source history?
- How are autosave, test, timeout, and submit races resolved coherently?
- Which fixed API surface provides the UI without exposing arbitrary files?
- How are Monaco and workers bundled reproducibly for offline wheel installs?
- Which real-browser journeys prove assessment fidelity and coaching continuity?

## Expected Documents

Documents that will be produced during this phase:

- `inputs/gaps.md` — resolved gaps, decisions, risks, and evidence
- `decisions/D001` through `D005` — accepted architecture decisions
- `plan/STRUCTURE.md` — festival/phase/sequence/task hierarchy
- `plan/IMPLEMENTATION_PLAN.md` — exact files, ordering, verification, release

## Success Criteria

This planning phase is complete when:

- [x] Every B01-B25 requirement or exclusion maps to a planned phase
- [x] Significant architecture choices include alternatives and consequences
- [x] No unresolved product question requires interrupting the user
- [x] Implementation is decomposed into atomic, testable, judgeable work
- [x] Festival implementation/review phases are scaffolded with no markers
- [x] Festival validates and quality gates are applied

## Notes

The user delegated routine decisions to Cursor agents and the local judge. The
accepted plan uses Monaco for fidelity, a standard-library loopback server for
runtime simplicity, and one dedicated file-backed candidate-document service.
Implementation evidence may supersede a decision, but cannot silently relax the
ingest contract.

---

*Planning phases use freeform structure. Create topic directories as needed.*
