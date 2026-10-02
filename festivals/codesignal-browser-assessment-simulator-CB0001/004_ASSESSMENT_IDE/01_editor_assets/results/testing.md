# Editor asset testing

Date: 2026-09-09

Versions:

- Python 3.14.6 for the application suites
- Python 3.11.16 with `build` 1.6.0 for distribution construction
- Monaco Editor 0.56.0
- esbuild 0.28.2
- Playwright 1.63.0

Commands and results:

- `ASSET_BUILDER=/tmp/codesignal-build-env-48721/bin/python python3 -m unittest discover -s tests -v`
  - 248 tests passed; no skips (final approved-state rerun used `-q`).
- `ASSET_BUILDER=/tmp/codesignal-build-env-48721/bin/python python3 -m pytest -q`
  - 258 tests and 162 subtests passed; no skips.
- `python3 scripts/run_legacy_checks.py`
  - All tracked, fixture-cache, and Git-boundary manifest checks passed.
  - 26 legacy specification tests and 12 staged-solution tests passed.
  - Study levels 1 through 4 passed their cumulative checks.
- `python3 -m compileall -q src tests`
  - Passed.
- `git diff --check`
  - Passed.
- `npm --prefix webui run check`
  - Lockfile, exact-version, provenance, and license checks passed.
- `npm --prefix webui run build`
  - Passed with deterministic generated output and no relevant warnings.
- `npm --prefix webui run test:browser`
  - 4 tests passed against the real Python server.
- `ASSET_BUILDER=/tmp/codesignal-build-env-48721/bin/python python3 -m unittest tests.test_asset_verification -v`
  - Asset, archive, clean-build, and installed-wheel tests passed; no skips.
- `ASSET_BUILDER=/tmp/codesignal-build-env-48721/bin/python python3 -m unittest tests.test_asset_verification tests.test_web_resources tests.test_web_server -v`
  - 60 focused asset, publication, recovery, resource, and route tests passed; no skips.
- `ASSET_BUILDER=/tmp/codesignal-build-env-48721/bin/python python3 scripts/run_packaged_browser.py`
  - An isolated wheel was built and installed outside the checkout.
  - 4 network-denied browser tests passed against the installed package.
- `python3 scripts/check_assets.py`
  - 13 declared assets passed size, SHA-256, MIME, cache, content, and containment checks.
  - Manifest SHA-256: `9573e91c0725cd5bc0a8487d46597e6ae5767557a59d033352dc0665af2eb3d6`.

Coverage and failure-path evidence:

- Two clean `npm ci --ignore-scripts` builds were byte-identical.
- Wheel and sdist static member sets and bytes matched the source manifest exactly.
- Browser requests outside the launched loopback origin were denied; required document, script, stylesheet, font, and worker responses were successful.
- Forced Monaco initialization failure preserved the exact server source in a read-only fallback, disabled mutations, and issued no mutation request.
- Stale capability storage, asset tampering, stale files, symlinks, cache directories, archive pollution, source-path leakage, fixture sentinels, secrets, and external network invocation forms have negative tests.
- Successful runs retained no screenshots, traces, attempt data, or fixture bytes.

Failure-only artifacts: none.
