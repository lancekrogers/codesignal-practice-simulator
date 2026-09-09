# CLI and session-state contract

`codesignal-sim` and `python -m codesignal_practice_simulator` expose the same
command contract. The runtime stores only versioned JSON owned by
`codesignal_practice_simulator.models`; Markdown, fixture files, candidate
files, and the active pointer are never session authority.

## State schemas

`session.json` uses schema version `session/v1` and contains:

- `attempt_id`: canonical UUID;
- `assessment`: its lowercase identifier, display name, and `level_count` of
  exactly four;
- `profile`: `full` with `full-90m` and exactly 5,400 seconds, or `drill`
  with named `drill-30m` and a positive persisted effective duration (default
  1,800 seconds);
- UTC ISO-8601 `started_at` and `deadline_at`, whose difference equals the
  effective duration;
- lifecycle `status` (`active`, `expired`, or `submitted`), non-negative
  `revision`, and an optional complete four-level `score`;
- `submitted_at`, which is absent except on a submitted session. A submitted
  session always has both this UTC timestamp and a score.

Every score contains results for levels 1 through 4, in order. Each result is
`passed`, `failed`, or `error`; `passed_levels` and
`highest_contiguous_level` are stored and must match those results.

Each `events.jsonl` record uses `event/v1`, a canonical UUID event ID and
attempt ID, a non-negative state revision, a UTC timestamp, a lowercase event
name, an outcome (`succeeded`, `rejected`, or `recovered`), and JSON-safe
command arguments. `attempts/active.json` uses `active-pointer/v1` and
contains only its selected canonical attempt ID. It is a selector, not
session authority.

Before publishing a scored submission, persistence writes an attempt-owned
`.submission-recovery.json` record containing the exact prior and submitted
`session/v1` states plus its exact `event/v1` record. While that marker exists,
any selected-attempt access accepts only the saved prior or submitted state,
then finishes the event and marker sequence under the attempt lock without
rerunning the scorer.
Recovery rejects duplicate event IDs or a conflicting submitted event instead
of manufacturing another submission. A completed repeat `submit` has no marker
and is byte-identical: it does not score or write.

## Lifecycle and expiry

An active session is expired when the injected UTC clock is at or after
`deadline_at`.

| Command | Active and before deadline | Active at/after deadline | Expired | Submitted |
| --- | --- | --- | --- | --- |
| `status`, `time` | Render success | Atomically record `expired`, then render success | Render success; no new change | Render success |
| `resume` | Resume and may select the attempt | Atomically record `expired`, then return exit 4 | Exit 4; no score, event, revision, or state change | Exit 4; no change |
| `test` | Run all four groups and persist the score | Atomically record `expired`, then return exit 4 without scoring | Exit 4; no score, event, revision, or state change | Exit 4; no change |
| `submit` | Run scoring and atomically store one submitted result | First record `expired`, then store one submitted result | Store one submitted result | Return the exact stored result; no scoring, event, revision, timestamp, or state change |

The expiry transition in the “active at/after deadline” column is the one
permitted mutation for that observation. Rejection itself does not append a
second event or revise the state. Every state change is made while holding the
attempt lock and is paired with exactly one event by persistence services.

## Stable exits

| Exit | Meaning |
| --- | --- |
| 0 | Command completed, including expired `status`/`time` and every successfully finalized `submit`, even when stored groups failed or errored. |
| 2 | Invalid input, including malformed identifiers, unsupported schemas, invalid profiles, or invalid durations. |
| 3 | Session unavailable or corrupt, including no valid active pointer, malformed persisted state, or a saved assessment that no longer matches the registry. |
| 4 | Illegal lifecycle operation or lock contention. |
| 5 | Only the `test` command returns this exit: it ran and at least one group was non-passing. |

Expected domain errors are rendered as safe structured errors in `--json` mode
and safe messages for people; command adapters do not expose tracebacks.

## Command surface

Both entry points use one `argparse` parser:

```text
codesignal-sim
├── fetch   [--json] [--workspace-root PATH] [--source PATH]
├── start   [--json] [--workspace-root PATH]
│           [--assessment ID] [--mode {full,drill}]
│           [--drill-duration-seconds SECONDS]
├── resume  [--json] [--workspace-root PATH] [--attempt UUID]
├── status  [--json] [--workspace-root PATH] [--attempt UUID]
├── time    [--json] [--workspace-root PATH] [--attempt UUID]
├── task    [--json] [--workspace-root PATH] [--attempt UUID] --level {1,2,3,4}
├── test    [--json] [--workspace-root PATH] [--attempt UUID]
├── submit  [--json] [--workspace-root PATH] [--attempt UUID]
└── context [--json] [--workspace-root PATH] [--attempt UUID]
            [--format {markdown,json}]
```

Common options are intentionally after the subcommand. `--workspace-root`
defaults to the current working directory. `--attempt` must be a canonical,
lowercase UUID. An explicit `--attempt` is passed to the application adapter
and takes precedence over the active pointer; the CLI never selects the newest
directory or guesses an attempt from a timestamp. `start --mode full` rejects
`--drill-duration-seconds`, and every supplied duration must be positive.

`fetch`, `start`, `resume`, `status`, `time`, `task`, `test`, `submit`, and
`context` use production application adapters. `test` and `submit` use the
attempt-local isolated scorer; selection is held only long enough to choose the
attempt, while scoring holds only that attempt's lock. `context` reads only
validated session state and a safe projection of event metadata; it never reads
candidate source, copied tests, fixtures, or educational/reference material.
Its `--format` defaults to `markdown`; `json` returns the same safe context
document as structured data inside the CLI envelope. The wheel includes a small,
first-party runtime manifest containing only the seven fetch paths and hashes;
it contains no upstream fixture bytes. It stores the fetched, ignored cache at
`.cache/codesignal-fixtures/6aab304/` under `--workspace-root`, so installed
commands do not depend on a source checkout. `fetch --source PATH` accepts a
complete offline tree with the declared upstream paths.

The workspace manager resolves the actual `attempts/` destination before it
locks or writes. It rejects an `attempts` symlink, symlink ancestors that land
in the cache, and either direction of cache/attempts containment. This guard
also runs before fixture setup or a selected attempt can be used by a mutating
operation.

Before `start` creates any workspace path, it validates the complete
seven-record fixture cache. A missing or invalid cache returns exit 3 with an
actionable repair command:

```sh
codesignal-sim fetch --workspace-root PATH
```

It fetches and validates fixture material; do not replace cache files by hand.
`start --mode full` persists the fixed `full-90m` 5,400-second profile. `start
--mode drill` persists the named `drill-30m` profile and its supplied positive
duration (or 1,800 seconds by default).

`status` and `time` observe an overdue active attempt, atomically persist its
single `expired` transition, then return successful expired output. A final
(`expired` or `submitted`) attempt causes `resume` to exit 4 without mutation.
After a successful command the adapter may refresh the derived `STATUS.md`
through the renderer while holding the attempt lock, so a slow refresh cannot
replace it with an older concurrent lifecycle snapshot. A renderer failure
never rolls back or changes durable lifecycle state.

`task --level N` reads only the selected attempt's copied `levelN.md`. It
validates the selected attempt's registry metadata and level before reading,
does not fall back to a cache file, and never reads solution or study material.
An unavailable copied level is exit 3; an invalid level syntax is exit 2.

## Output envelopes

Every command result is wrapped in the versioned `cli/v1` envelope. Human
output uses the same version and error code, while JSON is suitable for
automation:

```json
{"ok":true,"result":{"session":{"attempt_id":"...","status":"active"}},"schema_version":"cli/v1"}
```

```json
{"error":{"code":"invalid_input","message":"attempt ID must be a canonical UUID"},"ok":false,"schema_version":"cli/v1"}
```

The equivalent human error is:

```text
[cli/v1] error (invalid_input): attempt ID must be a canonical UUID
```

Error codes follow the stable exit table: `invalid_input` (2),
`session_unavailable` (3), `illegal_lifecycle` (4), and
`candidate_failure` (5). Parser errors, malformed selectors/paths, invalid
option combinations, serializer failures, and unexpected adapter exceptions
produce a safe error envelope with no traceback and no CLI-owned mutation.
Serializer and unexpected-adapter failures use exit 2 with
`serialization_failed` and `internal_error`, respectively.

For `context`, the requested `--format` controls the `result.context` value:
Markdown is a deterministic string and JSON is a deterministic object with
assessment metadata, lifecycle timestamps, score summary, safe event metadata
(revision, timestamp, name, and outcome), and legal commands. `--json` still
controls the outer `cli/v1` envelope for both formats.
