# Festival Structure

## Festival goal

Deliver a private, local browser assessment application that gives the user a
credible CodeSignal rehearsal: intentional start, one-sitting countdown,
question navigation, realistic Python editing, autosave/history, separate test
and submission actions, final results, refresh recovery, and terminal-agent
coaching visibility. The existing engine remains the only lifecycle and scoring
authority.

## 001_INGEST — Requirements intake (complete)

Goal: turn the approved browser-simulator request and existing engine evidence
into traceable requirements and constraints.

## 002_PLAN — Architecture and execution plan (current)

Goal: close design gaps, make technical decisions, decompose all requested work,
and scaffold executable implementation/review phases.

## 003_APPLICATION_FOUNDATION — Trusted browser backend

Goal: expose the current engine through a maintainable, secure, testable local
application boundary and add durable candidate-document ownership.

### 01_RUNTIME_COMPOSITION — Share the production application graph

- 01: Inventory `_RuntimeApplication`, CLI parser/dispatch, and construction
  tests; define the public container contract.
- 02: Extract the public runtime container/factory without changing CLI
  behavior.
- 03: Add composition and CLI regression tests across Python 3.10+.

### 02_CANDIDATE_DOCUMENTS — Own source, revisions, reset, and restore

- 01: Define candidate document/history models, limits, and error cases.
- 02: Implement locked read/CAS-save using only the registered candidate file.
- 03: Implement bounded snapshot history, reset, and restore.
- 04: Test stale writes, invalid input, symlinks, final states, recovery, and
  lock ordering.

### 03_LOCAL_WEB_API — Serve the capability-scoped application

- 01: Implement loopback launcher, capability lifecycle, static-resource
  loading, and clean shutdown.
- 02: Implement read-only bootstrap/session/prompt/source/history routes.
- 03: Implement start/save/reset/restore/test/submit mutation routes and stable
  error JSON.
- 04: Enforce Origin/token/body/method/path/security-header boundaries and test
  forbidden behavior.

Dependencies: composition precedes both services; candidate documents precede
source routes; lifecycle/evaluation route tests reuse existing synthetic fixture
builders.

## 004_ASSESSMENT_IDE — CodeSignal-like browser experience

Goal: build the offline candidate UI and connect every consequential interaction
to the backend contracts.

### 01_EDITOR_ASSETS — Reproducible offline editor bundle

- 01: Add the locked npm build workspace, Monaco license/provenance, and build
  commands.
- 02: Build and package Monaco, its worker assets, and the small application
  bundle without runtime network access.
- 03: Verify deterministic rebuild inputs, wheel inclusion, CSP compatibility,
  and offline loading.

### 02_ENTRY_AND_SHELL — Start flow and assessment layout

- 01: Implement the pre-assessment full/drill instructions and explicit start.
- 02: Implement top bar, server-derived timer, level navigation, split-pane IDE,
  action bar, loading/error/reconnect states, and responsive layout.
- 03: Add keyboard navigation, focus treatment, dialogs, and accessible status
  announcements.

### 03_EDITOR_AND_ASSESSMENT_ACTIONS — Work the assessment

- 01: Integrate Monaco for Python with line numbers, syntax, indentation,
  autocomplete, find, undo/redo, and local settings.
- 02: Implement debounced ETag autosave, conflict recovery, reload recovery,
  reset, and History preview/restore.
- 03: Implement Description/Rules/Info tabs and four-level switching without
  leaking non-candidate material.
- 04: Implement Run Tests output, navigation/skip, submission confirmation,
  timeout locking, and final results.

### 04_AGENT_CONTINUITY — Keep browser and terminal coaching aligned

- 01: Verify every browser lifecycle mutation refreshes safe derived terminal
  surfaces.
- 02: Document a practice/coaching loop where agents observe context and coach
  without silently editing candidate code.

Dependencies: editor assets and backend API precede integration; the shell can
be built against fixture JSON while those sequences finish.

## 005_BROWSER_VERIFICATION — Real-browser confidence and packaging

Goal: prove the complete candidate journey, safety boundaries, and installed
artifact work without network access.

### 01_BROWSER_HARNESS — Deterministic Playwright infrastructure

- 01: Add locked Playwright tooling, isolated server/workspace fixtures,
  injected clock controls, and network-denial assertions.
- 02: Add reusable page objects/helpers that select by accessible role or stable
  test id rather than visual implementation detail.

### 02_CANDIDATE_JOURNEYS — Exercise consequential behavior

- 01: Cover pre-start, full/drill start, timer, navigation, prompt tabs, editor
  settings, autosave, conflict, history, reset, and refresh.
- 02: Cover passing and failing tests, output safety, expiry, submit
  confirmation, exactly-once finalization, restart recovery, and terminal status
  synchronization.
- 03: Cover keyboard-only use, narrow-laptop layout, security headers, invalid
  capability/origin/routes/bodies, and zero unexpected network requests.

### 03_DISTRIBUTION_AND_DOCS — Ship a durable practice tool

- 01: Verify editable install, sdist, wheel contents, wheel-only offline browser
  launch, and all supported Python versions available in CI/local tooling.
- 02: Update README and agent guidance for browser launch, CLI fallback,
  coaching, troubleshooting, timer semantics, data ownership, and cleanup.
- 03: Run the canonical Python, browser, provenance, clean-clone, and package
  verification suite and record evidence.

## 006_RELEASE_REVIEW — Independent acceptance

Goal: have independent Cursor and local judge reviews challenge fidelity,
maintainability, security, content isolation, and verification evidence; fix all
material findings; commit and publish the completed private project/campaign
state.

### 01_INDEPENDENT_REVIEW — Judge the finished application

- Review architecture and human maintainability against the ingest contract.
- Review browser fidelity with screenshots and live interaction evidence.
- Review security/provenance/package boundaries and test coverage.
- Remediate findings and rerun canonical verification.

### 02_RELEASE — Preserve and publish the result

- Confirm clean worktree/clone evidence and no FETCH_ONLY content in history.
- Commit through Festival traceability, push the private project branch, merge
  through the campaign-approved flow, and synchronize the campaign pointer.
- Mark the festival complete only after all success criteria are evidenced.

## Requirement coverage

- B01-B14: phases 003 and 004, with verification in phase 005.
- B15-B18: candidate-document and IDE integration sequences.
- B19-B20: phase 005.
- B21-B25: enforced as exclusions in architecture, security, and release review.
