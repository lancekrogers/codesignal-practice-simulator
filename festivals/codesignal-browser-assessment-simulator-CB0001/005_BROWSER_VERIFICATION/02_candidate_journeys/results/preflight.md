# Candidate-journey preflight — 2026-09-10

Read-only Cursor Luna High coverage audit, prepared while the preceding harness
was reviewed. No candidate-journey task is completed by this document.

## Reuse existing coverage

The final harness suite passed 151 tests. Existing `shell_contract`,
`shell_layout`, `navigation`, `editor`, `editor_settings`, `source_save`,
`source_terminal`, `actions`, `accepted_journeys`, `fresh_findings`, and
`browser_continuity` specs cover the core candidate workflow. Confirm exact
assertions against the sequence tasks before adding tests; avoid duplicating
passing coverage.

## Focused gaps to validate and fill

- B02: visible pre-start duration, rules, and explicit no-pause warning.
- B05: Python syntax presentation, indentation, and actual automatic bracket
  behavior. Disabling a default-enabled preference and reload persistence are
  now covered through `EditorPage.applySettings`.
- B15: history timestamps and content hashes, beyond bounded preview/restore.
- B18: computed visible focus styling and reduced-motion behavior.
- B06/B11/B19: browser-suite direct HTTP rejection matrix for token, Origin,
  method/path, UUID, body, ETag, security/cache headers, and forbidden content.
  Check existing `tests/test_web_server_*.py` before adding missing invalid UTF-8,
  request-level symlink, or terminal-mutation assertions. Filesystem setup can
  remain in focused Python integration tests.
- Task 04: exact B01–B20 evidence index and B21–B25 exclusions, distinguishing
  actual browser/Python execution from package evidence still pending sequence 03.

Some task command examples name stale modules or generic spec selectors. Derive
the executable commands from current filenames; e.g. there is no aggregate
`tests.test_web_server` module. Record corrected commands in the evidence.

## Execution boundaries

Use the shared fixture/page helpers, synthetic data, injected clocks, and default
privacy-safe reporters. Do not override reporters or sanitize artifacts after a
test run to make the proof pass. Preserve the completed harness at `be5389b`.
Follow tasks 01–04 in order, then testing, independent Cursor review, iteration,
and `fest commit`. Wheel/CLI provenance and clone proof remain sequence 03 work.
