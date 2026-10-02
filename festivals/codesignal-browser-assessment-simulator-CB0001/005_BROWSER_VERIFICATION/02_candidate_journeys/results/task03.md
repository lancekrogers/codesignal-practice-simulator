# Task 03 — accessibility, security, and offline journey

## Verification

All browser runs used the repository-default Playwright configuration and its
privacy-safe reporters. No reporter or worker override was supplied. All
fixtures were synthetic; no candidate or `FETCH_ONLY` content was read.

- `npm run test:browser -- tests/accessibility_security_offline.spec.mjs tests/shell_layout.spec.mjs` (from `webui/`) — 11 passed, exit 0.
- `npm run check` (from `webui/`) — passed, exit 0.
- `python3 -m unittest tests.test_web_server_static tests.test_web_server_source tests.test_web_server_safety tests.test_web_server_lifecycle -v` (from the project root) — 21 passed (`Ran 21 tests`), exit 0.

No full suite was run.

## Requirement-to-assertion mapping

- Keyboard accessibility: `shell_layout.spec.mjs` now reaches the start
  control using `Tab` and asserts the computed `:focus-visible` state,
  solid 2px outline, 2px offset, and non-empty focus shadow. Existing
  `shell_layout`, `navigation`, `source_save`, and `actions` coverage retains
  roving, modal trapping/opener restoration, conflict/action focus, names,
  live status, and narrow viewport behavior.
- Reduced motion: `shell_layout.spec.mjs` emulates
  `prefers-reduced-motion: reduce` and asserts the applied computed
  `scroll-behavior: auto` and minimized animation/transition durations.
- D004 direct HTTP boundary: `accessibility_security_offline.spec.mjs` uses
  the synthetic fixture server to assert no-store/nosniff/CSP/permissions
  headers and absent CORS. It rejects missing/wrong capability, foreign
  Origin, invalid method, invalid UUID, malformed JSON, wrong content type,
  and missing ETag with exact status/code envelopes that contain no token,
  filesystem path, traceback, or forbidden sentinel. It also asserts
  404/not_found for fixed forbidden API and static paths.
- Request-level source boundaries: `test_web_server_safety.py` corrupts only
  synthetic source bytes to assert invalid UTF-8 maps to a safe 422 envelope,
  then replaces that source with a symlink and asserts a safe 404 envelope
  while preserving the external sentinel unchanged.
- Offline/content isolation: the reused `network_guard.mjs` is installed by
  every browser spec, blocks non-loopback and wrong-origin requests, scans
  same-origin responses for forbidden sentinels, and fails unexpected network
  activity. Existing `editor.spec.mjs` exercises local bootstrap, Monaco,
  workers, editing, and package-only asset checks through that guard.

## Scope

Only task03 gaps were added: computed keyboard focus, reduced-motion
behavior, the direct browser-suite HTTP rejection matrix, and synthetic
request-level invalid-UTF-8/source-symlink checks. Completed task01/task02
tests and the existing editor bundle were preserved. No task status changed
and no commit was created.
