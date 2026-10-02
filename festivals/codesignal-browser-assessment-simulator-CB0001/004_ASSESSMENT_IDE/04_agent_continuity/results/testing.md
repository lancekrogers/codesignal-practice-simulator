# Testing results

Date: 2026-09-09

## Environment

- Python 3.14.6
- Node.js 26.7.0
- npm 11.19.0
- Playwright 1.63.0

## Commands and outcomes

- Final `python3 -m unittest discover -s tests -v` after iteration: 275 tests passed, 1 skipped. The testing-gate run before the two controlled-expiry regressions was 273 passed, 1 skipped.
- `python3 scripts/run_legacy_checks.py`: passed all three manifest scopes, 26 legacy specification tests, 12 staged-solution tests, and Levels 1–4 study checks.
- `python3 -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- `npm --prefix webui run check`: passed metadata, lockfile, and license checks.
- `npm --prefix webui run build`: passed without scope-relevant warnings.
- `npm --prefix webui run check-assets`: passed integrity verification for 13 packaged assets.
- `npm --prefix webui run test:browser`: 95 Playwright tests passed with one worker.

## Continuity evidence

- Web start, time, candidate-failing test, submit, and repeat submit refresh the same derived `STATUS.md` and context semantics used by the CLI.
- The durable Python integration invokes the public CLI parser/execution path with `context --format json --json` against the same application and temporary workspace used by web requests.
- The real-process browser journey invokes the public CLI against the fixture server's workspace after start, time, test, and submit, and compares attempt ID, lifecycle status, deadline, score, events, and next legal commands.
- A unique synthetic coaching sentinel remains in candidate-owned `COACHING.md` and is absent from candidate source, source history and API payloads, prompts, scoring/practice evidence, `STATUS.md`, CLI context, and final browser results.
- Generated attempt guidance requires explicit permission before source/history access and separately before source edits.
- A delayed renderer failure cannot change a successful authoritative lifecycle response.
- Browser network policy denied undocumented same-origin and all external requests throughout the continuity journey.

## Failure triage

- An intermediate Cursor-run full suite reported that a temporary wheel environment lacked the `codesignal-sim` executable. It created no retained artifact and did not reproduce in the mandated clean run: `test_installed_wheel_fetches_offline_then_starts_outside_checkout` passed.
- An initial documentation assertion run failed while wording was being aligned across policy surfaces. The documents and assertions were corrected; the focused documentation/workspace/rendering suite then passed 26/26.
- The Playwright `NO_COLOR`/`FORCE_COLOR` message is a runner-environment notice and requires no application change.

## Repository hygiene

- All tests used temporary synthetic workspaces; no live attempt, fixture cache, browser profile, wheel environment, or coaching sentinel was retained.
- The passing Playwright result marker was removed after verification.
- No coverage threshold or security boundary was relaxed.
