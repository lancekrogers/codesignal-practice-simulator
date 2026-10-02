# Distribution matrix — task 01

Reviewed source: `83b76f7fa0467d041a24ac3015281b7b1f774ed9` (clean linked
worktree). Runs began against the identical staged tree before the candidate
sequence commit and completed against that commit. No source change occurred.

| Python | Full unittest | Explicit E2E | Legacy/provenance | sdist + wheel |
|---|---|---|---|---|
| 3.10.20 | 276 passed, no skips | 4 passed | Passed | Built |
| 3.11.16 | 276 passed, no skips | 4 passed | Passed | Built |
| 3.12.13 | 276 passed, no skips | 4 passed | Passed | Built |
| 3.14.6 | 276 passed, no skips | 4 passed | Passed | Built |
| 3.13 | Not installed | Not run | Not run | Not run |

Each available interpreter used a clean temporary build venv. Commands, with
`MATRIX_PYTHON` pointing to that interpreter and `DIST` to its owned temporary
output directory:

```sh
ASSET_BUILDER="$MATRIX_PYTHON" "$MATRIX_PYTHON" -m unittest discover -s tests -q
"$MATRIX_PYTHON" -m unittest tests.test_end_to_end -q
"$MATRIX_PYTHON" scripts/run_legacy_checks.py
"$MATRIX_PYTHON" -m build --no-isolation --outdir "$DIST"
```

Python 3.14's tests and legacy checks were run through `just verify` (verbose
discovery and explicit E2E), with the temporary builder supplied through
`ASSET_BUILDER`. Build tools were installed during setup, not fetched by the
runtime tests; `--no-isolation` builds require no dependency download. All runs
exited 0. Full suites/builds were serial in the shared checkout to avoid shared
setuptools-output collisions; the earlier failed parallel experiment and serial
correction are preserved in the preceding sequence's regression checkpoint.

Additional final commands:

- `npm --prefix webui run test:browser`: 160 passed, no skips, with default
  privacy-safe reporters and same-origin network denial; Node 26.7.0, npm
  11.19.0, Playwright 1.63.0, Chromium 153.0.8010.12 / revision 1243.
- `npm --prefix webui run build`: passed; `git diff --exit-code` remained clean.
- `npm --prefix webui run check`: metadata, lockfile, licenses and types passed.
- `python3 scripts/check_assets.py`: all 13 assets passed, manifest SHA-256
  `19d284d6377c9f74db84fd4051116fc8834d2df090cb7dc8ef5c502fb14e48bd`.
- `python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json
  --scope git-boundary`: passed for HEAD and staged index. Tracked mappings and
  fixture-cache hashes passed through each legacy run.
- Compilation and whitespace checks passed in the identical candidate sequence.

The static checker enforces declared asset membership/hashes, licensing, no
runtime external URLs or machine paths, and known secret/FETCH_ONLY patterns.
Git-boundary verification rejects pinned vendor hashes and forbidden paths.
First-party legacy solution/study checks remain permitted post-attempt material;
they are not served or included in the wheel.

Synthetic runtime workspaces are cleaned by the tests; passing browser output
was removed. The owned build environments and eight archives are retained only
for the immediately following installed-wheel verification, then scheduled for
cleanup. They are outside the checkout and no artifacts/logs/caches are tracked.
This matrix does not claim the pending clean-clone or installed-browser proof.
