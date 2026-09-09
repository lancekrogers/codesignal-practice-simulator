# CodeSignal Practice Simulator

Practice a four-level, stateful CodeSignal-style exercise locally. The CLI is
the supported timed interface; Just recipes are optional shortcuts.

## Install and FETCH_ONLY setup

Python 3.10+ is required and the simulator has no runtime dependencies. Create
and activate a virtual environment before installing:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
codesignal-sim --help
python3 -m codesignal_practice_simulator --help
```

The console command and `python3 -m codesignal_practice_simulator` have the
same commands, options, output envelopes, and exits. Substitute the module
form for `codesignal-sim` in every command below when a console script is not
convenient.

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
valid; rerun `fetch` rather than changing cache files by hand.

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
python3 -m unittest tests.test_asset_verification -v
python3 scripts/run_packaged_browser.py
```

Publication uses strict directory fsync on POSIX. Windows retains atomic
renames but treats its documented unsupported directory-open/fsync errors as
best effort, so it does not provide the same post-rename power-loss guarantee.

Successful browser runs retain no screenshots or traces. The Playwright
policy denies every request except the loopback server origin and verifies the
installed wheel's manifest, workers, styles, and font responses.

## Post-attempt learning and compatibility

After submission or an explicit end to timed work, you may opt into
[`study/`](study/), [`solution/`](solution/), and [`notes/`](notes/). They
contain learning material and reference behavior; do not use them during a
live attempt. [`docs/legacy/`](docs/legacy/) is deprecated historical material,
not a supported workflow.

At Level 4, a bundled visible compatibility test treats `ROLLBACK` as
log-only, while the written task requires restoring state. Post-attempt
reference checks keep both interpretations explicit. For an assessment,
implement the written specification; treat a contradictory visible test as a
compatibility issue rather than changing the specification. See the
[post-attempt discrepancy note](notes/level4-rollback-discrepancy.md).

For collaboration boundaries and safe attempt context, read
[docs/agent-safety.md](docs/agent-safety.md).
