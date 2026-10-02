# Browser Assessment Simulator Implementation Plan

## Overview

Implement a local single-page assessment interface over the existing tested
Python engine. The backend remains standard-library Python and file storage. A
small first-party JavaScript/CSS application embeds a locally bundled Monaco
Editor. The work proceeds from domain boundaries to transport, UI, real-browser
verification, and independent release review so later layers cannot bypass
earlier safety rules.

All work occurs in one campaign-managed project worktree on a feature branch.
Cursor CLI agents perform primary implementation and focused reviews. Festival
tasks, gates, and commits preserve traceability. Direct Codex work is limited to
orchestration, small corrections, and final verification.

## Planned file layout

Existing files intentionally changed:

- `src/codesignal_practice_simulator/cli.py` — import public composition,
  parse/dispatch the `web` command, preserve all existing command behavior.
- `src/codesignal_practice_simulator/workspace.py` — create the immutable initial
  candidate source needed by reset, with a legacy-attempt fallback.
- `src/codesignal_practice_simulator/filesystem.py` and `persistence.py` — only
  narrow reusable atomic/listing primitives required by source history.
- `src/codesignal_practice_simulator/rendering.py` and attempt agent templates —
  keep terminal-safe surfaces aligned and prohibit unapproved history access.
- `pyproject.toml` — recursively package browser assets/license notices.
- `README.md`, `AGENTS.md`, and supporting docs — browser practice/coaching and
  operational guidance.

New production areas:

- `src/codesignal_practice_simulator/application.py` — public runtime container
  and factory extracted from `cli.py::_RuntimeApplication`.
- `src/codesignal_practice_simulator/candidate_documents.py` — source read,
  ETag/CAS save, immutable bounded history, reset, restore, and final-state
  guards.
- `src/codesignal_practice_simulator/web/` — server lifecycle, fixed route
  adapter, response/error/security policy, package-resource loader.
- `src/codesignal_practice_simulator/web/static/` — generated HTML/CSS/JS,
  Monaco runtime, and workers shipped in the wheel.
- `webui/` — first-party frontend source, build script, npm manifests,
  dependency provenance, and licenses; `node_modules/` ignored.

New test areas:

- `tests/test_application.py`, `tests/test_candidate_documents.py`,
  `tests/test_web_server.py`, and focused documentation/package tests.
- `browser-tests/` or `tests/browser/` — Playwright fixtures, page helpers, and
  complete candidate journeys. The exact location is chosen once after checking
  the existing test runner conventions; it does not affect architecture.

## Phase 003 — Application foundation

### Sequence 01: Runtime composition

Goal: share one public production object graph between CLI and browser without
behavior drift.

1. Characterize `_RuntimeApplication` and `_default_application` with tests for
   dependency construction, clock injection, scorer selection, derived-status
   refresh, serialization, and all current CLI commands.
2. Move the object graph into `application.py` as `RuntimeApplication` plus
   `create_application(workspace_root, *, clock, registry, ...)`. Keep thin
   application methods and the exact existing services.
3. Update `cli.py` protocols/imports and run all 158 baseline tests plus console
   and `python -m` smoke flows before adding web behavior.

Completion evidence: no existing snapshot/output/exit-code changes, clean
supported-Python unit suite, and Cursor review of the public boundary.

### Sequence 02: Candidate documents

Goal: make one service the only mutable owner of candidate source.

1. Add typed immutable records (`CandidateDocument`, `SourceSnapshot`,
   `SourceHistory`) and domain errors for conflict, unsafe document, oversize,
   invalid UTF-8, and read-only attempt.
2. Create an immutable initial source beside attempt metadata during attempt
   creation. For legacy attempts only, initialize it under lock from the current
   registered candidate file and document that reset baseline.
3. Implement safe read and CAS save under `Persistence.attempt_lock`: selected
   attempt validation, registry-derived filename, regular-file/symlink checks,
   `sha256:<hex>` ETag, 256-KiB body limit, active/unexpired lifecycle guard,
   atomic predecessor snapshot, atomic candidate replacement, deduplication, and
   newest-50 pruning.
4. Implement list/preview/restore/reset through the same service. Snapshot IDs
   are validated opaque UUIDs; no route or method receives a path.
5. Add failure-injection and concurrency tests: stale ETag, simultaneous save,
   atomic-write failure at each boundary, orphan snapshot recovery/deduplication,
   corrupt metadata, symlink swaps, invalid encoding, over-limit content,
   missing attempt, expiry, submission, reset, restore, and legacy initialization.

Completion evidence: domain tests prove candidate correctness and prior-version
recoverability across every simulated interruption.

### Sequence 03: Local web API

Goal: expose fixed, capability-scoped browser operations with no domain-policy
duplication.

1. Implement `WebServer`/`WebServerConfig` around `ThreadingHTTPServer`,
   `127.0.0.1`, port selection, 256-bit token injection, URL fragment launch,
   optional browser open, signal/keyboard shutdown, and quiet structured logs.
2. Add `codesignal-sim web --workspace-root ... [--port 0] [--no-open]` through
   the normal injected CLI dispatch so fake application/server tests remain
   possible. Do not add a configurable non-loopback host.
3. Implement package-resource static serving with an explicit manifest and MIME
   map; reject traversal, encoded traversal, directories, unknown assets, and
   non-GET/HEAD methods.
4. Implement the D004 routes and envelope. `bootstrap` returns assessment entry
   metadata plus an optional selected durable session; it never starts time.
   Prompts come only from `PromptService`; context-safe result serialization is
   explicit and bounded.
5. For source/test/submit mutations, validate token/origin/body, persist the
   supplied source with `If-Match`, then call the existing service. Return the
   authoritative session, time, score groups, source ETag, and derived status
   needed for one client state transition.
6. Test success/error schemas; candidate test-failure semantics; capability and
   Origin enforcement; security/cache headers; content/body caps; malformed
   JSON/UUID/ETag; route/method allowlists; concurrent mutation; shutdown; no
   path/internal exception leakage; and absence of reference/study/vendor bytes.

Completion evidence: API tests cover B01, B06-B14 and baseline CLI behavior
still passes.

## Phase 004 — Assessment IDE

### Sequence 01: Editor assets

Goal: produce a licensed, reproducible, offline Monaco bundle that works from a
wheel under the restrictive server policy.

1. Add `webui/package.json` and lockfile for `monaco-editor@0.56.0`, esbuild, and
   the chosen Playwright version. Record registry/repository/license provenance,
   copy required notices, ignore install caches, and expose `build`, `check`, and
   `test:browser` scripts.
2. Build explicit application, editor-worker, and language-worker entries.
   Configure Monaco worker URLs to same-origin fingerprinted resources. Keep
   authored source separate from generated package assets.
3. Add a reproducibility check that starts from the lockfile, rebuilds assets in
   a temporary output directory, compares the declared asset manifest, inspects
   wheel contents, and loads the app with network disabled.

Completion evidence: editable and wheel installs serve all assets with zero CDN
requests; notices and exact build steps are documented.

### Sequence 02: Entry and shell

Goal: reproduce the visual hierarchy and start semantics of a coding assessment.

1. Build the entry screen from bootstrap metadata: title, total duration,
   four-level outline, concise rules, no-pause warning, full/drill controls,
   practice framing, explicit confirmation, and Start. No attempt exists until
   the successful start response.
2. Build the assessment shell: compact header/title, authoritative countdown,
   connection/save indicator, settings; numbered level navigation; tabbed prompt
   pane; Monaco editor pane; resizable output drawer; bottom navigation/Skip,
   Run Tests, and visually primary green Submit action.
3. Implement loading, missing fixture, corrupt/missing selected attempt,
   reconnect, expired, submitted, and internal-safe-error screens. Refresh uses
   bootstrap and never restarts or extends time.
4. Implement desktop and narrow-laptop layouts, visible focus, semantic
   landmarks, tab/arrow behavior, live regions, focus-contained dialogs, Escape,
   reduced-motion support, and at least WCAG AA color contrast.

Completion evidence: screenshot review at desktop/narrow viewport and
keyboard-only smoke coverage.

### Sequence 03: Editor and assessment actions

Goal: make every real practice interaction durable and predictable.

1. Initialize Monaco in Python mode and expose theme, 12-22px font size, 2/4/8
   tab size, minimap, word wrap, and bracket controls. Persist only these
   non-authoritative preferences locally.
2. Load source/ETag, mark dirty on edits, debounce save, serialize one in-flight
   save, retry only safe connection failures, and surface saved/conflict/error
   states. On 409, preserve the user's buffer and offer explicit reload or copy;
   never silently overwrite either version.
3. Implement Description from copied prompt, History list/preview/restore,
   first-party Rules, and environment/assessment Info. Switching level changes
   prompt/navigation state but keeps the one cumulative source file.
4. Implement reset confirmation, previous/next/Skip navigation, and reached/test
   status markers. Labels say “practice tests” or “assessment checks,” never
   official CodeSignal hidden tests.
5. Run Tests flushes source, disables competing evaluation, shows bounded group
   progress/results and candidate-readable failures, refreshes authoritative
   state/time, and returns focus sensibly.
6. Submit opens a consequence-focused confirmation, flushes source, calls the
   idempotent submit route once, and renders immutable final results. Expiry
   disables edits/run and resolves via server state; repeat submission/reload
   renders the stored result without rescoring.

Completion evidence: component-level browser checks plus visible manual review
of the complete flow.

### Sequence 04: Agent continuity

Goal: let terminal agents coach against browser activity without compromising
the attempt.

1. Ensure web start/status/time/test/submit paths refresh `STATUS.md` exactly as
   CLI paths do and safe `context --format json` reflects the active browser
   attempt.
2. Update root/attempt `AGENTS.md` and `COACHING.md`: agents may read derived
   status, prompts the user explicitly asks about, and user-pasted errors; they
   must ask before reading `simulation.py` or `.candidate-history`, and must not
   edit candidate work unless explicitly requested.
3. Document parallel browser/terminal workflows and verify changes in one
   surface are durably visible in the other.

Completion evidence: automated sync assertions and a real-process coaching
rehearsal.

## Phase 005 — Browser verification

### Sequence 01: Browser harness

1. Install the locked Chromium build and add a fixture that creates a temporary
   project/workspace, injects a controllable clock and known token, starts the
   server on loopback, and guarantees cleanup.
2. Deny unexpected network traffic, capture console/page errors, preserve trace
   and screenshot only on failure, and add role-first page helpers.

### Sequence 02: Candidate journeys

1. Test entry/start full and drill; timer/no-pause; level navigation; all tabs;
   Monaco editing/settings; autosave; stale conflict; reset/history/restore;
   refresh and process restart.
2. Test passing and intentionally failing practice tests; safe output; run/save
   race; expiry; submit confirmation/cancel/success; exact repeat submit; immutable
   final result; terminal status/context synchronization.
3. Test keyboard-only use, focus restoration, live regions, narrow viewports,
   invalid token/origin/routes/methods/body, headers/CSP, offline load, and no
   prohibited content in responses, static assets, screenshots, or traces.

### Sequence 03: Distribution and docs

1. Run Python tests under available 3.10/3.11/3.12/3.14 interpreters, browser
   suite, static build check, and provenance scan.
2. Build sdist/wheel; install the wheel into a clean temporary virtualenv without
   the source tree; launch with network denied; complete a browser smoke flow.
3. Rehearse clean private project and campaign clones with the documented fixture
   setup, then run canonical console/module/browser flows.
4. Update README/troubleshooting and canonical verification commands from the
   actual proven flow, not aspirational steps.

Completion evidence: recorded command outputs, wheel manifest, browser trace on
failure only, and clean-clone hashes.

## Phase 006 — Release review

### Sequence 01: Independent review

Run separate Cursor Agent reviews for architecture/maintainability,
security/content isolation, and live UI/browser fidelity. Run local judge gates
with the full contract and evidence. Convert every material finding to a tracked
fix, then rerun the relevant focused and canonical suites.

### Sequence 02: Release

Use `fest commit` for traceable commits. Verify no FETCH_ONLY content, secrets,
temporary traces, `node_modules`, or generated attempt data is tracked. Push the
private project feature branch, integrate it through the campaign project flow,
push project main, synchronize and push the campaign submodule pointer, and
complete the festival only after remote/clone evidence matches local HEAD.

## Global ordering and gates

- Phase 003 is strictly first because every UI action depends on trusted domain
  and transport boundaries.
- Phase 004 may begin only after the API contract and source service pass their
  sequence gates.
- Phase 005 follows a feature-complete IDE; it may add only testability fixes and
  documentation, not unplanned product scope.
- Phase 006 accepts no deferred P0/P1 behavior.
- Every implementation sequence ends with tests, independent Cursor review,
  remediation, a clean diff/status check, and a Festival commit.
- Every phase gate reruns the cumulative canonical suite and local delegated
  judge before advancing.
