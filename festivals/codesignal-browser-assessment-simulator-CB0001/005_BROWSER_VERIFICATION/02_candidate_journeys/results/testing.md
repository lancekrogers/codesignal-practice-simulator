# Candidate sequence — final verification

Executed against `be5389b` plus the staged candidate-journey sequence changes,
2026-09-10. No production source changed after these runs. Default Playwright
privacy/failure/cleanliness reporters were retained throughout.

| Command from project root | Final result |
|---|---|
| `npm --prefix webui run test:browser` | 160 passed, no skips, exit 0 |
| `npm --prefix webui run test:browser -- tests/candidate_journey.spec.mjs --repeat-each=3` | 15 passed |
| `npm --prefix webui run test:browser -- tests/accepted_journeys.spec.mjs -g 'expired attempt accepts' --repeat-each=3` | 3 passed |
| `ASSET_BUILDER=<temporary-builder-python> just verify` | 276 discovered Python tests, no skips; 4 explicit end-to-end tests; all legacy/provenance checks; exit 0 |
| `npm --prefix webui run check` | Metadata, lockfile, license and TypeScript checks passed |
| `python3 -m compileall -q src tests` | Exit 0 |
| `python3 scripts/check_assets.py` | 13 assets passed |
| `python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary` | Passed, including the staged index |
| Same verifier with `--scope tracked` | Passed |
| `git diff --check` and `git diff --cached --check` | Passed |

Versions: Python 3.14.6, Node 26.7.0, locked Chromium 153.0.8010.12 (revision
1243). The temporary Python builder includes build 1.6.1, setuptools 84.0.0,
and wheel 0.48.0, so archive verification did not skip for missing build tools.
The exact builder invocation is recorded in `regression-checkpoint.md`.

Legacy verification passed the tracked manifest, existing ignored fixture-cache
hashes, Git boundary, 26 specification checks, 12 staged checks, and all four
study levels. It did not execute fetched upstream tests or use real attempts.

## Failures and corrections

The initial full browser run was 157 passed, 1 failed, 2 skipped because the
new timeout-submit test checked reconnect visibility before bootstrap resolved.
It now waits for either valid final-state presentation; the small case passed
three repeats and the final full suite passed all 160. Earlier task-01 input
readiness and task-03 focus-order corrections are recorded in `evidence-index.md`.
The failed concurrent interpreter experiment and passing serial reruns are
recorded in `regression-checkpoint.md`; they are not silently counted as passes.

All current sequence failures have a fix and rerun evidence. No diagnostic
reporter was bypassed and no artifact was sanitized after a run to turn an
assertion green. No candidate source, tokens, attempt data or FETCH_ONLY bytes
are retained in this evidence. Distribution/wheel/clone/final-docs acceptance
remains the next sequence and is not claimed complete by these checks.
