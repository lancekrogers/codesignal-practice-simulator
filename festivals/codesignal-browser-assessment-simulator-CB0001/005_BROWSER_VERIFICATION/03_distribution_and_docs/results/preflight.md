# Distribution preflight — 2026-09-10

Read-only Cursor Luna Medium audit; this is preparation, not completed task or
execution evidence.

## Matrix and available tools

Available interpreters: Python 3.10.20, 3.11.16, 3.12.13, 3.14.6. Python 3.13 is
unavailable. Use the existing full unittest, explicit end-to-end, legacy,
compile, asset, browser and packaging commands. `just verify` covers Python,
legacy/provenance and whitespace; it does not run Playwright or build archives.

The harness sequence provisioned a temporary Python 3.14 environment with
`build`, `setuptools`, and `wheel`; its archive test passed using `ASSET_BUILDER`.
Recreate a temporary builder if that environment has been cleaned up. Do not
interpret the passing archive test as a completed packaged-browser smoke.

## Early executed compatibility check

`ASSET_BUILDER=<temporary-builder>/bin/python python3.10 -m unittest discover -s tests -q`
passed all 275 tests with no skips on 2026-09-10. The same command with
`python3.11` and `python3.12` also passed all 275 tests each with no skips. This checks the existing runtime
and packaging tests under Python 3.10, 3.11 and 3.12; it does not replace the final matrix,
browser, clean-clone or wheel-runtime gates.

## Confirmed issues to resolve

- `webui/tests/continuity_controls.mjs` always prepends the source checkout to
  `PYTHONPATH`; installed-mode CLI invocation must resolve the installed wheel.
- `scripts/run_packaged_browser.py` uses checkout-based Playwright tooling as a
  test driver. This is compatible with a wheel-only Python runtime, but evidence
  must separately prove the launched runtime cannot import source or execute Node.
- Clean clones must use the final committed project state, not the earlier
  `0ccdf6a` base. The campaign gitlink currently points at `f1a178a`; a temporary
  campaign rehearsal must identify and reconcile this difference without touching
  unrelated dirty submodules.

## Clean-clone legacy constraint

The canonical `scripts/run_legacy_checks.py` deliberately fails its fixture-cache
step when the seven pinned records are absent, then prints fetch guidance. A
synthetic browser fixture cannot satisfy those pinned hashes. Sequence 03 requires
synthetic-only clone setup and prohibits copying campaign caches, so it cannot
claim an unmodified clean-clone `just verify` success without resolving this
constraint. Preserve the strict provenance behavior; record actual outcomes and
do not silently substitute a synthetic cache for canonical fixture evidence.

## Documentation checks

Document proven editable/wheel commands, clarify runtime versus test-driver
dependencies, correct the continuity isolation issue, and map every documented
command to actual recorded results. The locked browser is Chromium revision 1243
with Playwright 1.63.0. No distribution task has been marked complete by this audit.
# Candidate review documentation follow-up

TG01 from the completed candidate-sequence review: explicitly document that the
expired browser is read-only and its Submit action is disabled. The existing
public API/CLI can finalize an expired attempt once; the timeout journey proves
that server/transport path, not a browser timeout-submit action. Add the proven
CLI recovery command and refresh/reconnect instructions in task 04 operating
documentation without changing lifecycle authority or inventing UI behavior.
