# Final remote project reproduction

## Published identity and fresh setup

Created owned root `/private/tmp/cb0001-release.HTxOTs/remote-project.m4paFW`
using mktemp. Cloned actual GitHub remote with `git clone --branch main
--single-branch git@github.com:lancekrogers/codesignal-practice-simulator.git
<owned-root>/project`. No local URL rewrite/cache copy/hardlink rehearsal.
HEAD verified exactly `600c6cff0bd9428c6cf605e24085ea8729a475d2`; status clean.

Fresh .venv from retained Python3.14.6 builder; installed setuptools==84.0.0
then `pip install --no-build-isolation --no-deps -e <clone>`. Locked npmci used
`--ignore-scripts --no-audit --no-fund`, nine packages. Console and module help
both passed. No real attempt created.

Existing CLI `fetch --workspace-root <clone>` populated only the ignored cache;
explicit `scripts/verify_manifest.py --manifest docs/migration-manifest.json
--scope fixture-cache` passed. Narrow approved exception: seven pinned hash-
checked files, no protected-content inspection/copy/upstream-test execution.

## Canonical published-commit verification

`env PATH="<clone>/.venv/bin:$PATH"
ASSET_BUILDER=/private/tmp/cb0001-release.HTxOTs/builder/bin/python
just python=<clone>/.venv/bin/python verify` passed:

- 289 maintained Python tests in105.083s, no skips;
- 4 explicit E2E tests in27.536s, no skips;
- tracked/cache/Git-boundary verification,26 first-party spec tests,12 staged
  tests and all4 study levels;
- whitespace check.

## Installed-wheel and final boundary proof

Metadata/lock/license and all13assets passed. From this actual remote clone,
`ASSET_BUILDER=/private/tmp/cb0001-release.HTxOTs/builder/bin/python
.venv/bin/python scripts/run_packaged_browser.py` passed **171 browser cases**,
no skips, default privacy reporters. Archive inspection passed94sdist/49wheel/
14static members;13asset hashes and7synthetic records. Console/module web each
served13assets from isolated site-packages, runtime PATH without Node/npm/npx.
Owned wheel temporary environment `codesignal-browser-wheel-cva9olsv` was
removed by the script and independently confirmed absent.

Final exact600c HEAD, empty full porcelain status, whitespace, ignored .venv/
node_modules/cache, absent actual attempts, and all three manifest scopes passed.
After every process exited, `/usr/bin/trash` moved the exact owned remote-project
root; its original path and the separate remote-campaign clone path were verified
absent. Recovery remains possible through Trash. Shared builder retained until
final reviewer disposition/closure. No product changes or protected bytes retained
in project/campaign history. This establishes published-commit reproduction,
not merely local working-tree equivalence.
