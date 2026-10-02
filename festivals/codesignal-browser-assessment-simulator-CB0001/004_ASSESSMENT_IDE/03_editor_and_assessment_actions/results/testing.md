# Testing results

Date: 2026-09-09

## Environment

- Python 3.14.6
- Node.js 26.7.0
- npm 11.19.0
- Playwright 1.63.0

## Commands and outcomes

- `python3 -m unittest discover -s tests -v`: 267 tests passed, 1 skipped.
- `python3 scripts/run_legacy_checks.py`: passed. This included all three manifest scopes, 26 legacy specification tests, 12 staged-solution tests, and Levels 1–4 study checks.
- `python3 -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- `npm --prefix webui run build`: passed with no scope-relevant warnings.
- `npm --prefix webui run check`: passed metadata, lockfile, and license checks.
- `npm --prefix webui run check-assets`: passed packaged-asset integrity verification for 13 assets.
- `npm --prefix webui run test:browser`: 76 Playwright tests passed with one worker.
- Supplemental `python3 -m pytest -q`: 304 passed, 1 skipped, and 190 subtests passed.

## Coverage and recovery evidence

- Source edits, settings, autosave, manual retry, stale ETag recovery, conflict choices, history, reset, tests, submit, expiry, refresh, and real server restart are exercised through the real packaged UI and synthetic fixture server.
- Run/Test/Submit and source mutations share one operation lock. Tests assert exact CAS request ordering and prevent duplicate or competing mutations.
- Candidate failure, internal failure, malformed practice data, and hostile diagnostic text have distinct bounded handling.
- Server-derived expiry and submitted states disable mutations while retaining authoritative source in a read-only fallback.
- Accessible action names, keyboard navigation, dialog focus restoration, narrow layout, save/action indicators, and offline Monaco behavior have meaningful assertions.
- The browser policy fails undocumented same-origin routes, external requests, missing or failed static resources, console/page errors, and forbidden fixture content.

## Failure triage

An intermediate full-browser run found a worker-failure race at `webui/.test-results/editor_settings-preserves--d601c-y-state-when-a-worker-fails/`. The fallback preserved exact source but could retain the stale live message `Saving…`. The implementation now settles the in-flight autosave before locking the fallback and reports authoritative saved/unsaved state. The focused case passed five consecutive runs, both editor suites passed 18 tests, and the final full browser run passed 76/76. The failure artifacts were removed by the clean rerun.

## Repository hygiene

- No attempt workspace, fixture cache, Playwright trace/report, or `.test-results` path is tracked by Git.
- Browser tests used temporary synthetic workspaces and the existing shared fixture implementation.
- No coverage threshold was lowered and no coverage-only assertions were added.
