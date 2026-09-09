# CodeSignal Practice Simulator

Practice a four-level, stateful CodeSignal-style exercise locally. The goal is
to work through one evolving program under interview conditions, then study
clear reference material afterward.

## Setup

This project supports Python 3.10 and newer and has no project runtime
dependencies.

```sh
python3 -m pip install -e .
just --list
```

`just setup` performs the same editable install. The `codesignal-sim` command
is available after installation.

## FETCH_ONLY assessment material

The upstream assessment has no license grant recorded for redistribution, so
its README, task descriptions, starter, and bundled test are never committed
to this repository. Fetch the seven pinned files only when you need them:

```sh
just fetch
# or: python3 scripts/fetch_fixture.py --manifest docs/migration-manifest.json
```

The fetcher validates every file before atomically placing it in
`.cache/codesignal-fixtures/6aab304/`. That cache is intentionally ignored by
Git. Do not add its contents, upstream requirements, or any other vendor
files to a commit. An offline source tree can be supplied with
`--source PATH` when network fetching is unavailable.

## Timed simulator

The canonical timed workflow uses `codesignal-sim` and UUID-named attempt
directories. It stores authoritative lifecycle state in
`attempts/<uuid>/session.json`, selects the active attempt with
`attempts/active.json`, and treats `STATUS.md` as derived output.

```sh
just fetch
just practice
just task 1
just status
just time
just resume
```

`just practice-drill 1800` starts a drill with a persisted 1,800-second
duration. The CLI creates only a candidate-facing copy of the six assessment
files; it never uses the cache as an attempt directory. `test` and `submit`
are reserved command names while their runtime adapters are being added, so
they are not part of this workflow.

The installed wheel ships only first-party fixture metadata, never upstream
bytes. From any directory, set up its local cache with:

```sh
codesignal-sim fetch --workspace-root "$PWD"
codesignal-sim start --workspace-root "$PWD"
```

Use `--source PATH` with `codesignal-sim fetch` for an offline complete tree.

## Learn after an attempt

The material tracked here is original learning support:

- `study/` contains a blank starter, small cumulative drills, and a checker.
- `solution/stages/` shows intentionally simple, interview-realistic Python:
  one complete program after each level, without premature architecture.
- `solution/simulation.py` is the fully factored reference solution.
- `notes/` explains the progression and the level-4 ambiguity.

These are post-attempt study and compatibility tools, not another simulator.
Run `just study-stages` for the staged examples and `just study-spec` for the
spec-oriented reference checks. `just test-compat` runs the fetched bundled
test against the reference implementation; it needs the ignored fixture cache.

## Level 4: compatibility is not the specification

The fetched bundled level-4 test treats `ROLLBACK` as a log-only operation.
The level-4 task text instead requires restoring the state at the requested
time. The reference implementation makes that distinction explicit: its
default simulator entry point preserves bundled-test compatibility, while its
`FileStorage` behavior and `study-spec` enforce real rollback. For an actual
assessment, implement the stated behavior and treat a conflicting visible
test as a compatibility concern, not as the specification.
