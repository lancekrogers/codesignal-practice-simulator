# Requirements

## P0 — Required for the browser simulator

| ID | Requirement | Acceptance criteria |
| --- | --- | --- |
| B01 | Launch a local assessment application | `codesignal-sim web` (final command name may be refined in planning) binds only to loopback, selects an available port, emits a usable URL, and can open the default browser. It works from editable and wheel installs. |
| B02 | Present a pre-assessment entry screen | Before state or time is created, show assessment name, duration, levels, rules, no-pause warning, and full/drill choice. Only the explicit Start action creates the attempt and begins the timer. |
| B03 | Reproduce the assessment shell | Show a compact top bar with assessment title, persisted countdown, connection/save state, and editor settings; question/level navigation; a prompt/navigation pane; editor pane; result/output pane; and Run Tests, Skip/navigation, and green Submit actions in CodeSignal-like positions. |
| B04 | Provide the documented information views | Description, History, Rules, and Info are keyboard-accessible views. Description renders only the selected copied level prompt. Rules and Info are first-party static guidance. History shows candidate-source revisions only. |
| B05 | Provide a realistic Python editor | Use a locally bundled, license-compatible editor with Python syntax, line numbers, indentation, bracket support, find, undo/redo, and configurable theme, font size, tab size, and auto-brackets. No CDN or network is required at runtime. |
| B06 | Save candidate work durably and safely | Autosave only the selected attempt's registered `simulation.py`. Use content revisions/ETags and atomic replacement; reject stale writes, symlinks, oversized/invalid UTF-8 bodies, final/expired attempts, and arbitrary paths. Reload recovers the saved source. |
| B07 | Preserve server-authoritative lifecycle and time | Existing lifecycle services remain authoritative. The client polls/observes derived state; it cannot pause, extend, reset, or manufacture time. Expiry persists once and disables illegal actions. |
| B08 | Run and display assessment tests | Run Tests invokes the existing isolated four-group scorer, shows per-level status and bounded safe output, preserves candidate-failure exit semantics, and never imports browser/server/reference code into scoring. |
| B09 | Submit exactly once | Submit requires confirmation, saves the latest source, invokes existing idempotent finalization, renders the stored final result, and makes repeat submission byte/state stable. Timeout and refresh cannot double-score. |
| B10 | Recover browser sessions | A capability URL can reopen the selected attempt after refresh or server restart. The server reads durable state rather than browser-local lifecycle authority. Missing/corrupt/stale selections produce actionable screens. |
| B11 | Enforce local web security boundaries | Bind to `127.0.0.1`; generate a per-launch capability token; validate token and mutation Origin; send no CORS permission; cap request sizes; set CSP, no-sniff, and cache policy headers; expose no arbitrary file or command API. |
| B12 | Preserve live-attempt content boundaries | No endpoint serves `solution/`, `study/`, `notes/`, fetched reference/starter/test bytes beyond copied candidate-facing inputs, structured state files, or raw scorer internals. Static browser assets contain no assessment/vendor bytes. |
| B13 | Support terminal-agent coaching | Existing `context`, `STATUS.md`, `COACHING.md`, and attempt `AGENTS.md` remain synchronized with browser actions. Agents default to safe context/coaching and require explicit user permission before candidate-code access. Coaching is not imported, executed, or scored. |
| B14 | Work offline after setup | Runtime requires no external service. Browser assets are packaged locally; fixture handling remains FETCH_ONLY and hash-validated. Python 3.10+ remains supported. |

## P1 — Fidelity and quality

| ID | Requirement | Acceptance criteria |
| --- | --- | --- |
| B15 | Candidate source history and restore | Record bounded, attempt-local source revisions with timestamps/content hashes. History can preview and explicitly restore a prior revision without altering lifecycle events or exposing reference content. |
| B16 | Reset safely | Reset requires confirmation and restores the attempt's own initial candidate source, records a source revision, and is unavailable after expiry/submission. |
| B17 | Progressive level experience | Level navigation reflects four groups, keeps each copied prompt distinct, preserves code across levels, and shows completed/reached state without falsely representing local cases as official hidden tests. |
| B18 | Accessibility and responsive behavior | All actions work by keyboard, focus is visible, dynamic saves/results use appropriate live regions, dialogs manage focus, and the layout remains usable from narrow laptop widths through desktop. |
| B19 | Browser-level verification | Playwright covers entry, start, autosave/conflict, refresh recovery, navigation, settings, test, candidate failure, expiry, confirmation, submit idempotency, security headers, forbidden routes, and terminal-agent surface updates. |
| B20 | Operational documentation | README and agent docs distinguish browser UI, direct CLI, canonical verification, troubleshooting, data ownership, timer semantics, and post-attempt learning material. |

## P2 — Explicitly deferred

| ID | Deferred capability | Reason |
| --- | --- | --- |
| B21 | Pixel-for-pixel CodeSignal branding or proprietary assets | Interaction fidelity is required; trademark/asset copying is not. |
| B22 | Accounts, invitations, cloud workspaces, video, identity verification, or proctoring | Local personal practice does not require CodeSignal platform services. |
| B23 | Multiple languages or arbitrary shell/terminal execution in the browser | The approved assessment is Python/file-storage and arbitrary execution would materially expand the security surface. |
| B24 | Claimed CodeSignal hidden tests, score prediction, or remote integration | The project has only its pinned visible fixture and first-party study checks; it must not fabricate equivalence. |
| B25 | Keystroke replay or collaborative editing | Source revision history is sufficient for first release; realtime collaboration is not needed for solo rehearsal. |
