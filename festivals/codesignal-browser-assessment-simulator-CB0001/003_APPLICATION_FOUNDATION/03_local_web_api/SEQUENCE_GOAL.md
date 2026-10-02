---
fest_type: sequence
fest_id: 03_local_web_api
fest_name: local web api
fest_parent: 003_APPLICATION_FOUNDATION
fest_order: 3
fest_status: completed
fest_created: 2026-09-09T03:13:06.987727-06:00
fest_updated: 2026-09-09T05:46:23.941598-06:00
fest_tracking: true
---


# Sequence Goal: 03_LOCAL_WEB_API

**Sequence:** 03_LOCAL_WEB_API | **Phase:** 003_APPLICATION_FOUNDATION | **Status:** Pending

## Sequence Objective

**Primary Goal:** Expose the shared application through a small loopback HTTP adapter with fixed JSON routes, packaged static resources, capability authentication, exact mutation Origin checks, and no arbitrary filesystem or command surface.

**Contribution to Phase Goal:** This turns the trusted services into the stable contract consumed by the offline browser while enforcing D004 boundaries before UI code can exist.

## Success Criteria

The sequence goal is achieved when:

### Required Deliverables

- [ ] **Server lifecycle**: `src/codesignal_practice_simulator/web/server.py` launches `ThreadingHTTPServer` on `127.0.0.1`, creates a per-launch token/fragment URL, and shuts down cleanly.
- [ ] **Fixed API and resources**: `src/codesignal_practice_simulator/web/routes.py`, `responses.py`, and `resources.py` implement only the bootstrap/session/time/prompt/source/history/start/test/submit routes and explicit static manifest.
- [ ] **Boundary test suite**: `tests/test_web_server.py` covers schemas, errors, methods, tokens, Origin, body limits, headers, forbidden paths/content, mutations, and shutdown.

### Quality Standards

- [ ] **Transport isolation**: Handlers parse/validate/serialize and call one application method; lifecycle, path, and scoring policy stays in services.
- [ ] **Defensive delivery**: Responses are bounded and schema-versioned; API/state is no-store; HTML CSP and headers deny framing, sniffing, and permissions.

### Completion Criteria

- [ ] All tasks in sequence completed successfully
- [ ] Focused verification tasks passed
- [ ] Independent review findings addressed
- [ ] Relevant documentation updated

## Task Alignment

| Task | Task Objective | Contribution to Sequence Goal |
|------|----------------|-------------------------------|
| 01_implement_web_server_and_cli_launch.md | Add the loopback server, token URL, static manifest loader, and `web` CLI command. | Provides a runnable transport shell. |
| 02_implement_read_api_and_static_serving.md | Implement bootstrap, session/time, prompt, source/history reads, and safe static delivery. | Gives the browser authoritative read snapshots. |
| 03_implement_mutation_api.md | Implement start/save/reset/restore/test/submit envelopes and stable errors. | Connects all state-changing candidate actions. |
| 04_verify_api_security_and_isolation.md | Prove the API boundary, headers, body/path rules, and content isolation. | Prevents UI work from hiding transport defects. |

## Dependencies

### Prerequisites

- 01_RUNTIME_COMPOSITION and 02_CANDIDATE_DOCUMENTS

### Provides

- A stable API consumed by `webui/src/api.ts` and browser verification

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Route adapter leaks internal files or maps races inconsistently | High | High | Use an explicit route table and response mapper; enumerate rejected methods, paths, tokens, origins, and body forms in HTTP tests. |

## Progress Tracking

### Milestones

- [ ] **Milestone 1**: Loopback server and CLI launch work
- [ ] **Milestone 2**: Read routes and static manifest are bounded
- [ ] **Milestone 3**: Mutation routes and security/isolation tests pass

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
