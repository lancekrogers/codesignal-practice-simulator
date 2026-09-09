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
| 0 | Command completed, including expired `status`/`time` and repeat `submit`. |
| 2 | Invalid input, including malformed identifiers, unsupported schemas, invalid profiles, or invalid durations. |
| 3 | Session unavailable or corrupt, including no valid active pointer or malformed persisted state. |
| 4 | Illegal lifecycle operation or lock contention. |
| 5 | Candidate tests ran and at least one level group did not pass. |

Expected domain errors are rendered as safe structured errors in `--json` mode
and safe messages for people; command adapters do not expose tracebacks.
