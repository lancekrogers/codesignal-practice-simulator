# Festival Overview: codesignal-browser-assessment-simulator

## Problem Statement

**Current State:** The private project has a tested terminal simulator with a
durable four-level engine, but it does not rehearse the browser layout, editor,
navigation, timing pressure, or submission interactions of a CodeSignal test.

**Desired State:** One local command opens a secure, offline-capable browser IDE
that closely mirrors the consequential CodeSignal candidate flow while calling
the existing engine and synchronizing safe terminal coaching surfaces.

**Why This Matters:** The user has a real assessment soon and needs muscle-memory
practice that is more representative than CLI commands, while retaining a tool
that remains useful for future timed rehearsals and agent-assisted coaching.

## Scope

### In Scope

- Public shared application composition and candidate-document/history service
- Capability-scoped loopback HTTP server and fixed safe JSON API
- Locally bundled Monaco editor and CodeSignal-like assessment shell
- Full/drill start, server timer, levels/tabs, autosave/reset/history, test,
  submit/expiry/final states, refresh/restart recovery
- Terminal-agent derived status/coaching continuity
- Unit, HTTP/security, Playwright, package, offline, and clean-clone verification

### Out of Scope

- CodeSignal branding, proprietary assets/page source, or official-hidden-test
  claims
- Hosted accounts, cloud workspaces, invitations, proctoring, or collaboration
- Additional languages/assessments and arbitrary browser shell execution
- Keystroke surveillance or silent agent edits to candidate source

## Planned Phases

### 001_INGEST — Requirements intake

Capture the approved candidate experience, current official interaction
references, existing engine boundaries, constraints, and exclusions.

### 002_PLAN — Architecture and execution

Resolve design gaps, record decisions, and scaffold detailed executable work.

### 003_APPLICATION_FOUNDATION — Trusted backend

Share production composition, own candidate documents, and expose the secure
loopback API.

### 004_ASSESSMENT_IDE — Browser candidate experience

Bundle Monaco and build the entry, IDE, actions, recovery, accessibility, and
agent-continuity interactions.

### 005_BROWSER_VERIFICATION — Confidence and distribution

Exercise the real browser journeys and prove installed/offline/private-clone
operation.

### 006_RELEASE_REVIEW — Independent acceptance

Use Cursor and local judges to challenge and remediate the completed tool before
publishing project and campaign state.

## Notes

The browser is local and single-user. The existing server-side lifecycle and
scorer remain the only source of truth. See `002_PLAN/decisions/` for accepted
tradeoffs and `002_PLAN/plan/IMPLEMENTATION_PLAN.md` for task ordering.
