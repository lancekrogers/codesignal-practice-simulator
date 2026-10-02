# Combined release-remediation verification

Both Cursor implementation agents exited before these checks. Changes are
limited to candidate history reconstruction, scorer output collection, and
focused synthetic tests. Detailed failing-before/passing-after evidence is in
`history-remediation.md` and `scorer-remediation.md`.

## Canonical checkpoint

- `ASSET_BUILDER=/private/tmp/cb0001-release.HTxOTs/builder/bin/python just verify`
  passed: 289 Python tests in 104.771s, then four explicit E2E in 28.033s,
  no skips. Tracked/cache/Git-boundary checks, 26 first-party spec checks,
  12 staged checks, all four study levels and whitespace checks passed.
- `python3 -m compileall -q src tests scripts` passed.
- `node --check webui/tests/candidate_journey.spec.mjs` passed.
- `npm --prefix webui run check` passed (metadata/lock/license, not TypeScript).
- `python3 scripts/check_assets.py` passed all 13 unchanged assets; manifest
  SHA256 `19d284d6377c9f74db84fd4051116fc8834d2df090cb7dc8ef5c502fb14e48bd`.
- `git diff --check` passed; only seven intended project files changed.

No protected source was inspected. Canonical legacy checks execute first-party
checks and only hash the approved cache. All candidate/browser tests synthetic.
The corrected runtime is no longer tree-identical to prior b61d136/62d950c
clone evidence; fresh corrected-commit reproduction remains mandatory.

## Exact corrected-commit installed-wheel check

Committed as `600c6cff0bd9428c6cf605e24085ea8729a475d2`, with clean project
status before and after. `ASSET_BUILDER=/private/tmp/cb0001-release.HTxOTs/builder/bin/python
python3 scripts/run_packaged_browser.py` passed all **171** synthetic browser
cases, no skips, default privacy reporters. Installed console and module web
entry points each served all13assets; runtime imports came from isolated
site-packages, runtime PATH had no Node/npm/npx. Archive checks:94sdist members,
49wheel members,14static members,7synthetic records. All13asset hashes unchanged.
Owned temporary wheel/venv/fixtures/attempts/traces were removed by the script
from `codesignal-browser-wheel-v8dmkpbj`.

Independent final reviews and corrected-commit clone checks remain in progress.
No final release approval is claimed here.

## Focused supported-interpreter recheck

On exact600c, ran the four candidate-document modules plus test_scoring and
test_web_server_evaluation using each retained isolated interpreter:
Python3.10.20:46passed in5.107s; Python3.11.16:46passed in5.007s;
Python3.12.13:46passed in5.190s. No skips or failures. Python3.14.6 ran the
full289+4 canonical suite above. Python3.13 and other OSes remain unverified.
The wheel temporary path was independently confirmed absent after cleanup.
