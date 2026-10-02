# Iteration results

Date: 2026-09-09

## Testing findings copied from `testing.md`

1. An intermediate browser run exposed a Monaco worker-failure/autosave race: the exact source survived, but the detached live shell could remain at `Saving…`.
   - Fix: worker fallback now waits for an in-flight save before locking the source controller and reports clean or dirty state from the settled authoritative source.
   - Evidence: the focused case passed five consecutive runs, both editor suites passed 18/18, and the final full browser suite passed 94/94.

No other failed assertion, warning requiring application action, or missing evidence was listed in `testing.md`. The Playwright `NO_COLOR`/`FORCE_COLOR` message is emitted by the test runner environment and does not affect the application or gate.

## Code-review findings copied from `review.md`

### Major findings

1. Level status markers stayed stale after Run Tests.
   - Fix: evaluation completion refreshes every level-status marker.
   - Evidence: navigation/action browser assertions and the 94/94 final suite pass.
2. Confirmation dialogs lacked stable accessible label and description relationships.
   - Fix: the shared dialog assigns stable title/description IDs and `aria-labelledby`/`aria-describedby`.
   - Evidence: dialog keyboard/focus/accessibility browser cases pass in the final suite.
3. Monaco worker failure could enqueue a duplicate PUT while a save was already in flight.
   - Fix: fallback reuses and settles the active save instead of calling `change` again.
   - Evidence: focused repeated worker-failure checks and the final editor suites pass.
4. A strict `web/v1` evaluation without `practice` was treated as incompatible.
   - Fix: absent practice evidence is derived only from the typed score using fixed safe strings; malformed present evidence still fails closed.
   - Evidence: absent, null, oversized, hostile, mismatched, candidate-failure, and internal-error browser/Python cases pass.
5. A locally displayed zero could remain stuck after an authoritative active resync.
   - Fix: all authoritative snapshots use one countdown controller; it remains monotonic except for explicit recovery from local zero.
   - Evidence: zero recovery, stale periodic resync, explicit refresh, evaluation refresh, and server expiry cases pass.

### Minor finding

1. Evaluation evidence plumbing retained unused runner state and an unused browser-output constant.
   - Fix: evidence is constructed from the score alone; unused state and constant were removed.
   - Evidence: Python evaluation/scoring suites and safe browser rendering pass.

### Test gaps

1. Async request-policy assertions were not consistently awaited.
   - Fix: all affected suite teardown hooks await policy settlement.
2. Level-marker updates after evaluation lacked direct coverage.
   - Fix: action/navigation assertions verify updated reached/completed/test outcomes.
3. Real server-clock expiry lacked a browser journey.
   - Fix: `accepted_journeys.spec.mjs` drives the fixture clock through the real `/api/time` endpoint and proves every mutation is locked.
4. Lost submit-response recovery lacked end-to-end coverage.
   - Fix: the browser drops the response after real finalization, recovers submitted state, retries idempotently, and proves one scorer call plus `started`/`submitted` events.
5. Actual isolated-scorer failure and execution-error evidence lacked backend coverage.
   - Fix: Python tests exercise both outcomes through `IsolatedAttemptScorer` and assert only fixed bounded evidence.

## Subsequent independent Cursor findings and fixes

Fresh read-only Cursor judge passes found the following additional concrete issues during iteration. None was deferred.

1. Installed fixture restarts ignored `SIMULATOR_WORKSPACE`.
   - Fix: the installed fixture uses the configured persistent workspace and only creates a temporary fallback when none is supplied.
   - Evidence: real process-restart browser journeys pass both from the checkout and installed wheel.
2. Direct refresh and active evaluation snapshots bypassed the countdown controller.
   - Fix: refresh, resync, and evaluation paths call `CountdownController.applySnapshot`.
   - Evidence: focused timer tests and final browser matrix pass.
3. Time/evaluation/reconnect responses could belong to another attempt.
   - Fix: requested, current, and returned attempt IDs are validated before state mutation.
   - Evidence: mismatch tests preserve timer, source, score/output, mutation controls, and terminal state.
4. Failed/error practice levels could carry null or non-fixed evidence.
   - Fix: present evidence requires the exact fixed string for its matching outcome; passed/mismatched/extra evidence is rejected.
   - Evidence: malformed-evidence browser cases and Python result-model tests pass.
5. Clock-file replacement and collision cleanup were not ownership-safe enough.
   - Fix: clock writes use exclusive unique temporary files plus atomic rename, and cleanup occurs only after this writer created the temporary file.
   - Evidence: deterministic collision and rename-failure tests pass.
6. Terminal reload could lose fixed failure/error evidence.
   - Fix: a stored score derives the same fixed safe evidence when no transient practice payload exists.
   - Evidence: a real scorer submit, process restart, reconnect, and one-call score check passes without raw exception text.
7. Terminal evaluation could synchronously tear down the shell and then mutate detached controls.
   - Fix: source, session, practice, result markers, and disabled controls are finalized before a single terminal time application; evaluation returns immediately after transition.
   - Evidence: a MutationObserver regression proves one terminal shell replacement and payload evidence in the final shell.
8. A delayed valid resync could update a disposed shell.
   - Fix: resync rechecks runtime disposal after the awaited response before touching connection UI.
   - Evidence: the delayed-resync test proves the replacement remains connected and the detached shell remains unchanged.
9. Evaluation normalization allowed missing source/ETag and could fabricate an empty document.
   - Fix: evaluation responses require authoritative source content and ETag.
   - Evidence: a malformed terminal submit remains active, retains exact source, and transitions nowhere.
10. The old expiry-fallback test still expected a redundant source reload after the one-transition fix.
    - Fix: the test now asserts the stronger contract: the saved authoritative fallback renders directly, read-only, with zero redundant source GETs. Reconnect without a live fallback still loads authoritative source.
    - Evidence: the revised test passed three consecutive runs, the terminal-source suite passed 3/3, and the clean full suite passed 94/94.

Final Cursor verdict: **READY**, with no remaining critical, major, minor, or concrete test-gap findings.

## Final verification

- `python3 -m unittest discover -s tests -v`: 268 passed, 1 skipped.
- `python3 scripts/run_legacy_checks.py`: passed all manifest, legacy specification, staged-solution, and Levels 1–4 checks.
- `python3 -m compileall -q src tests`: passed.
- `python3 -m pytest -q`: 305 passed, 1 skipped, 190 subtests passed.
- `npm --prefix webui run build`: passed.
- `npm --prefix webui run check`: passed.
- `npm --prefix webui run check-assets`: passed for 13 packaged assets.
- `npm --prefix webui run test:browser`: 94 passed with one worker.
- `python3 scripts/run_packaged_browser.py`: a fresh wheel installed outside the checkout and passed the same 94 browser tests.
- `git diff --check`: passed.
- Authored source and spec files remain below 500 lines; generated bundles remain excluded from that authored-file gate.
- No coverage threshold, security boundary, or requirement exclusion was relaxed.

## Hygiene

- Browser attempt workspaces, installed-wheel environments, fixture controls, and Playwright output used temporary directories.
- The final Playwright result marker was removed.
- `git status --short` contains no attempt workspace, fixture cache, dependency cache, secret, trace/report, or unexpected generated artifact.
