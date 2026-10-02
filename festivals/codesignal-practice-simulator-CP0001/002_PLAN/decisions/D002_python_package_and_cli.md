# D002: Python Package, CLI, and Attempt Layout

**Status:** accepted<br>
**Date:** 2026-09-08

## Context

The existing project is Python and standard-library test based. Its primary
interface is a collection of Just recipes that dispatch to
`scripts/new_attempt.py` and `scripts/scorecard.py`. The approved product
requires stable `start`, `resume`, `status`, `time`, `task`, `test`, and
`submit` commands for reusable sessions; recipe names such as `practice` and
`level` are no longer a complete interface.

The upstream assessment is fetch-only because its repository has no license.
The simulator and fixture setup tooling therefore use the standard library and
must not track the upstream starter, dependencies, or tests. This keeps basic
state, status, and CLI behavior independently installable and testable.

The command layer also needs a predictable filesystem boundary. Candidate
attempts must never be created beside the ignored validated cache or inside
reference/study material, and terminal automation needs an unambiguous way to
select an attempt without guessing from directory timestamps.

## Options

### Option A: Retain only standalone scripts and Just recipes
- **Pros:** Minimal short-term refactor; existing users recognize the commands.
- **Cons:** Does not establish the required command names, a versioned public
  interface, or reliable importable test seams.

### Option B: Create a standard Python package with a `codesignal-sim` console command and `python -m` entry point
- **Pros:** Gives one discoverable CLI contract; keeps modules testable; can
  preserve Just recipes as compatibility aliases; needs no runtime framework.
- **Cons:** Requires packaging metadata and a thin command parser.

### Option C: Add a third-party CLI framework
- **Pros:** Rich help and argument parsing quickly.
- **Cons:** Adds a dependency without a requirement that standard `argparse`
  cannot meet; contradicts the preference for a simple standard-library core.

## Decision

Choose Option B with the Python standard library: package reusable modules
under a named package, use `argparse` for command parsing, install
`codesignal-sim`, and expose the same behavior through `python -m
codesignal_practice_simulator`. Direct Python commands are the authoritative
verification route. Retain adapted Just recipes only as optional documented
compatibility checks, never as the public contract or a clean-clone
prerequisite.

The repository layout separates tracked code, fetched material, and disposable
runtime data:

```text
src/codesignal_practice_simulator/  # CLI adapter and application services
scripts/fetch_fixture.py            # pinned downloader and --source test seam
docs/migration-manifest.json        # provenance and expected paths/hashes only
.cache/codesignal-fixtures/6aab304/ # Git-ignored validated local fixture cache
solution/, study/, notes/           # non-verbatim user-authored material only
attempts/<attempt-id>/              # Git-ignored self-contained workspace
```

`attempts/` is the default workspace root and is Git-ignored. A command may
receive an explicit workspace root for temporary-directory testing or another
local location; it must resolve that root before selecting an attempt. An
attempt selector takes precedence over the active-attempt pointer. When no
selector is supplied, commands that need an attempt use the one explicit
active pointer; if no pointer exists or it is invalid, they fail rather than
choosing the newest directory. `start` creates an ID and makes it active, and
`resume` may make the explicitly selected active attempt current.

`scripts/fetch_fixture.py --manifest docs/migration-manifest.json` is the
fixture setup command. It materializes every record in the one declared
seven-record set—upstream `README.md` to cache `vendor-readme.md`, and the six
upstream `practice_assessments/file_storage/` files to cache
`assessment/file_storage/` paths—from the exact upstream commit; `--source
PATH` requires the equivalent complete upstream-path tree for offline tests.
It rejects network, unsafe-path, missing-file, incomplete-set, and hash errors
without leaving a usable cache. Attempts use only the six assessment inputs.
All commands provide a machine-readable `--json` mode and documented nonzero
exit codes for invalid input, unavailable session state, failed level tests,
and illegal lifecycle transitions. Command handlers call application services
rather than implementing persistence or scoring inline. The `task` command
reads copied prompt material only; it never opens reference solutions or
teaching notes.

## Consequences

- User-authored behavior is decomposed into importable attempt, clock, scorer,
  renderer, and CLI modules rather than copying upstream code wholesale.
- The baseline targets Python 3.10+; modern type syntax remains allowed.
- Core commands/tests run without upstream dependencies. Clean-clone tests use
  a temporary local fixture source or mocked downloader that materializes and
  validates every fetch record, including `vendor-readme.md`, never vendored or
  downloaded unlicensed tracked bytes.
- After 003.01.03 stages its manifest, it configures `core.hooksPath=.githooks`;
  pre-commit and pre-push then call a manifest-driven scanner that inspects
  staged and `HEAD` blobs for known vendor hashes and forbidden vendor paths.
- CLI help, exit code, JSON schema, and compatibility-recipe behavior become
  part of the tested interface.
- The CLI owns argument parsing and presentation only. Attempt creation,
  selection, lifecycle validation, persistence, scoring, and rendering remain
  independently testable services.
