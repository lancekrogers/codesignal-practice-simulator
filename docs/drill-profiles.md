# Timed profiles

Profiles are selected when an attempt starts and are persisted in that
attempt's `session.json`. Later commands use the persisted profile; they do not
recalculate a duration from the current command line.

| Mode | Profile ID | Effective duration | Start command |
| --- | --- | --- | --- |
| `full` (default) | `full-90m` | 5,400 seconds (90 minutes) | `codesignal-sim start --workspace-root PATH` |
| `drill` | `drill-30m` | 1,800 seconds (30 minutes), unless overridden | `codesignal-sim start --workspace-root PATH --mode drill` |

There is one named drill profile, `drill-30m`. Set a different positive
effective duration when starting it:

```sh
codesignal-sim start --workspace-root PATH --mode drill --drill-duration-seconds 900
```

The profile ID remains `drill-30m` and the session records `900` as its
effective duration. `--drill-duration-seconds` is invalid with `--mode full`
and a zero, negative, or non-integer duration exits 2.

When the UTC clock reaches the persisted deadline, the attempt is expired.
`status` and `time` record and display that state; `resume` and `test` exit 4;
and `submit` records the final result once. See
[the lifecycle contract](cli-contract.md#lifecycle-and-expiry) for full
semantics.
