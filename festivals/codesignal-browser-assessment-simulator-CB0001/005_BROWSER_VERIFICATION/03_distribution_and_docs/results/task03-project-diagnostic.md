# CB0001 task03 project diagnostic

Bounded diagnostic only; task03 is blocked awaiting the fixture-policy decision. Reviewed commit:
`b61d136f2fd938ef7236c1d4331ae32fb561fd2b`.

## Clone and status

- Clone command: `git clone --no-hardlinks --branch browser-assessment-app "$PWD" /private/tmp/cb0001-release.HTxOTs/project-clone`
- Clone result: exit `0`; required destination did not exist before cloning.
- Clone HEAD: `b61d136f2fd938ef7236c1d4331ae32fb561fd2b` (exact match).
- Final `git status --short --untracked-files=all`: exit `0`, empty.
- Pinned cache `.cache/codesignal-fixtures/6aab304`: absent.
- After coordinator checks, the owned clone was moved to macOS Trash and its
  original path was verified absent. Recovery remains possible from Trash.

## Commands and results

| Command | Exit | Aggregate result |
|---|---:|---|
| `python3 scripts/run_legacy_checks.py` | 1 | Expected blocker: tracked manifest passed, then pinned fixture cache was absent. No fetch or fixture copy was attempted. |
| Coordinator `just verify` | 1 | Unmodified canonical recipe stopped at the same missing fixture-cache check, before Python discovery. |
| `ASSET_BUILDER=/private/tmp/cb0001-release.HTxOTs/builder/bin/python python3 -m unittest discover -s tests -q` | 1 | 276 tests; 265 passed, 11 failed, 0 errors. Failures were asset-builder/browser build cases; the reported browser build failure was missing `esbuild`. |
| Same discovery command after locked npm prerequisites | 0 | All 276 tests passed, no skips, in 102.255 seconds. Final status and whitespace checks clean; HEAD unchanged and pinned fixture cache still absent. |
| `ASSET_BUILDER=/private/tmp/cb0001-release.HTxOTs/builder/bin/python python3 -m unittest tests.test_end_to_end` | 0 | 4 tests passed. |
| `python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope tracked` | 0 | Passed. |
| `python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary` | 0 | Passed. |
| `python3 scripts/check_assets.py` | 0 | 13 assets verified; manifest SHA-256 `19d284d6377c9f74db84fd4051116fc8834d2df090cb7dc8ef5c502fb14e48bd`. |
| Final `git status --short --untracked-files=all` | 0 | Empty; clone clean. |

## Blocker

The canonical legacy check requires the missing pinned FETCH_ONLY cache. An
operator must approve the documented fetch before that check can proceed.
No approval was assumed, and no real fixture cache, attempt data, or
`FETCH_ONLY` bytes were read or copied. Full browser/npm installation was not
performed by the agent. The coordinator subsequently installed the nine locked
frontend test dependencies with `npm --prefix webui ci --ignore-scripts --no-audit
--no-fund` (exit 0) to resolve the missing build-tool prerequisite and rerun Python
discovery successfully (276/276). This installed no assessment fixtures. This diagnostic does not claim
task03 completion.
