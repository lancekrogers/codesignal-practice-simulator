# Approved campaign-clone verification — 2026-09-10

Scope: local clean-clone rehearsal under the operator-approved exception in
`fixture-exception.md`. This is not yet final remote release reproduction.

## Identity and isolation

- Campaign cloned with `git clone --no-hardlinks --no-recurse-submodules` into
  `/private/tmp/cb0001-release.HTxOTs/approved-campaign-clone`.
- Campaign HEAD: `905b011b0341514d797a35bd95cb9072cb0fbdba`; initial status clean.
- Only in the temporary clone: configured the simulator's local repository URL,
  staged reviewed gitlink `b61d136f2fd938ef7236c1d4331ae32fb561fd2b`, and ran
  targeted `git -c protocol.file.allow=always submodule update --init --
  projects/codesignal-practice-simulator`. No other submodule initialized.
- Simulator HEAD exactly matched that reviewed commit. Committed festival wheel
  evidence was present. The sole campaign index difference was the target gitlink.

## Commands and outcomes

From the cloned simulator:

- `python3 scripts/fetch_fixture.py --manifest docs/migration-manifest.json`:
  exit 0; existing atomic fetch validated exactly seven pinned records in the
  ignored cache. No existing cache copied and no fetched contents inspected.
- `npm --prefix webui ci --ignore-scripts --no-audit --no-fund`: exit 0,
  nine locked development packages installed.
- `ASSET_BUILDER=/private/tmp/cb0001-release.HTxOTs/builder/bin/python just verify`:
  exit 0; tracked, fixture-cache and git-boundary scopes passed; 26 legacy spec
  tests, 12 staged tests and all four study levels passed; 276 Python tests
  passed without skips, followed by four explicit end-to-end tests and whitespace.
  The legacy runner executes first-party checks, not fetched upstream tests.
- `npm --prefix webui run check`: metadata, lockfile and licensing checks passed.
  This recipe does not run a TypeScript type checker; no such result is claimed.
- `python3 scripts/check_assets.py`: all 13 assets passed. Manifest SHA256:
  `19d284d6377c9f74db84fd4051116fc8834d2df090cb7dc8ef5c502fb14e48bd`.
- `git status --short --untracked-files=all`: empty in the simulator.
- `git check-ignore` confirmed the fetched cache and `webui/node_modules` ignored.

Browser lifecycle and end-to-end tests use synthetic fixture workspaces. No real
assessment attempt was started. The fetched records were used only for the
canonical hash-verification prerequisite.

## Cleanup and remaining release evidence

After all processes completed, the exact owned campaign clone was moved to macOS
Trash and its original path was verified absent. This removed its cache, dependency
directory and temporary staged gitlink from the working location; recovery remains
possible from Trash. The shared builder was retained for subsequent release checks.
The actual campaign pointer and unrelated dirty submodules were not changed.

Final remote clone/pointer proof follows release review and authorized publishing;
the staged-pointer rehearsal above is not presented as already published state.
