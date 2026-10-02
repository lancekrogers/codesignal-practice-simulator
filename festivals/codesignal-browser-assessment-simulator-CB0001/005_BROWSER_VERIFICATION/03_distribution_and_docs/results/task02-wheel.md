# Task 02 — wheel and offline installation verification

Verified on 2026-09-10 from clean base `83b76f7` with:

`ASSET_BUILDER=/private/tmp/cb0001-release.HTxOTs/builder/bin/python`

## Result

The final installed-wheel run passed. It built an sdist and wheel, installed the
wheel offline into a fresh Python 3.14 venv, checked package and CLI origins,
launched both public web entry points, and passed the complete installed browser
suite with the default privacy-safe reporters.

## Commands and counts

- `ASSET_BUILDER=... python3 -m unittest tests.test_asset_verification.DistributionTests tests.test_asset_packaging.IncrementalPackagingTests -v`
  — 7 passed.
- `npm --prefix webui run test:browser -- continuity_controls.spec.mjs success_cleanliness_reporter.spec.mjs`
  — 2 passed.
- `npm --prefix webui run test:browser -- harness.spec.mjs --grep "arms streaming before fast same-origin responses finish" --repeat-each=3`
  — 3 passed.
- `git diff --check` and Python/Node syntax checks — passed.
- `ASSET_BUILDER=... python3 scripts/run_packaged_browser.py`
  — 161 browser tests passed with the configured default reporters.
- A final temporary wheel was inspected with `unzip -l`
  — 49 total wheel members, 44 package members, and 14 static package members.

The first full rehearsal reported 159 passed and one failure in the existing
fast-response streaming harness test. The exact test then passed three
consecutive repetitions, and the final complete installed suite passed 161/161.
The failure was therefore classified as a non-reproduced harness timing failure,
not a wheel-runtime or import-origin failure.

## Archive and installation proof

- Final archive inspection found 93 sdist members and 49 wheel members.
- The 13 manifest assets plus static `__init__.py` were the exact 14 static
  package members in both archives.
- Every wheel and sdist asset byte matched the source manifest digest.
- `ASSET_PROVENANCE.txt`, `NOTICE.txt`, Monaco workers, styles, font, hashed
  assets, and aliases were present.
- Package-data suffix rules in `pyproject.toml` covered every manifest asset.
- Duplicate and forbidden archive paths were rejected using the full existing
  cache/build/output policy plus attempt/reference/solution/study/vendor paths.
- Wheel installation used `pip install --no-index --no-deps`.

The installed origin probe resolved these modules under the fresh venv and
outside the checkout:

- `.../environment/lib/python3.14/site-packages/codesignal_practice_simulator/__init__.py`
- `.../environment/lib/python3.14/site-packages/codesignal_practice_simulator/cli.py`
- `.../environment/lib/python3.14/site-packages/codesignal_practice_simulator/web/resources.py`
- `.../environment/lib/python3.14/site-packages/codesignal_practice_simulator/web/static/__init__.py`

Installed browser and continuity children ran with an outside-checkout cwd,
`PYTHONHOME` and `PYTHONPATH` absent, no checkout entry in `sys.path`, and a
venv-only runtime `PATH` in which `node`, `npm`, and `npx` were unavailable.
The focused continuity regression directly recorded and asserted that child cwd
and environment.

## Proof scopes

The console and module probes used the unmodified installed wheel and an empty
workspace:

- installed `codesignal-sim web --no-open --json` bound
  `http://127.0.0.1:58978` and served all 13 manifest assets with exact digests;
- installed `python -m codesignal_practice_simulator web --no-open --json`
  bound `http://127.0.0.1:58992` and served the same 13 assets.

These probes prove the public entry points and packaged static server. They did
not replace or rewrite the pinned wheel manifest and did not inject synthetic
assessment bytes.

The separate installed-browser fixture copied the existing fixture builder and
controls into the owned temporary root. It generated exactly seven synthetic
records for the full entry/start/edit/save/test/submit journey. The browser
harness imported simulator modules from the wheel, and continuity calls used the
installed `codesignal-sim` console entry point. This fixture scope does not claim
that the public console web probe used an injected application.

Browser routing denied non-loopback requests. The installed Python fixture added
a loopback-only socket audit guard and successfully self-probed denial of an
external address. Response scanning and the browser suite verified all manifest
assets, including Monaco workers, without runtime Node.

## Cleanup

The owned wheel, sdist, venv, copied fixture driver, synthetic cache/workspaces,
attempts, Playwright metadata, traces, and failure output were removed after
verification. The default reporter first enforced its existing rule that only
`.last-run.json` may remain after a successful run; the runner then removed that
owned output directory. The coordinator-owned builder root was preserved.

No commit, festival status change, or task 03 work was performed.
