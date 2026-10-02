---
fest_type: festival
fest_id: CB0001
fest_name: codesignal-browser-assessment-simulator
fest_status: dungeon/completed
fest_created: 2026-09-09T02:42:54.484549-06:00
fest_updated: 2026-09-10T17:20:52.107767-06:00
fest_tracking: true
---




# codesignal-browser-assessment-simulator

**Status:** Planned | **Created:** 2026-09-09T02:42:54-06:00

## Festival Objective

**Primary Goal:** Extend the existing private CodeSignal practice simulator into a local browser assessment application that closely reproduces the current CodeSignal candidate flow and IDE interaction while preserving FETCH_ONLY provenance, isolated scoring, terminal-agent coaching boundaries, and deterministic offline operation.

**Vision:** The user launches one local command and enters a polished browser
assessment that feels spatially and behaviorally familiar to CodeSignal while
remaining honest about its first-party practice tests. The browser and terminal
surfaces observe the same durable attempt, allowing safe live coaching without
silently changing candidate work.

## Success Criteria

### Functional Success

- [ ] Explicit entry/start, one-sitting countdown, four-level navigation, prompt
  tabs, realistic Python editing, autosave/history/reset, test, submit, expiry,
  refresh/restart recovery, and final results all work in a real browser.
- [ ] Existing CLI, FETCH_ONLY fixture, lifecycle, isolated scorer, and
  terminal-agent safety behavior remain authoritative and backward compatible.
- [ ] Editable and installed-wheel browser launches work without runtime network
  access or proprietary CodeSignal assets/content.

### Quality Success

- [ ] Existing 158-test baseline plus new unit, HTTP, security, packaging, and
  Playwright candidate-journey tests pass.
- [ ] Candidate writes are atomic/CAS guarded, final actions are idempotent, and
  security tests prove loopback/token/Origin/body/path/content boundaries.
- [ ] Keyboard-only and narrow-laptop flows are usable; independent Cursor and
  local judge reviews have no unresolved material findings.

## Progress Tracking

### Phase Completion

- [x] 001_INGEST: approved, traceable browser requirements
- [ ] 002_PLAN: accepted architecture and executable festival plan
- [ ] 003_APPLICATION_FOUNDATION: shared runtime, source service, secure API
- [ ] 004_ASSESSMENT_IDE: offline Monaco candidate experience and coaching sync
- [ ] 005_BROWSER_VERIFICATION: Playwright, packaging, docs, clean-clone proof
- [ ] 006_RELEASE_REVIEW: independent review, remediation, and private release

## Complete When

- [ ] All phases completed
- [ ] The private project and campaign remotes reference the verified release
- [ ] No FETCH_ONLY content, secret, attempt data, trace, or dependency cache is
  present in Git history
