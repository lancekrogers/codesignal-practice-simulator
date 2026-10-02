# Entry and shell testing

Date: 2026-09-09

Versions:

- Python 3.14.6 for application and legacy suites
- Python 3.11 packaging interpreter from the isolated asset-builder environment
- Node.js 26.7.0
- npm 11.19.0
- Playwright 1.63.0
- Monaco Editor 0.56.0

Commands and final results:

- `ASSET_BUILDER=/tmp/codesignal-build-env-48721/bin/python python3 -m unittest discover -s tests -q`
  - 261 tests passed; no skips; 98.351 seconds after review fixes.
- `python3 scripts/run_legacy_checks.py`
  - Tracked, fixture-cache, and Git-boundary manifest verification passed.
  - 26 legacy specification tests and 12 staged-solution tests passed.
  - Study levels 1 through 4 passed their cumulative checks.
- `python3 -m compileall -q src tests`
  - Passed.
- `git diff --check`
  - Passed.
- `npm --prefix webui run check`
  - Metadata, lockfile, exact versions, provenance, and licenses passed.
- `npm --prefix webui run check-assets`
  - 13 manifest-declared assets passed integrity, type, cache, containment,
    license, and content checks.
  - Manifest SHA-256: `2dad4825cc8cf1db7092ea978f5a2a4264eb8de68e12c30bd24b9871317a5e93`.
- `npm --prefix webui run test:browser`
  - 32 real-browser tests passed in 35.4 seconds against the real Python
    loopback server with the strict same-origin/offline request policy.
- `npm run test:browser -- shell`
  - 23 focused shell tests passed.
- `python3 scripts/run_packaged_browser.py`
  - 32 browser tests passed in 31.3 seconds against an isolated installed wheel.
- Incremental packaging regressions
  - The original installed-wheel test and seeded stale-build tests passed.
  - Unsafe source-overlap and symlinked build outputs fail closed without
    source or outside-target mutation.

Coverage evidence:

- Full and drill selection, cancel, confirmation, exactly-one authoritative
  attempt creation, concurrent duplicate Start rejection, and refresh/reconnect
  continuity are covered.
- Desktop and narrow layouts, semantic landmarks, no document-level horizontal
  clipping, keyboard traversal, roving tab stops, dialog focus containment and
  restoration, visible focus, and reduced-motion behavior are covered.
- Monotonic countdown, successful and failed resynchronization, prompt response
  races, terminal cleanup, expiry, submission, safe errors, and forbidden-text
  exclusion are covered.
- Every browser test rejects unexpected origins, relevant HTTP failures,
  console errors, and page errors.
- A ten-repeat focus stress run initially exposed an asynchronous dialog-focus
  race. Initial focus was made synchronous, the stress and full suites passed,
  and its temporary screenshot/trace were deleted.

Failure-only artifacts retained: none.
