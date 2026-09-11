# CodeSignal Practice Simulator

Practice a four-level, stateful CodeSignal-style exercise locally. Use the
browser for the interactive assessment and the CLI for an equivalent local
transport, automation, and recovery. Both use the same attempt.
Just recipes are optional shortcuts.

## Quick start with Just

From the project directory (tested with Just 1.58):

```sh
just setup                 # Install the editable Python app
just fetch                 # Explicit, pinned assessment download
just dev                   # Launch the web app and open its local browser URL
just dev --no-open         # Print the private URL without opening a browser
just dev --port 8000       # Choose a port instead of the default available port
```

`just dev` serves the bundled UI through the existing Python loopback server.
It does not start an assessment, fetch fixtures, install dependencies, or run
study checks. Confirming **Start practice** in the UI starts the timer. Stop
the server with Ctrl-C. Keep the printed capability URL private.

The root command list stays small; documented modules live in `.justfiles/`,
following the camp pattern. Run `just`, `just app`, `just build`, `just check`,
or `just study` to see each menu:

- `just app practice`, `just app drill 600`, `just app status`: CLI attempts.
- `just build deps`, then `just build assets`: install the locked frontend
  toolchain and rebuild assets after UI edits. Refresh the page afterward;
  there is no hot reload. Python changes require restarting `just dev`.
- `just verify`: the unchanged canonical verification sequence.
- `just check browser-install`, `just check browser`, `just check wheel`:
  explicit browser setup, synthetic browser tests, and installed-wheel checks.
- `just study`: explicit post-attempt commands, separate from development.

Existing flat CLI/study recipes still work as hidden compatibility shortcuts.
For another workspace, use `SIMULATOR_WORKSPACE=/path/to/workspace just dev`
(the same environment variable applies to `fetch` and `app` commands), or
`just workspace=/path/to/workspace dev`. Root `python=...` overrides are
forwarded by `setup` and `verify`; module overrides use Just's qualified form,
for example `just check::python=.venv/bin/python check unit`. `PYTHON` also
selects the interpreter across modules. Quote paths containing spaces.

The longer installation and verification prerequisites below still apply;
neither Node nor npm is needed just to launch the bundled app.

## Install, runtime, and FETCH_ONLY setup

Python 3.10+ is required and the simulator has no Python runtime dependencies.
For a development checkout, create and activate a virtual environment, then
install it editable:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --no-deps -e .
codesignal-sim --help
python3 -m codesignal_practice_simulator --help
```

The console command and `python3 -m codesignal_practice_simulator` have the
same commands, options, output envelopes, and exits. Substitute the module
form for `codesignal-sim` in every command below when a console script is not
convenient.

This normal editable install lets pip provision its isolated build backend and
may need network access during installation. For an offline machine, use the
separate pre-provisioned build-tool path below or install a previously built wheel.

For an offline editable install or a distribution build, a fresh environment
must already have `pip`, `setuptools>=61`, and `wheel`. The
`python -m build --no-isolation` command additionally needs `build>=1.2`.
Provision those build tools from your approved local wheelhouse before using
the no-isolation commands; do not assume every fresh Python venv includes
them:

```sh
python -m pip install --no-index --find-links /path/to/wheelhouse \
  "setuptools>=61" wheel "build>=1.2"
python -m pip install --no-index --no-build-isolation --no-deps -e .
python -m build --no-isolation --outdir dist
```

Run the maintained Python documentation check from the source checkout:

```sh
python -m unittest tests.test_documentation -v
```

For an offline runtime installation, install a previously built wheel without
resolving dependencies. A wheel contains the console entry point and all local
browser assets, but no development scripts or fixture bytes:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --no-index --no-deps /path/to/codesignal_practice_simulator-*.whl
codesignal-sim --help
```

Neither installation needs Node, npm, or network access to run `codesignal-sim
web`; the loopback server serves only bundled local assets. Building the assets
and running browser checks are separate development activities. In a source
checkout with the locked frontend dependencies available, use:

```sh
npm --prefix webui ci --ignore-scripts --no-audit --no-fund
npm --prefix webui run check
npm --prefix webui run build
```

`npm --prefix webui run check` checks frontend metadata, the lockfile,
licenses, and Node syntax; it does **not** run a TypeScript type checker.
`test:browser` and packaging checks also need their documented development
tools, not merely the installed wheel. The optional Python `test` extra
provides the build tool for distribution inspection; it is not a runtime
dependency.

The assessment is FETCH_ONLY: no license grant is recorded to redistribute its
README, prompts, starter, or bundled test. `fetch` validates the seven pinned
files and places them under the ignored workspace cache
`.cache/codesignal-fixtures/6aab304/`. Do not commit cache contents, upstream
requirements, or other vendor files.

```sh
codesignal-sim fetch --workspace-root "$PWD"
# Offline: codesignal-sim fetch --workspace-root "$PWD" --source /path/to/complete/source
```

The installed package contains only the first-party manifest and hashes, never
assessment bytes. `start` fails with exit 3 until that workspace's cache is
valid; rerun `fetch` rather than changing cache files by hand. Fetch is the
only explicit fixture-setup step: it may use its configured source, while an
already fetched workspace and all browser runtime assets work locally. For an
offline setup, point `--source` at a complete approved source tree; a wheel
does not include pinned fixtures.

## Timed workflow

Use a dedicated workspace. This example creates a temporary one; its cleanup
also removes the ignored cache and any candidate attempt it created.

```sh
workspace="$(mktemp -d)"
trap 'rm -rf "$workspace"' EXIT
codesignal-sim fetch --workspace-root "$workspace"
codesignal-sim start --workspace-root "$workspace" --mode drill --drill-duration-seconds 1800
codesignal-sim status --workspace-root "$workspace" --json
codesignal-sim context --workspace-root "$workspace"
```

`start` defaults to the full `full-90m` profile (5,400 seconds). The named
drill profile is `drill-30m`, with a default effective duration of 1,800
seconds; `--drill-duration-seconds` accepts another positive duration and
persists it. See [drill profiles](docs/drill-profiles.md).

### Browser entry, timer, and terminal transport

After fetching the dedicated workspace, launch the loopback browser server.
`--port 0` chooses an available loopback port and `--no-open` leaves opening
the browser to you:

```sh
# Console entry point
codesignal-sim web --workspace-root "$workspace" --port 0 --no-open

# Equivalent module entry point
python3 -m codesignal_practice_simulator web --workspace-root "$workspace" --port 0 --no-open
```

The command reports a `127.0.0.1` capability URL. Open that complete URL in a
local browser, retaining its `#...` fragment. The fragment is a private
per-launch capability and is not part of the HTTP URL. After loading, the
browser sends it only to the same loopback origin in the
`X-Simulator-Token` request header (not an `Authorization` header). It can
therefore appear in captured request diagnostics: do not paste the URL or
header value into chat, tickets, shell history, screenshots, or retained logs.
`--no-open` suppresses the automatic opener; omit it only when the local
opener is wanted.

The entry screen shows the profile and no-pause terms. Choosing **Start
practice** only opens the confirmation; **Confirm and start** creates the one
authoritative attempt and starts its server-authoritative timer immediately.
There is no pause, extension, or browser-side reset. At the deadline, the
browser becomes read-only and its **Submit** button is disabled. Its source and
stored results remain viewable.

Use **Back to start** in the assessment header to leave the test view. For an
active attempt, confirm the warning: the timer keeps running, saved changes are
kept, and unsaved local edits are discarded. Cancel and save first if needed.
Reconnect from the start page to continue the same attempt. Returning from a
submitted or expired attempt needs no confirmation and does not change its result.
Wait for an in-flight save, test, or submission to finish before leaving.

Ctrl-C stops the local server; additional Ctrl-C presses during cleanup are
ignored until its listener and connections are released. Stopping the server
does not pause or submit an attempt.

The browser UI and direct CLI are two transports for the same attempt. Keep
the web server running in one terminal, then use a second terminal for safe
state inspection or the CLI fallback after the browser starts an attempt:

```sh
# Terminal 1
codesignal-sim web --workspace-root "$workspace" --port 0 --no-open

# Terminal 2
codesignal-sim context --workspace-root "$workspace"
```

`web` serves the loopback browser; it does not create a second lifecycle
authority. Reloading the page or reconnecting through a newly launched web
server reads the selected attempt's authoritative state. A restart rotates the
capability URL, so use the newly printed complete URL, but does not restart or
extend an existing attempt. Start a new attempt only after a final state, using
the explicit entry confirmation.

Browser edits are debounced and autosaved with a compare-and-swap revision.
If another browser or CLI action made the source stale, the browser preserves
the local text and presents an explicit choice to reload the server version or
copy the local version after it refreshes the revision. Candidate-only,
bounded history supports explicit restore and reset; it is not permission for
an agent to read source or history.

`context` and the generated `STATUS.md` are safe, derived views. The
server-authoritative timer, scoring, and lifecycle own the result. Candidate
source and source history belong to the candidate, while `COACHING.md` is
candidate-owned, non-executable text for candidate-approved goals, questions,
and high-level hints.

During timed work, read derived context first and ask explicit permission
before reading source or history. Never read or use reference, study, vendor,
fixture cache, copied tests, or hidden-test material; never import or execute
coaching in `simulation.py`, make hidden-test claims, or manually edit
`session.json`, `events.jsonl`, `STATUS.md`, locks, or `active.json`. Verify
browser state through the server response and `status`, `time`, `context`,
`test`, or `submit`. This is process guidance, not same-user isolation.
It is operational policy, not a security sandbox.

Every CLI command works without Just:

```text
fetch   [--source PATH]
start   [--assessment ID] [--mode {full,drill}] [--drill-duration-seconds SECONDS]
resume | status | time | test | submit | context [--format {markdown,json}]
task --level {1,2,3,4}
```

All commands accept `--workspace-root PATH` after the subcommand; commands
other than `fetch` and `start` also accept `--attempt UUID`. Without an
explicit UUID, `attempts/active.json` selects the attempt. An explicit,
canonical lowercase UUID takes precedence over that pointer; the CLI never
guesses from directory recency. The complete command, JSON, lifecycle, and
exit contract is in [docs/cli-contract.md](docs/cli-contract.md).

## Canonical local verification

After `fetch` has populated the ignored fixture cache, run the migration and
post-attempt compatibility checks directly:

```sh
python3 scripts/run_legacy_checks.py
```

This verifies the tracked mappings, cache hashes, and Git boundary before
running the first-party solution and study checks. It does not run the fetched
upstream compatibility test.

### Workspace layout

```text
workspace/
├── .cache/codesignal-fixtures/6aab304/  # ignored, validated FETCH_ONLY cache
└── attempts/
    ├── active.json                      # selected UUID; not session authority
    └── <uuid>/
        ├── session.json                 # authoritative lifecycle state
        ├── events.jsonl                 # lifecycle event log
        ├── STATUS.md                    # generated, non-authoritative view
        ├── COACHING.md                  # candidate-owned non-executable text
        └── candidate-facing copied files
```

Never hand-edit `session.json`, `events.jsonl`, locks, `active.json`, or
`STATUS.md`. `attempts/<uuid>/session.json` is the authoritative session
record. The fixture cache and `attempts/` are deliberately separate.

## Evaluation and submission

`test` scores all four level groups against the selected attempt and persists
the score. It exits 0 when every group passes and exits 5 only when `test` ran
and one or more groups were non-passing. `submit` scores and finalizes an
active or expired attempt once; an expired submission first records expiry,
then stores the final result. `submit` always exits 0 when it successfully
finalizes, even when stored groups failed or errored. Repeating `submit`
returns the stored result with exit 0 and does not rescore or mutate the
attempt.

`status` and `time` show an overdue attempt as expired and persist that single
expiry transition with exit 0. `resume` and `test` then exit 4 without scoring
or changing it. The lifecycle table in [the CLI contract](docs/cli-contract.md#lifecycle-and-expiry)
defines every state transition.

The browser intentionally cannot submit after expiry: it displays a read-only
expired state and disables **Submit**. The CLI remains the explicit fallback:
`codesignal-sim submit --workspace-root "$workspace"` finalizes that expired
attempt once. A repeated CLI submit returns the stored result without scoring
or mutation, and a browser refresh or reconnect then displays that stored
final result. Do not use
`test` as a dry-run submit: it records a score but keeps an active attempt
active; `submit` is the irreversible finalization operation.

Use `--json` for the stable `cli/v1` envelope. Exits are 0 (success), 2
(invalid input), 3 (unavailable or corrupt session/cache), 4 (illegal
lifecycle operation or lock contention), and 5 (only when `test` runs and any
group is non-passing).

## Optional Just recipes

`just` is not required. If installed, `just --list` shows shortcuts for the
same CLI workflow, including `just verify` for the maintained test suite and
whitespace check. `just setup` creates `.venv` and installs the console CLI
used by the timed shortcuts. The `test-compat`, `study-spec`, `study-stages`,
and `study-check` recipes are post-attempt educational or deprecated
compatibility support, not timed commands.

Run the hermetic editable-process verification directly with:

```sh
python3 -m unittest tests.test_end_to_end -v
```

## Browser asset verification

The generated static package can be checked without Node:

```sh
python3 scripts/check_assets.py
```

The bounded release checks use temporary lockfile installs and distributions.
The optional `test` extra contains only the Python build tool used for sdist
inspection; it is not a runtime dependency:

```sh
npm --prefix webui run install:browser
npm --prefix webui run test:browser
python3 -m unittest tests.test_asset_verification -v
python3 scripts/run_packaged_browser.py
```

Run the npm dependency setup and Python build-tool setup above first.
`install:browser` provisions the Chromium version selected by the locked
Playwright dependency and may download development binaries. This setup is
separate from the offline application runtime; wheel users do not need it.

Publication uses strict directory fsync on POSIX. Windows retains atomic
renames but treats its documented unsupported directory-open/fsync errors as
best effort, so it does not provide the same post-rename power-loss guarantee.

Successful browser runs retain no screenshots or traces. The Playwright
policy denies every request except the loopback server origin and verifies the
installed wheel's manifest, workers, styles, and font responses.

## Troubleshooting and scoped cleanup

| Symptom | Safe action |
| --- | --- |
| `start` reports an unavailable or corrupt fixture cache | Run `codesignal-sim fetch --workspace-root "$workspace"` again, or use the explicit offline `--source` form. Do not repair cache files manually. |
| The web server cannot bind, or the automatic opener is unavailable | Use `--port 0 --no-open`, then open the newly printed complete capability URL locally. Stop an old simulator server only if it is yours. |
| A page says the fixture or selected session is unavailable | Check `codesignal-sim status --workspace-root "$workspace"` and repair the fixture cache with `fetch`; do not point the browser at arbitrary files. |
| Monaco/editor assets fail to load | Reinstall or use the verified wheel. Do not add a CDN, start Node at runtime, or substitute generated assets; `python3 scripts/check_assets.py` verifies a source checkout's bundle. |
| An autosave reports a conflict or stale source | Keep either version explicitly: choose **Reload server version** to discard local text, or **Copy local version** to save it after refreshing the revision. |
| The attempt is expired or submitted | It is read-only. For expired browser attempts, use the CLI `submit` once if finalization is intended; after submission use the stored result or explicitly start a new attempt. |
| An offline machine has no fixture cache | Install the wheel locally, then run the separately supplied complete fixture source through `fetch --source`. The wheel carries the first-party pinned paths and hashes, but never fixture bytes. |

Stop the web server before cleanup. For the temporary workspace created by the
timed-workflow example, let that same shell exit so its `mktemp`-scoped trap
removes the workspace, cache, and attempts together. For a named workspace,
confirm its path and use your normal file-management process to remove only
that whole workspace. Never use a broad deletion against an unknown workspace
or hand-delete individual session, history, lock, or cache records. In a source
checkout, `just clean` removes only Python caches; it does not remove an
attempt or fixture cache.

## Post-attempt learning and compatibility

After submission or an explicit end to timed work, you may opt into
[`study/`](study/), [`solution/`](solution/), and [`notes/`](notes/). They
contain learning material and reference behavior; do not use them during a
live attempt. [`docs/legacy/`](docs/legacy/) is deprecated historical material,
not a supported workflow.

At Level 4, the separately fetched visible compatibility test treats
`ROLLBACK` as log-only, while the written task requires restoring state.
Post-attempt reference checks keep both interpretations explicit. For an
assessment, implement the written specification; treat a contradictory visible
test as a compatibility issue rather than changing the specification. See the
[post-attempt discrepancy note](notes/level4-rollback-discrepancy.md).

For collaboration boundaries and safe attempt context, read
[docs/agent-safety.md](docs/agent-safety.md).

The simulator is a local practice tool, not an official CodeSignal evaluator.
No local result, including synthetic browser verification, is equivalent to
official hidden tests or makes that claim.
