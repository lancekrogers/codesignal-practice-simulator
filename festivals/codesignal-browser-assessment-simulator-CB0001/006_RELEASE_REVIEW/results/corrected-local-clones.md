# Corrected local clean-clone rehearsal — 2026-09-10

## Scope and isolation

This is the authorized local-only reproduction under the pinned-fixture
exception in `005_BROWSER_VERIFICATION/03_distribution_and_docs/results/fixture-exception.md`.
It does not establish remote or published-release proof.

- Created the fresh owned root with
  `mktemp -d /private/tmp/cb0001-release.HTxOTs/review-clones.XXXXXX`,
  yielding `/private/tmp/cb0001-release.HTxOTs/review-clones.AUufse`.
- Local project clone command:
  `git clone --no-hardlinks --branch browser-assessment-app <local-project>
  <owned-root>/project`. Its initial `HEAD` was exactly
  `600c6cff0bd9428c6cf605e24085ea8729a475d2`; initial full status was empty.
- Local campaign clone command:
  `git clone --no-hardlinks --no-recurse-submodules <JobSearch>
  <owned-root>/campaign`. Its initial `HEAD` was
  `23cee2179f7afe38619419d95519b1cbe9b335e8`; initial full status was empty.
- The retained shared asset builder was
  `/private/tmp/cb0001-release.HTxOTs/builder/bin/python`: Python 3.14.6
  with `build` 1.6.1. Both clone-local virtual environments used that Python,
  provisioned `setuptools==84.0.0`, and installed the project with
  `pip install --no-build-isolation --no-deps -e <clone>`.

No project source, product files, commits, pushes, or festival state were
changed. The only durable mutation from this rehearsal is this report.

## Project-clone evidence

- `npm --prefix webui ci --ignore-scripts --no-audit --no-fund` exited 0 and
  installed the nine locked packages.
- The existing editable `codesignal-sim fetch --workspace-root <clone>`
  completed successfully. The manifest declares exactly seven `fetches`;
  `scripts/verify_manifest.py --scope fixture-cache` passed. The fetched
  records remained in the clone's ignored cache.
- Canonical command, using the clone venv and retained builder:

  `env PATH="<clone>/.venv/bin:$PATH" ASSET_BUILDER="<shared-builder>"
  just python="<clone>/.venv/bin/python" verify`

  exited 0. It passed tracked, fixture-cache, and Git-boundary provenance
  checks; 26 legacy tests; 12 staged tests; study levels 1–4; 289 maintained
  Python tests in 104.208 seconds; four explicit end-to-end tests in 27.560
  seconds; and `git diff --check`.
- `npm --prefix webui run check` exited 0 (metadata, lockfile, and license).
  `scripts/check_assets.py` passed all 13 assets, with manifest SHA-256
  `19d284d6377c9f74db84fd4051116fc8834d2df090cb7dc8ef5c502fb14e48bd`.
- Both `<clone>/.venv/bin/codesignal-sim --help` and
  `<clone>/.venv/bin/python -m codesignal_practice_simulator --help` exited
  0; a direct package import passed.
- Final clone checks confirmed the target `HEAD`, empty full status,
  `git diff --check`, and that `.venv`, `webui/node_modules`, and the fixture
  cache were ignored.

The first canonical invocation incorrectly placed `-C` after `just`, which
just interpreted it as a nonexistent recipe and exited 1 before verification.
The command above is the immediately corrected, successful invocation. A
separate final-check wrapper initially used `git check-ignore -q` with multiple
pathnames; Git rejects that combination. Its corrected per-path checks passed.
Neither was a product or test failure.

## Limited campaign-clone smoke

Within only the campaign clone, the index was temporarily staged with:

`git update-index --add --cacheinfo
160000,600c6cff0bd9428c6cf605e24085ea8729a475d2,projects/codesignal-practice-simulator`

The local submodule URL was configured as
`submodule.codesignal-practice-simulator.url` pointing to the local main
project, then targeted update used
`git -c protocol.file.allow=always -c clone.local=false submodule update --init
-- projects/codesignal-practice-simulator`. It checked out the required
`600c6cff0bd9428c6cf605e24085ea8729a475d2`.

An earlier configuration used the submodule path as the config section, so
Git registered the `.gitmodules` GitHub URL and the target update failed with
“not our ref” before any checkout completed. The failed target worktree and
its temporary gitdir were moved to Trash (not removed with `rm -rf`), the
correct named local URL was configured, and the targeted local update above
then passed. No remote release, publication, or proof is claimed.

Post-update evidence:

- The campaign clone's sole index difference was
  `projects/codesignal-practice-simulator`; its submodule was at the required
  commit.
- All other submodule status entries retained the uninitialized `-` marker;
  the computed count of other initialized submodules was zero.
- Its own Python 3.14.6 / setuptools 84.0.0 venv completed editable install;
  console help, module help, and direct package import passed.
- The existing CLI fetch completed, the manifest again declared exactly seven
  fetches, and tracked, fixture-cache, and Git-boundary provenance checks
  passed. `check_assets.py` again passed all 13 assets with the same manifest
  SHA-256.
- No canonical suite, frontend build, frontend browser suite, packaged browser
  suite, browser launch, or real attempt was run in the campaign clone.

## Boundaries, cleanup, and limitations

- No fetched bytes were opened, copied, executed as upstream tests, committed,
  or retained outside the ignored caches. The cache was used solely by the
  approved hash-verification prerequisite.
- No browser server was started, so no capability URL was generated or
  retained. No real attempt was created.
- After all processes exited, `/usr/bin/trash` moved the exact owned clone root
  `/private/tmp/cb0001-release.HTxOTs/review-clones.AUufse`; its original path
  was verified absent. The shared builder root was retained.
- The real campaign gitlink was verified before and after cleanup as
  `f1a178ae5276dd36cdba7c450dcc2fe39b5d49d3`. Its pre-existing dirty
  submodules (names omitted from the public archive) were not modified. Other unrelated
  festival-result changes appeared concurrently and were likewise untouched.

This proves the specified local clean-clone path only. Remote clone/pointer
and published-artifact evidence remain release-stage work.
