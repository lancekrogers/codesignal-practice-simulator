# Packaging review remediation

## Scope and disposition

- **Missing `wheel` preflight:** fixed. Interpreter discovery now imports
  `setuptools`, `pip`, `venv`, and `wheel`, plus `build` for the packaged
  browser check. Its failure message names every required capability and gives
  an `ensurepip`/`pip install` remediation and `ASSET_BUILDER` selection path.
- **Unexpected non-static package resources:** fixed. Archive inspection now
  rejects file members beneath the runtime package prefix unless they are a
  Python module, a member already covered by the existing static-member
  validation, or the declared `resources/fixture-manifest.json` metadata.
  This applies to wheel and sdist file members; tar directory entries are not
  treated as resources.
- **Whole-archive metadata catalog:** removed per coordinator scope correction.
  Existing archive-path and static-asset checks are preserved.

This resource policy does not prove arbitrary future Python module content is
safe. Source and provenance review remain required.

## Verification

Focused commands only; no archive builds or browser runs:

1. `python3 -m unittest tests/test_packaging_support.py`
   - Initial result: 6 tests, 2 failures and 1 error. The failures exposed a
     test-only sdist prefix assumption and a stale test helper name after the
     scope correction.
   - Final result: 6 tests passed in 0.004s.
2. `git diff --check && git diff -- scripts/packaging_support.py scripts/run_packaged_browser.py tests/test_packaging_support.py`
   - Result: passed before the final focused test run.

The six unit tests cover interpreter rejection/fallback, required-module probe
acceptance, actionable missing-capability guidance, and synthetic wheel/sdist
acceptance plus rejection of both direct and nested unexpected resource names.

## Archive-member counts

No real wheel or sdist was built or modified in this remediation, so no actual
archive member count changed (or was measured). The change only rejects
undeclared non-static package-resource members; it adds or removes no
distribution content. Coordinator-owned canonical/build/wheel verification
remains pending.

## Real prerequisite-import follow-up

Cursor Luna High session `03caed8e-5000-4f94-b266-ab29115dc550` replaced the
mocked command-shape assertion with a temporary stdlib venv (`with_pip=False`).
The child reports its executable and `sysconfig` site-packages path. Synthetic
setuptools/pip/build stubs are supplied; actual `_probe` rejects missing wheel,
then accepts after a synthetic wheel stub is added. Stdlib venv remains real.
This verifies import presence, not package build capability; real builds remain
the coordinator's integration check.

All six tests passed, exit 0, using `-m unittest tests.test_packaging_support`:

- `/opt/homebrew/bin/python3`: 0.245s.
- `/private/tmp/cb0001-release.HTxOTs/python310/bin/python`: 0.277s.
- `/private/tmp/cb0001-release.HTxOTs/python311/bin/python`: 0.508s.
- `/private/tmp/cb0001-release.HTxOTs/python312/bin/python`: 0.592s.

No browser or archive build ran. The agent initially wrote its aggregate note
under the project's `results/`; coordinator incorporated it here and removed
that duplicate so no misplaced evidence file enters the project commit.
