# Entry and shell iteration

Date: 2026-09-09

## Testing findings

- The original formal test run had no failed assertions, actionable warnings,
  or missing required evidence. The expected Node `NO_COLOR` notice does not
  affect product behavior or test validity.
- A ten-repeat dialog-focus stress run had exposed an intermittent initial-focus
  race before the formal run. Initial focus was made synchronous; the stress,
  focused, complete source-browser, and installed-wheel suites passed afterward.

## Code-review findings and fixes

- Cache symlink traversal (High): added lexical ancestor/root checks before
  resolution and a publication-time destination check. A regression verifies
  the symlink and outside sentinel remain unchanged.
- Invalid UTF-8 metadata (Medium): translated decode failures to
  `FixtureSetupError` and `FixtureSetupRequiredError` at their respective API
  boundaries, with focused source and packaged metadata tests.
- Delayed countdown resync (P1): incorporated snapshot transit age into the
  monotonic anchor and retained the no-increase clamp. A delayed real-browser
  response now proves the visible countdown continues progressing.
- Oversized UI helper (P2): split display and control responsibilities into
  focused helpers below 50 lines without changing shell behavior.
- Verification follow-up: added the standard `src` path bootstrap to the new
  standalone workspace-cache test module so isolated discovery works.

Both independent Cursor disposition reviews returned **APPROVE** with no
remaining actionable findings.

## Final rerun evidence

- 261 Python tests passed with no skips.
- 32 source-tree Playwright tests passed.
- 32 installed-wheel Playwright tests passed.
- All legacy manifest, specification, stage, and levels 1-4 checks passed.
- TypeScript/JavaScript metadata checks, static asset integrity, Python
  compilation, and `git diff --check` passed.
- Changed hand-maintained source/test files remain below 500 lines; the reviewed
  functions remain below 50 lines.
- No attempt data, dependency cache, secret, FETCH_ONLY payload, or retained
  Playwright failure artifact is part of the intended diff.

No P0/P1 requirement was deferred and no exclusion was relaxed.
