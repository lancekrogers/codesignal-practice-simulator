# Entry and shell code review

Date: 2026-09-09

Reviewed diff base: project worktree `HEAD b318fec` through the complete
uncommitted sequence diff.

Reviewers used fresh, read-only Cursor Agent CLI sessions with model
`gpt-5.6-luna-high` and `--mode ask --trust`. The initial repository-wide
review was split into bounded backend and frontend passes after the first
session exceeded the output-capture window. Neither review pass edited files.

## Initial findings

- High, `src/codesignal_practice_simulator/fixture_setup.py`: resolving a
  symlinked cache path before validating its lexical components could let
  publication move or remove an unrelated directory inside the workspace.
- Medium, `src/codesignal_practice_simulator/fixture_setup.py` and
  `workspace_cache.py`: invalid UTF-8 fixture metadata could escape as
  `UnicodeDecodeError` instead of the documented fixture-setup domain error.
- P1, `webui/src/state.ts`: a delayed resync reset the countdown anchor at
  response receipt, allowing the displayed timer to pause for the response
  age even though its monotonic clamp prevented an increase.
- P2, `webui/src/attempt_view.ts`: `createElementApi` exceeded the sequence's
  50-line hand-maintained function limit.

Initial verdicts: backend **REJECT**; frontend **REJECT**.

## Dispositions

- The cache path is now checked lexically for symlink traversal before
  resolution, and publication independently refuses a symlink destination.
  A regression proves an outside sentinel and target contents are unchanged.
- UTF-8 decode failures are translated at both packaged-runtime and
  source-manifest boundaries, with focused tests for both error contracts.
- Countdown anchors now include snapshot transit age derived from
  `observed_at`; the monotonic clamp remains in place. A real-browser test
  delays the resync response and verifies countdown progress continues.
- The UI API constructor was split into focused display and control helpers;
  the affected functions are below 50 lines.
- A missing `src` path bootstrap in the new standalone workspace-cache test
  was corrected during root verification.

Focused rerun evidence:

- Fixture setup: 8 tests passed.
- Workspace cache metadata: 1 test passed.
- Stale countdown resync: 1 Playwright test passed.
- Web metadata and asset-integrity checks passed.

## Final disposition reviews

The same concerns were re-reviewed in fresh, read-only Cursor sessions.

- Backend: no actionable findings; **APPROVE**.
- Frontend: no actionable findings; **APPROVE**.

The reviewers explicitly confirmed FETCH_ONLY/cache isolation, sentinel
preservation, documented error translation, continuous countdown behavior,
maintainable helper size, and coverage of the delayed-resync case. Features
scheduled for sequence 03 (autosave, execution, submission, and results) were
excluded from this gate as required by the sequence boundary.

Final result: **APPROVE**.
