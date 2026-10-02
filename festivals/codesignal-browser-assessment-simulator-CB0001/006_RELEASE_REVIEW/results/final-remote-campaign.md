# Final remote campaign clone verification — 2026-09-10

## Scope

This is a fresh, remote-only campaign-clone release verification. It verifies
the published campaign pointer and the targeted project checkout; it does not
claim festival completion or substitute for the coordinator's independent
project-remote check.

The only durable mutation is this report. No product files, project source,
campaign files, commits, pushes, festival state, or real workspaces were
changed. No browser was started, no real candidate attempt was created, no
frontend build was run, and no fetched file contents were opened, copied, or
executed as tests.

## Remote clone and git proof

Owned clone root:

`/private/tmp/cb0001-release.HTxOTs/remote-campaign.MSZBOk`

Commands:

```text
git ls-remote --heads <campaign-repository> main
mktemp -d /private/tmp/cb0001-release.HTxOTs/remote-campaign.XXXXXX
git clone --branch main --no-recurse-submodules \
  <campaign-repository> <owned-root>/campaign
git -C <campaign> rev-parse HEAD
git -C <campaign> status --porcelain=v1 --untracked-files=all
git -C <campaign> diff --check
git -C <campaign> ls-tree HEAD projects/codesignal-practice-simulator
git -C <campaign> config --file .gitmodules --get \
  submodule.codesignal-practice-simulator.url
git -C <campaign> submodule update --init -- \
  projects/codesignal-practice-simulator
```

Proof:

- Remote `main` and fresh campaign `HEAD` were both exactly
  `033c75eb18535184a3d0e6185d3dc73a6758f4b4`.
- The committed campaign gitlink was exactly
  `160000 commit 600c6cff0bd9428c6cf605e24085ea8729a475d2
  projects/codesignal-practice-simulator`.
- The published `.gitmodules` URL was used unchanged:
  `git@github.com:lancekrogers/codesignal-practice-simulator.git`.
  No temporary index entry, local URL override, or protocol override was used.
- The only initialized submodule was the requested target. Its checkout `HEAD`
  was exactly `600c6cff0bd9428c6cf605e24085ea8729a475d2`, with the same `origin`
  URL. Of 11 declared submodules, the other 10 remained uninitialized
  (`other_initialized=0`).
- Before cleanup, both project and campaign had an empty full porcelain status
  and passed `git diff --check`.

## Isolated environment and verification

The project venv was created only in the fresh clone:

```text
<shared-builder> -m venv <project>/.venv
<project>/.venv/bin/python -m pip install setuptools==84.0.0
<project>/.venv/bin/python -m pip install --no-build-isolation --no-deps -e <project>
npm --prefix <project>/webui ci --ignore-scripts --no-audit --no-fund
<project>/.venv/bin/codesignal-sim fetch --workspace-root <project>
env PATH="<project>/.venv/bin:$PATH" ASSET_BUILDER="<shared-builder>" \
  just python="<project>/.venv/bin/python" verify
```

Versions and installation evidence:

- Shared builder: `/private/tmp/cb0001-release.HTxOTs/builder/bin/python`,
  Python `3.14.6`.
- Fresh project venv: Python `3.14.6`, `setuptools 84.0.0`.
- Node `v24.12.0`, npm `11.6.2`, and just `1.58.0`.
- Locked `npm ci --ignore-scripts` installed 9 packages; `npm run check`
  passed its metadata, lockfile, and license checks.
- The existing fetch CLI completed successfully. The declared manifest count
  was exactly 7 `fetches`; canonical tracked, fixture-cache, and Git-boundary
  manifest checks all passed.
- Existing console help, module help, and direct package import all passed.
- `scripts/check_assets.py` passed 13 assets; its manifest SHA-256 was
  `19d284d6377c9f74db84fd4051116fc8834d2df090cb7dc8ef5c502fb14e48bd`.

Canonical verification completed successfully in 135.237 seconds:

- provenance checks: tracked, fixture-cache, and Git-boundary — pass;
- legacy checks: 26 plus 12 tests — pass; study levels 1–4 — pass;
- maintained Python suite: 289 tests in 104.605 seconds — pass;
- explicit end-to-end suite: 4 tests in 27.765 seconds — pass;
- final `git diff --check` — pass.

The clone-local `.venv`, `webui/node_modules`, and
`.cache/codesignal-fixtures` were each confirmed ignored.

## Command issues and limits

- After the successful fetch, a standalone invocation of
  `scripts/verify_manifest.py --scope fixture-cache` exited 2 because this
  revision requires `--manifest`. The canonical recipe supplied
  `--manifest docs/migration-manifest.json` and passed every scope.
- A first final-check wrapper exited 127 after all substantive checks had
  passed because its zsh loop variable was named `path`, clobbering zsh's
  command-search array. The corrected wrapper used `candidate_path` and
  passed all ignored-path, submodule-count, remote, version, and clean-status
  checks. These were command-wrapper issues, not product failures.
- npm emitted the pre-existing shell completion diagnostic
  `compdef:153: _comps: assignment to invalid subscript range`; both npm
  commands still exited 0.
- This report deliberately does not assert final festival completion. The
  coordinator must still make its separate project-remote determination.

## Cleanup

After the verification processes exited, the exact owned clone root named
above is moved to Trash with `/usr/bin/trash` and its original path is checked
absent. The shared builder is intentionally retained. The real campaign root
and its unrelated dirty submodules were not accessed or changed.
