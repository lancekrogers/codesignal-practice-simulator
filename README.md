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

After fetching, `just practice` creates an ignored timed attempt from the
validated cache. Work through levels in order, use `just level N` or
`just score` to check progress, and use `just submit` to save the result.

## Learn after an attempt

The material tracked here is original learning support:

- `study/` contains a blank starter, small cumulative drills, and a checker.
- `solution/stages/` shows intentionally simple, interview-realistic Python:
  one complete program after each level, without premature architecture.
- `solution/simulation.py` is the fully factored reference solution.
- `notes/` explains the progression and the level-4 ambiguity.

Run `just test-stages` for the staged examples and `just test-spec` for the
spec-oriented reference checks. `just test` runs the fetched bundled test
against the reference implementation; it needs the ignored fixture cache.

## Level 4: compatibility is not the specification

The fetched bundled level-4 test treats `ROLLBACK` as a log-only operation.
The level-4 task text instead requires restoring the state at the requested
time. The reference implementation makes that distinction explicit: its
default simulator entry point preserves bundled-test compatibility, while its
`FileStorage` behavior and `test-spec` enforce real rollback. For an actual
assessment, implement the stated behavior and treat a conflicting visible
test as a compatibility concern, not as the specification.
