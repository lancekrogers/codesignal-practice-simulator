# Assessment IDE Delivery Evidence

## Delivered project state

The linked project worktree is clean at commit `0ccdf6a`. Phase 004 is represented
by four traced project commits:

- `b318fec` — reproducible offline Monaco assets
- `937c9a8` — assessment entry and responsive browser shell
- `56c6ac8` — editor and assessment actions
- `0ccdf6a` — safe browser/terminal coaching continuity

All four phase sequences and every task within them are complete. Their testing,
review, and iteration records are stored under each sequence's `results/`
directory.

## Required deliverables

### Locked offline editor workspace

- `webui/package.json` and `webui/package-lock.json` lock Monaco Editor 0.56.0,
  esbuild, DOMPurify, marked, and Playwright.
- `webui/build.mjs` creates the browser bundle, same-origin editor/language
  workers, stable aliases, and a fingerprinted manifest.
- `webui/PROVENANCE.md`, `webui/LICENSES/`, packaged `NOTICE.txt`, and
  `ASSET_PROVENANCE.txt` record the shipped license and asset provenance.
- `src/codesignal_practice_simulator/web/static/manifest.json` declares the 13
  packaged runtime assets. `tests/test_asset_packaging.py` and
  `tests/test_asset_verification.py` verify exact source, sdist, wheel, and
  installed-package contents and offline loading.

### Entry and assessment shell

- `webui/src/app.ts`, `views.ts`, `view_state.ts`, and `attempt_view.ts` render
  bootstrap metadata, explicit full/drill selection, confirmation, loading,
  reconnect/error, expired, and submitted screens.
- `attempt_shell.ts`, `navigation_view.ts`, `attempt_panes.ts`, and
  `attempt_controls.ts` render the timer/save top bar, four-level navigation,
  prompt/editor/output panes, and action bar.
- `styles/base.css` and `styles/assessment.css` implement desktop and narrow
  layouts, visible focus, reduced motion, bounded panes, and dialogs.
- `webui/tests/shell_contract.spec.mjs`, `shell_layout.spec.mjs`, and
  `shell_lifecycle.spec.mjs` exercise entry semantics, server-authoritative
  countdown behavior, responsive layout, keyboard paths, focus, and recovery.

### Editor, source recovery, and assessment actions

- `webui/src/editor.ts` configures Python Monaco, same-origin workers, local-only
  non-authoritative settings, and the exact-source read-only fallback.
- `source_api.ts`, `source_controller.ts`, `source_controller_runtime.ts`, and
  `source_state.ts` implement debounced ETag autosave, explicit conflict
  recovery, history preview/restore, and reset without silent overwrite.
- `prompt_controller.ts`, `attempt_evaluation.ts`, `attempt_results.ts`, and the
  `attempt_runtime*.ts` modules implement prompt tabs, local practice tests,
  bounded candidate-safe failures, submit confirmation, expiry locking,
  repeat-submit recovery, and stored final results.
- Browser coverage is in `editor_settings.spec.mjs`, `source_save.spec.mjs`,
  `navigation.spec.mjs`, `actions.spec.mjs`, `accepted_journeys.spec.mjs`, and
  `source_terminal.spec.mjs`; Python transport/lifecycle coverage is in the
  `tests/test_web_server_*.py` modules.

### Accessibility and safe terminal continuity

- `webui/src/a11y.ts` and `confirmation_dialog.ts` implement live regions,
  keyboard interaction, dialog containment, initial focus, and focus restore.
- `RuntimeApplication` refreshes derived `STATUS.md` after browser start, time,
  test, submit, repeat-submit, and deadline transitions while preserving the
  server lifecycle as the only authority.
- Root/attempt `AGENTS.md`, `COACHING.md`, `README.md`, and
  `docs/agent-safety.md` require permission before candidate source/history
  access or edits. Coaching remains outside browser APIs, source, scoring,
  status/context, and final results.
- `tests/test_web_continuity.py` and
  `webui/tests/browser_continuity.spec.mjs` verify real browser/CLI continuity,
  deadline transitions, repeat submission, allowlisted context schemas, and
  coaching/source/reference isolation.

## Final verification

The final phase-004 verification recorded on 2026-09-09 is:

- `python3 -m unittest discover -s tests -v`: 275 passed, 1 skipped.
- `python3 scripts/run_legacy_checks.py`: all manifest scopes, 26 legacy
  specification tests, 12 staged-solution tests, and Levels 1–4 passed.
- `python3 -m compileall -q src tests`: passed.
- `npm --prefix webui run check`: passed locked metadata and license checks.
- `npm --prefix webui run build`: passed.
- `npm --prefix webui run check-assets`: all 13 packaged assets passed.
- `npm --prefix webui run test:browser`: 95 Playwright tests passed.
- `git diff --check`: passed.

Fresh read-only Cursor reviews were run for every sequence. All accepted findings
were fixed and reverified; the final phase review records no unresolved material
finding, relaxed security boundary, or deferred P0/P1 requirement.

## Phase conclusion

The phase objective is met. The application now provides the feature-complete,
offline CodeSignal-style browser assessment IDE required for the real-browser
journey and distribution verification in phase 005.
