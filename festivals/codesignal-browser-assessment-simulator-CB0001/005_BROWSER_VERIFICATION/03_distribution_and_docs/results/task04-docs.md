# Task 04 — operating documentation

Completed 2026-09-10 in the linked simulator worktree. Scope was operating
documentation and its source-level regression test only; production runtime
code, generated assets, the pinned manifest, and fixtures were unchanged.

## Documentation coverage

- README now presents browser interaction and CLI operations as equivalent
  transports for one attempt, while retaining legacy CLI and optional Just
  workflows.
- Installation guidance distinguishes editable and offline wheel installs,
  explicitly separates FETCH_ONLY fixture setup, and states fresh-venv
  `setuptools`, `wheel`, and `build` prerequisites for no-isolation package
  commands.
- Browser operation documents loopback `web --port 0 --no-open`, private
  capability handling, confirmation/no-pause timer semantics, source
  autosave/CAS conflicts/history, refresh/reconnect, test versus submit, and
  the expired-browser/CLI-submit transition.
- Capability wording is precise: the fragment is not part of the HTTP URL;
  the browser later uses the capability in the same-origin
  `X-Simulator-Token` header, so neither URL nor header value is retained.
- Wheel wording is precise: it contains first-party pinned metadata and local
  browser assets, never fixture bytes or development scripts.
- Troubleshooting covers missing cache, port/opener, unavailable session,
  Monaco assets, stale source, final states, offline setup, and
  workspace-scoped cleanup. It does not offer a standalone unresolved-variable
  deletion command.
- Agent policy and safety docs preserve explicit candidate source/history
  permission, same-user non-sandbox limitations, and the absence of any
  official hidden-test equivalence claim.

## Verification

| Command | Result |
| --- | --- |
| `python3 -m unittest tests.test_documentation -v` | Passed: 6 tests |
| `git diff --check` | Passed |
| `PYTHONPATH=src python3 -m codesignal_practice_simulator web --help` | Passed: confirmed `--workspace-root`, `--port`, and `--no-open` |
| Documentation link/command scan across README, operating docs, and policy | Passed: 13 local links resolved; 6 README CLI subcommands were all supported |
| `python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary` | Passed |
| `npm --prefix webui run check` | Passed: metadata, lockfile, license, and Node syntax checks; no TypeScript type checker is invoked |

The documentation regression initially failed while its new assertions still
expected the superseded “fragment never travels in requests” wording and
line-wrapped strings. Those test assertions were corrected with the
documentation; the final run passed. No product test failed.

## Provenance and bounded non-runs

Task 01 matrix and task 02 wheel evidence provide the prior multi-version
build, wheel, installed-browser, and runtime-without-Node proof. The task 03
approved clone evidence confirms the documented frontend check behavior and
fixture-cache boundary. This task did not repeat the full browser or canonical
suite; task 05 is responsible for that sequence-level verification.

`python3 -m build --version` exits 1 in this worktree because its current
default Python resolves a non-CLI `build` module rather than the required
`build>=1.2` distribution. No package build was attempted here. The README
therefore requires provisioning the documented build tools in the target
environment, and the prior task 01/02 release evidence remains the executable
proof for the distribution build command.

No real attempt was started, no FETCH_ONLY bytes were read or fetched, and no
capability URL or candidate source was retained. No commit or festival task
status change was made.
