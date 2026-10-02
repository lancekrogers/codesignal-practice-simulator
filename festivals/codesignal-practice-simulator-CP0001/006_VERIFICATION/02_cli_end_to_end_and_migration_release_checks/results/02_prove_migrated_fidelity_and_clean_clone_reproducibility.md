# 006.02.02 Verification Evidence

Date: 2026-09-09

## Compatibility profile and prerequisites

- Project commit: `f1a178ae5276dd36cdba7c450dcc2fe39b5d49d3`
- Campaign commit: `a4365835cebab4a68fb63bf5599d2d5ec905ea07`
- Campaign submodule commit: `f1a178ae5276dd36cdba7c450dcc2fe39b5d49d3`
- Interpreter for both direct routes: Python 3.10.20
- Installer: fresh virtual environments with bundled pip/setuptools/wheel;
  `pip --no-index --no-deps --no-build-isolation --disable-pip-version-check -e`
- Fixture prerequisite: the original retained explore source containing upstream
  `README.md` plus the six `practice_assessments/file_storage/` files.
- Network use during package installation and fixture setup: none.

## Clone and setup commands

The rehearsal allocated `/tmp/codesignal-release.Y3RD1u`, then ran:

```text
git clone --no-local /workspace/campaign <run>/campaign
git -C <run>/campaign submodule update --init --recursive --jobs 4
git clone --no-local /workspace/campaign/projects/codesignal-practice-simulator <run>/project
python3.10 -m venv <run>/project-env
<run>/project-env/bin/python -m pip install --no-index --no-deps --no-build-isolation --disable-pip-version-check -e <run>/project
python3.10 -m venv <run>/campaign-env
<run>/campaign-env/bin/python -m pip install --no-index --no-deps --no-build-isolation --disable-pip-version-check -e <run>/campaign/projects/codesignal-practice-simulator
```

The source fixture was created outside both Git trees and contained exactly
seven files. Each clone then ran `scripts/fetch_fixture.py --source
<run>/fixture-source` and reported its own validated ignored cache path.

## Direct verification output

Both the standalone project clone and campaign submodule independently
reported:

```text
Manifest verification passed: tracked
Manifest verification passed: fixture-cache
Manifest verification passed: git-boundary
solution/test_spec.py: Ran 26 tests ... OK
solution/test_stages.py: Ran 12 tests ... OK
study/check.py level1.py: Level 1 PASS
study/check.py level2.py: Levels 1-2 PASS
study/check.py level3.py: Levels 1-3 PASS
study/check.py level4.py: Levels 1-4 PASS
Canonical legacy checks passed.
python -m unittest discover -s tests -v: Ran 158 tests ... OK
git diff --check: exit 0, no output
git status --short: exit 0, no output
```

The clean campaign submodule also ran optional `just verify`:

```text
Canonical legacy checks passed.
Ran 158 tests ... OK
Ran 4 tests in 15.384s ... OK
git diff --check: exit 0
```

The runner command list contains no `test_simulation.py`; the fetched upstream
test was hash-verified but never executed by canonical verification.

## Seven cache hashes

Both caches produced the same verified digests:

```text
vendor-readme.md b4c2fbb6810f5969b1cfaea9534369b7a1b1ba40fe759d9951804e727823eca5
assessment/file_storage/level1.md 0529eb7272952842e50957a3823a063ad1f46c426d236c4f4cdaaba90a247a5b
assessment/file_storage/level2.md 78a7c6f8fa4078b570af16399f158f30f91f5bc91e51c55171b4580c91f11695
assessment/file_storage/level3.md 45218db3791433e8f089ef34c1c550205951e971300ca3ecfa08411f2caae7f0
assessment/file_storage/level4.md 5e1f8bae5e82ea9a61cef9eaae512e9bc6df60a7473bd2ade1b20b1715c59736
assessment/file_storage/simulation.py 3f402921360fc7fc3deb30392425873844268ade3515fb74e0c909f30c809fdc
assessment/file_storage/test_simulation.py 3bc1451a1c10b5a77624e66a2dc32ea57e14446919b07378941e56fcbfcfa51a
```

## Boundary and cleanup proof

```text
VISIBILITY=PRIVATE
FIXTURE_FILE_COUNT=7
PROJECT_STATUS=
CAMPAIGN_STATUS=
SUBMODULE_STATUS=
SUBMODULE_GIT_LINK=PASS
PROJECT_CLONE_VERIFICATION=PASS
CAMPAIGN_SUBMODULE_VERIFICATION=PASS
RELEASE_TEMP_CLEANUP=PASS
```

The per-run tree was deleted only after all checks completed, and its absence
was asserted.
