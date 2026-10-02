# Task 03 — approved clean PROJECT clone verification

Verified on 2026-09-10 at reviewed commit
`b61d136f2fd938ef7236c1d4331ae32fb561fd2b`.

## Scope and clone

- `test ! -e /private/tmp/cb0001-release.HTxOTs/approved-project-clone`
  passed before cloning.
- `git clone --no-hardlinks --branch browser-assessment-app
  /workspace/campaign/projects/worktrees/codesignal-practice-simulator/browser-assessment-app
  /private/tmp/cb0001-release.HTxOTs/approved-project-clone` exited 0.
- Initial `git rev-parse HEAD` exactly matched the reviewed commit, and initial
  `git status --short --untracked-files=all` was empty.
- README, Just recipes, package metadata, Playwright configuration, and the
  existing scripts were read before running the documented flow.

Only the owned clone was mutated. The primary project worktree, festival
status, commits, task 04, and the shared builder root were not changed.

## Installation and entry points

- `npm --prefix webui ci --ignore-scripts --no-audit --no-fund` exited 0 and
  installed 9 locked frontend development packages.
- The external builder was present at
  `/private/tmp/cb0001-release.HTxOTs/builder/bin/python`: Python 3.14.6,
  `build` 1.6.1, and `setuptools` 84.0.0.
- The builder created `.venv`; `setuptools==84.0.0` was installed as the
  editable build backend, then `.venv/bin/python -m pip install
  --no-build-isolation --no-deps -e .` exited 0.
- Editable `.venv/bin/codesignal-sim --help` and
  `.venv/bin/python -m codesignal_practice_simulator --help` both exited 0.
- A captured `.venv/bin/codesignal-sim web --workspace-root . --port 0
  --no-open --json` launch bound loopback, returned a valid success envelope,
  and shut down cleanly on SIGINT. The capability URL was captured only for
  validation and suppressed from command output and this evidence.

## Approved pinned-fixture exception

- `.venv/bin/codesignal-sim fetch --workspace-root "$PWD"` exited 0 and used
  the documented fetch path to populate only the clone's ignored cache.
- `.venv/bin/python scripts/verify_manifest.py --manifest
  docs/migration-manifest.json --scope fixture-cache` exited 0.
- The manifest declared exactly seven fetches, and the existing fetch and
  verifier paths validated all seven pinned SHA-256 values: 7/7.
- No fetched source bytes were inspected, copied from another cache, executed
  as upstream tests, committed, or used to start a real attempt.

## Canonical and browser verification

- `env PATH="$PWD/.venv/bin:$PATH"
  ASSET_BUILDER=/private/tmp/cb0001-release.HTxOTs/builder/bin/python
  just python="$PWD/.venv/bin/python" verify` exited 0 with the unmodified
  recipe:
  - canonical legacy checks passed, including tracked, fixture-cache, and
    Git-boundary verification;
  - first-party solution tests: 26 passed;
  - first-party staged tests: 12 passed;
  - study checks passed through levels 1–4;
  - maintained discovery: 276 passed in 105.260 seconds;
  - hermetic end-to-end rerun: 4 passed in 27.786 seconds;
  - `git diff --check` passed.
- `npm --prefix webui run check` exited 0: metadata, lockfile, license, and
  Node syntax checks passed.
- `SIMULATOR_PYTHON="$PWD/.venv/bin/python"
  SIMULATOR_CLI="$PWD/.venv/bin/codesignal-sim"
  npm --prefix webui run test:browser` exited 0 with the configured default
  reporters and no overrides: 161 passed.
- `ASSET_BUILDER=/private/tmp/cb0001-release.HTxOTs/builder/bin/python
  .venv/bin/python scripts/run_packaged_browser.py` exited 0, sequentially
  after the checkout suite: 161 passed with default reporters. It verified 93
  sdist members, 49 wheel members, 14 static package members, 13 manifest
  assets, installed console/module web entry points, and 7 synthetic records.
  Its owned wheel, venv, fixtures, attempts, output, and traces were removed.

The runtime and browser test-driver dependencies are distinct. The Python
project declares no runtime dependencies, and the packaged wheel was installed
with `--no-index --no-deps`; its isolated runtime probe had no `node`, `npm`,
or `npx` available while both web entry points worked. Playwright 1.63.0,
Chromium, esbuild 0.28.2, Monaco 0.56.0, and their locked npm closure are
development/build/test-driver dependencies. Both complete browser runs used
the existing synthetic fixture driver for lifecycle/scoring behavior, never
the approved real cache.

## Final boundaries, failure record, and cleanup

The first aggregate final-check wrapper exited 1 only after its substantive
checks had passed because zsh reserves the variable name `status`
(`read-only variable: status`). The corrected wrapper used
`git_status_output`, repeated every check, and exited 0. This was a verification
wrapper failure, not a product or test failure.

The successful repeat proved:

- tracked, fixture-cache, and Git-boundary scopes passed;
- 13 assets passed with manifest SHA-256
  `19d284d6377c9f74db84fd4051116fc8834d2df090cb7dc8ef5c502fb14e48bd`;
- HEAD still exactly matched
  `b61d136f2fd938ef7236c1d4331ae32fb561fd2b`;
- `attempts/` was absent;
- `.venv`, `webui/node_modules`, and the fetched cache were ignored;
- `git diff --check`, tracked diff, staged diff, and
  `git status --short --untracked-files=all` were all clean.

After this evidence was written, the exact owned clone was moved with
`/usr/bin/trash` and its original path was verified absent. The shared builder
root was retained.
