# Distribution sequence final testing — passed

**Checkpoint qualification:** These are the passing task05 results before the
independent task06 review. Task07 is now correcting accepted guard and packaging
findings in `review.md`; a new final verification record is required in
`iteration.md` before commit. Do not treat these historical pass counts as proof
of the currently in-progress remediation diff.

Source checkpoint: `b61d136` plus final operating documentation, one documentation
regression case, and the test-only streaming guard correction. Final checks below
passed; intermediate failures and their dispositions remain recorded afterward.

## Final coordinator verification

- `ASSET_BUILDER=/private/tmp/cb0001-release.HTxOTs/builder/bin/python just verify`:
  exit 0, 277 Python tests without skips, four explicit E2E tests, 26 first-party
  legacy spec tests, 12 staged tests, all four study levels, tracked/cache/Git
  boundary verification, and whitespace passed.
- `ASSET_BUILDER=/private/tmp/cb0001-release.HTxOTs/builder/bin/python python3 scripts/run_packaged_browser.py`:
  exit 0, **166 browser tests passed without skips**, default reporters, isolated
  installed wheel/CLI, both public launch entry points, all 13 assets, seven
  synthetic fixture records, 93 sdist members, 49 wheel members, and 14 static
  members. The script verified removal of its temporary wheel, environment,
  fixtures, attempts and traces. This final run started after the implementation
  agent exited, with no other browser suite or editor running.
- A preceding installed-wheel run also passed 166 tests but briefly overlapped
  the agent's last checkout run because the coordinator started it too early.
  It is not used as the serialized cleanup proof; the final rerun above resolves
  that coordination error. No test failure or retained artifact resulted.
- Agent checkout verification: two full `npm --prefix webui run test:browser`
  runs passed 166 each. Focused regressions, 30 normalized-response repeats,
  24 harness cases and keyboard failure disposition are in `streaming-iteration.md`.
- `node --check webui/tests/network_guard.mjs`,
  `node --check webui/tests/harness.spec.mjs`, `npm --prefix webui run check`,
  `python3 scripts/check_assets.py`, `python3 -m compileall -q src tests`, and
  `git diff --check`: passed. The npm check is metadata/licensing, not type checking.
- Coordinator versions: Python 3.14.6, Node 26.7.0, npm 11.19.0, Playwright
  1.63.0 and locked Chromium 153.0.8010.12 (revision 1243), macOS ARM64.
- Guard/spec hashes before and after the final wheel run matched:
  `044d2d29bca7bf037090a6ec277db1859cad137c77e3400bb9ab11047f82f87d`
  and `ecb0522fc50b60e1f078d100b94f29ef8eded50a9097737abd508ec4915f7451`.
- Tracked diff contains only the seven intended documentation/test files. No
  runtime product or asset changes, attempts, caches, dependencies or diagnostics
  are being committed. Sequence-wide review includes already committed task02
  changes using base `83b76f7`, not just the current uncommitted diff.

## Executed checks

- `ASSET_BUILDER=/private/tmp/cb0001-release.HTxOTs/builder/bin/python just verify`:
  exit 0; 277 Python tests with no skips, four explicit E2E tests, tracked/cache/
  git-boundary manifest checks, 26 first-party legacy spec tests, 12 staged tests,
  all four study levels, and whitespace passed.
- `python3 -m compileall -q src tests`: passed.
- `npm --prefix webui run check`: metadata, lockfile and licensing passed; this
  does not perform TypeScript type checking.
- `python3 scripts/check_assets.py`: all 13 assets passed, unchanged manifest
  `19d284d6377c9f74db84fd4051116fc8834d2df090cb7dc8ef5c502fb14e48bd`.
- `python3 -m unittest tests.test_documentation -q`: six passed after the final
  quick-start and Chromium setup corrections.
- The same six final documentation tests also passed under the prepared Python
  3.10, 3.11 and 3.12 interpreters. This supplements the earlier full runtime
  matrix; it does not relabel that historical 276-test run as 277 tests.
- `npm --prefix webui run test:browser`: exit 1; 160 passed, one failed in
  `harness.spec.mjs` — “arms streaming before fast same-origin responses finish”.
  Default privacy-safe reporters remained enabled. Sanitized failure diagnostics
  were under `webui/.test-results/harness-arms-streaming-bef-b0ae3-ame-origin-responses-finish-chromium/`.

## Intermediate failures and completed iteration

Intermediate progress at that checkpoint (gate was still open): the scan-drain regression
first failed against the snapshot implementation and passed after correction.
Five focused checks and 40 repeated real-browser cases passed the first
intercepted-byte implementation. The subsequent whole run had 160 passed, one
keyboard-roving failure in `shell_layout.spec.mjs`, and three following serial
tests skipped. Those skips are serial fallout, not opted-out passing coverage.
The sanitized failure directory is
`webui/.test-results/shell_layout-roves-levels--4bcb5-bs-with-arrows-and-Home-End-chromium/`.

Coordinator review then identified JSON/default MIME and content-type override
false negatives in the draft scanner, plus unnecessary full-body copies. These
were corrected with focused regressions; see
`streaming-fulfill-semantics.md`. Read-only Cursor Terra High session
`8dc17605-caec-45e8-a23b-070c2703c611` independently inspects keyboard-navigation
ordering without running a competing suite. Its diagnosis is not a final review
gate. Final complete passing reruns are recorded above.

The streaming case also failed during an earlier wheel rehearsal, then passed
focused repeats and complete suites. Its recurrence is now a confirmed harness
reliability issue requiring investigation, not another “non-reproduced” dismissal.
A dedicated Cursor Sol High session `1012a200-20a5-4346-b2b5-4ddf44aa59bd`
owned the narrow investigation/remediation. It waited until the coordinator's full
suite process exited before editing or launching browser tests. See
`streaming-iteration.md` for cause, fix, limitations and rerun evidence.

No privacy guard, reporter, content bound, fixture boundary, or test threshold
may be relaxed merely to pass this gate. No real attempts or fetched source bytes
are in the browser test scope. Final independent sequence review follows passing
tests, not this intermediate record.
