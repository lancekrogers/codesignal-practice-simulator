# Documentation install correction and executable proof

The coordinator tested the draft quick-start in a fresh owned Python 3.14 venv.
`pip install --no-build-isolation --no-deps -e .` failed with exit 2 because
the fresh venv did not contain `setuptools.build_meta`. The README now preserves
normal pip build isolation for its first quick-start command, and states that
installation may use network to provision the backend. A documentation regression
assertion prevents reintroducing no-isolation before prerequisites are installed.

Verified in `/private/tmp/cb0001-release.HTxOTs/docs-install-probe`:

- `python -m pip install --no-deps -e .` (with the optional pip version-notice
  suppression flag): exit 0; isolated backend provisioned, editable package installed.
- Provisioned a local wheelhouse using pip download for setuptools, wheel, build
  and their dependencies. No assessment fixtures were downloaded or read.
- `python -m pip install --no-index --find-links <owned-wheelhouse>
  'setuptools>=61' wheel 'build>=1.2'`: exit 0, entirely local install.
- `python -m pip install --no-index --no-build-isolation --no-deps -e .`:
  exit 0 after those explicit prerequisites.
- `python -m build --no-isolation --outdir <owned-docs-dist>`: exit 0;
  both sdist and wheel built successfully from the corrected documentation state.
- `python3 -m unittest tests.test_documentation -v`: all six tests passed.
- `git diff --check`: passed. No runtime code or generated static assets changed.
- Added the missing locked Chromium provisioning command to the browser-check
  instructions. `npm --prefix webui run install:browser` exited 0 using the
  existing locked browser installation. The docs explicitly distinguish this
  potentially networked development setup from offline application runtime.

The installed console and module `--help` commands also exited 0. After these
checks, the exact owned install-probe, wheelhouse and docs-dist directories were
moved to Trash and their original paths verified absent. The shared release
builder environments were preserved. This record supersedes task04's agent-level note that
the default system Python lacked a build CLI; the explicitly provisioned interpreter
has now executed the documented build path successfully.
