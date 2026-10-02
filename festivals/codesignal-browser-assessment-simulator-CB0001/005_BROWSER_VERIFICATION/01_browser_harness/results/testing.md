# Browser harness testing evidence

## Fresh verification — 2026-09-10

Final corrected harness: `npm --prefix webui run test:browser` passed **151/151**
tests with the configured privacy-safe reporters and success-cleanliness check.
This supersedes the earlier 144/146-test runs and the 149-pass/one-failure run
described in `iteration.md`. First-run and fatal-startup proofs now use actual
Playwright subprocess output without a second sanitizer.

Final `npm --prefix webui run check`, JavaScript/Python syntax checks,
`scripts/check_assets.py` (13 assets), staged whitespace checks, and tracked/Git
provenance scans all passed. The project index contains only reviewed source,
test, and provenance changes; no generated artifact or fixture data is staged.

The uncommitted harness has expanded since the earlier report below. Fresh checks
against base `0ccdf6a` plus the preserved harness changes:

- `npm --prefix webui run check`: PASS.
- `npm --prefix webui run test:browser`: PASS — 144 tests; the configured
  privacy-safe reporters were retained. No failure artifacts remained.
- `just verify`: PASS — legacy/provenance checks, 275 Python tests with one
  environment skip, four explicit end-to-end tests, and `git diff --check`.
- The Python skip is the sdist/wheel archive test: no interpreter with the
  `build` module is installed. Installed-wheel tests passed. The distribution
  sequence must provision a temporary build environment and run the skipped
  archive check before claiming full distribution verification.

These baseline checks preceded the review corrections; focused and final reruns
are recorded in `iteration.md` and the final summary above.

## Earlier verification — 2026-09-09

Verified from the linked project worktree on 2026-09-09.

## Toolchain

- Python 3.14.6
- Node.js v26.7.0
- npm 11.19.0
- Playwright 1.63.0
- Locked Chromium revision 1243, Chromium 153.0.8010.12

## Required checks

- `python3 -m unittest discover -s tests -v`: PASS — 275 tests, 1 environment-based skip.
- `python3 scripts/run_legacy_checks.py`: PASS — manifest verification, 26 specification tests, 12 staged-solution tests, and all four study-level checks.
- `python3 -m compileall -q src tests`: PASS.
- `git diff --check`: PASS.
- `npm --prefix webui run check`: PASS — metadata, lockfile, license, and JavaScript syntax checks.
- `npm --prefix webui run test:browser -- tests/harness.spec.mjs`, repeated three consecutive times: PASS — 6/6 each run.
- `npm --prefix webui run test:browser`: PASS — 101/101 tests on the final run.

## Failure and cleanup evidence

The first full browser gate run found one intentional stale `/api/prompts/2` cancellation in the narrow keyboard-navigation test. The strict request guard rejected it and Playwright temporarily produced failure-only files under `webui/.test-results/shell_contract-traverses-e-f500d-ut-narrow-viewport-clipping-chromium/`. The test now declares that exact cancellation as expected; its focused rerun passed 1/1 and the complete rerun passed 101/101.

The opt-in failure probe also proves that configured Playwright `trace.zip` and screenshot artifacts are created on failure, scanned for raw token/path/source/prompt/body sentinels, and removed in a `finally` cleanup. Successful runs retained no trace, screenshot, attempt, cache, or fixture workspace. The runner-only `.last-run.json` was removed after verification.

No relevant build warnings or regressions were observed. The repeated `NO_COLOR`/`FORCE_COLOR` notice comes from the test runner environment and does not affect the product or verification result.
