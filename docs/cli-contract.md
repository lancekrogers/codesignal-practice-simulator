# CLI and session-state contract

`codesignal-sim` and `python -m codesignal_practice_simulator` expose the same
command contract. The runtime stores only versioned JSON owned by
`codesignal_practice_simulator.models`; Markdown, fixture files, candidate
files, and the active pointer are never session authority.

## State schemas

`session.json` uses schema version `session/v2` for attempts created by this
release and `session/v1` for attempts created before it. Both are read; each
attempt keeps writing the version it was created with, and no read upgrades a
record on disk. An older release cannot read `session/v2`, so running mixed
versions against one workspace is unsupported. Both versions contain:

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

`session/v2` additionally pins the content its attempt was created from and
identifies the review it published:

- `content_identity` is `pinned` for every attempt this release creates. Its
  `assessment` then also carries `content_version` and `content_digest`,
  computed at creation from the packaged manifest's declared file hashes plus
  the runner contract, and verified against the staged copies before the
  attempt exists. Continuing or scoring the attempt requires that same
  installed content; stored results stay readable when it is gone.
- `status` may also be `abandoned`, with `abandonment` metadata: `ended_at`,
  a `reason`, and `practice_score`, the last `test` result moved out of
  `score` so it is never read as a submitted result. The original `started_at`
  and `deadline_at` are unchanged.
- `review_digest` on a submitted session names its `review.json` record.

`session/v1` records carry no content identity. Nothing infers one for them
from today's registry. The one mutation that rewrites a v1 record's schema is
explicit abandonment (a restart or an end-attempt action): v1 has no
`abandoned` status, so that record becomes `session/v2` with
`content_identity: unavailable` and its stored three-field `assessment`
unchanged. This legacy-identity variant is only ever abandoned; a new attempt
can never start from it, and no content version or digest is ever attached to
it. Its `events.jsonl` keeps the existing `event/v1` records and gains the
`event/v2` abandonment event.

Every score contains results for levels 1 through 4, in order. Each result is
`passed`, `failed`, or `error`; `passed_levels` and
`highest_contiguous_level` are stored and must match those results.

Each `events.jsonl` record uses the schema family of its session (`event/v1`
or `event/v2`), a canonical UUID event ID and
attempt ID, a non-negative state revision, a UTC timestamp, a lowercase event
name, an outcome (`succeeded`, `rejected`, or `recovered`), and JSON-safe
command arguments. `attempts/active.json` uses `active-pointer/v1` and
contains only its selected canonical attempt ID. It is a selector, not
session authority.

Before publishing a scored submission, persistence writes an attempt-owned
`.submission-recovery.json` record (`submission-recovery/v1` or `/v2`, matching
the session) containing the exact prior and submitted states, the exact event,
and the immutable review record. While that marker exists, any selected-attempt
access accepts only the saved prior or submitted state, then publishes the
review, state, event, and marker sequence under the attempt lock without
rerunning the scorer. A review already on disk must be byte-identical to the
recorded one; a difference is corruption and fails closed rather than being
overwritten.
Recovery rejects duplicate event IDs or a conflicting submitted event instead
of manufacturing another submission. A completed repeat `submit` has no marker
and is byte-identical: it does not score or write.

## Input providers

Each registered assessment declares a `provider_kind` (D003). The provider
validates the assessment's inputs before any workspace mutation, computes the
content identity a new attempt pins, and stages only the allowlisted
candidate-facing files (four prompts, `simulation.py`, `test_simulation.py`).

- `pinned-fetched` (File Storage): the existing seven-file fixture cache and
  its provenance validation, unchanged. `content_version` is
  `upstream-<manifest commit>` and the digest is the one described above; the
  cache must be fetched before an attempt can start.
- `packaged-original`: exercises bundled in the installed package under
  `resources/<input directory>/` with a `content-manifest.json`
  (`assessment-package/v1`: `assessment_id`, a slug `content_version`, and the
  SHA-256 of every candidate-facing file). Validation requires exactly those
  files plus the manifest in the directory, so development solutions can never
  be staged; every byte is checked against the manifest before staging and the
  staged copies are checked again before the attempt exists. Originals start
  offline and never require the fetched cache.

Only the selected assessment's provider runs. A missing or tampered input,
an unknown provider kind, or an unsupported profile is exit 3 (or 2 for the
profile) before any attempt, staging directory, restart journal or abandonment
marker is written (the shared `attempts/` root and its lock file may already
exist); the fetch remedy is suggested only for fetched content.

## Assessment catalog

`codesignal-sim catalog` and `GET /api/catalog` enumerate every installed
definition from the registry (stable ID order) with `assessment_id`,
`display_name`, `description`, `level_count`, `levels`, `profiles`,
`provider_kind`, the `content_version` and `content_digest` a new attempt
would pin (declared by the manifest, so known before any fetch), and readiness:
`available` plus a `setup` reason when not — `fetch_required` (fetched content
whose cache is absent or invalid), `packaged_content_invalid` (a bundled
original whose files do not match their manifest), or `provider_unavailable`
(no provider for that kind in this installation). Enumeration validates inputs
by reading them and writes nothing; `setup_message` never contains a path.
`GET /api/bootstrap` carries the same list as `catalog` beside its existing
single-assessment keys, which describe the primary (File Storage when
installed) definition.

Bundled originals ship under `resources/assessments/<id>/` and the archive
checks (`just check wheel`) accept exactly the six candidate-facing files plus
`content-manifest.json` there; any other member fails the build check.
`just check content` validates the bundled directories in the checkout: exact
file set, manifest hashes, registry agreement, and a `test_simulation.py` that
defines exactly `test_group_1` through `test_group_4` importing only `unittest`
and `simulation`.

Two original exercises are bundled: `in_memory_records` (In-Memory Records)
and `account_ledger` (Account Ledger), both specified in `docs/content/`. They
start offline without the fetched File Storage cache. Their development
oracles live under `tests/oracles/` and are never packaged.

## Submission review record

A submission publishes `review.json` (`review/v1`) once and never rewrites it.
It records the attempt and state revision, the score, the profile and
timestamps, the assessment as stored, and `content_identity`, which is `pinned`
only for a `session/v2` attempt and otherwise `unavailable`. Its `source` holds
the exact scored bytes with their digest.

The submitted bytes are read, scored, and re-read under one attempt lock. If
the source changed while the scorer ran, nothing is committed and the command
reports exit 4 so it can be retried. If the source could not be read at all,
the submission still finalizes and `source` is null: absence is recorded, never
guessed. A `session/v1` attempt submitted by this release therefore has bound
source bytes with no content identity, while one submitted by an older release
has no review record at all.

A review of an attempt that was never submitted reports `source_binding:
not_applicable` and `source: null`; for an expired attempt `score` is the last
local practice result the record holds, and for an ended (abandoned) attempt
that result is `practice_score` while `score` is null. Neither is a submission
result, and the browser labels them "last practice result". The saved work of
such an attempt is read through the ordinary source route by explicit attempt
ID, never presented as submitted bytes.

## Lifecycle and expiry

An active session is expired when the injected UTC clock is at or after
`deadline_at`.

| Command | Active and before deadline | Active at/after deadline | Expired | Submitted |
| --- | --- | --- | --- | --- |
| `status`, `time` | Render success | Atomically record `expired`, then render success | Render success; no new change | Render success |
| `resume` | Resume and may select the attempt | Atomically record `expired`, then return exit 4 | Exit 4; no score, event, revision, or state change | Exit 4; no change |
| `test` | Run all four groups and persist the score | Atomically record `expired`, then return exit 4 without scoring | Exit 4; no score, event, revision, or state change | Exit 4; no change |
| `submit` | Run scoring and atomically store one submitted result | First record `expired`, then store one submitted result | Store one submitted result | Return the exact stored result; no scoring, event, revision, timestamp, or state change |
| `abandon`, `restart` | Write ahead and publish one `abandoned` transition (restart also publishes the replacement and selects it) | Atomically record `expired`, then return exit 4 | Exit 4; no change | Exit 4; no change |

Abandoned attempts behave like submitted ones for every command above except
that `submit` is also exit 4: an abandoned attempt is never scored. A repeat
`abandon` at the same expected revision, or a repeat `restart` with the same
operation ID and arguments, returns the stored outcome without writing.

The expiry transition in the “active at/after deadline” column is the one
permitted mutation for that observation. Rejection itself does not append a
second event or revise the state. Every state change is made while holding the
attempt lock and is paired with exactly one event by persistence services.

## Restart transaction

A restart abandons one active attempt and creates its replacement as a single
recoverable operation (`WorkspaceManager.restart_attempt`). The caller supplies
a `restart-request/v1`: an operation UUID, the old attempt ID and its expected
`revision`, and the target pinned assessment and profile. Those fields are the
operation's identity: reusing the UUID with any of them changed is a conflict
(exit 4), and an identical repeat returns the original replacement ID without
touching the current selection, even after that replacement was submitted or
another attempt was selected.

Locks are taken in the order workspace, old attempt, then the transaction-owned
replacement staging; the workspace lock is never taken while an attempt lock is
held. A busy old attempt (for example, one being scored) is a bounded exit 4,
not a wait. Before anything is staged the old attempt must be `active`, before
its deadline, and at the expected revision; the target must be the installed
content and a supported profile.

The replacement is staged through the same verified creation path as `start`,
then `attempts/.restart-journal/<operation>.json` (`restart-journal/v1`,
checksummed) is written. That file is the commit point. It holds the old
attempt's exact prior and abandoned states and event, the replacement's state
and `started` event, the staging name, and the selection the pointer is
expected to hold. Before it is durable, any failure leaves the old attempt
active and selected and removes only the staging directory. After it, the
operation is published in order: old abandoned state and event, replacement
directory, active pointer, then `attempts/.restart-completed/<operation>.json`
(`restart-completion/v1`, the immutable receipt), then the journal is pruned.
The replacement's timer starts at the timestamp committed in the journal; a
delayed recovery does not extend it.

A storage failure after the commit point is reported as exit 3 with the
operation ID, and the journal stays. Every selection mutation, `reconcile`, and
the explicit recovery entrypoint roll pending journals forward first, before
creation-marker reconciliation, so a published but not yet selected
replacement is never mistaken for an interrupted create. Recovery verifies the
old record is the prior or abandoned state, the replacement is either still
staged or published unchanged, and the pointer is either the expected prior
selection or already the replacement, before it writes anything. Anything else
fails closed with the journal and staging preserved for repair. Metadata and
history reads never run this recovery.

## Attempt history listing

`RuntimeApplication.list_attempts(filters, cursor, limit)` (the reader behind
the history API that 003/03/02 exposes) scans `attempts/` and returns one page
of metadata rows. It reads only each attempt's bounded `session.json`, the
pending-marker directory entries, and the pending restart journals; it never
opens source, review bytes, prompts or event logs, never takes a lifecycle
lock, never runs recovery, and never writes `active.json` or anything else.

- Rows carry attempt ID, schema version, effective and persisted status,
  profile, timestamps, revision, summary scores (submitted `score`, abandoned
  `practice_score`), assessment metadata with `content_identity` and version
  when pinned, `review_available` (presence of `review.json`, not its content),
  and safe issue codes. Never source, paths or capability tokens.
- An overdue active attempt is shown with effective status `expired` while
  `persisted_status` stays `active`; the listing does not persist that expiry.
- Ordering is creation time descending, then attempt UUID descending. Rows
  whose record cannot be read (`record_unavailable`, `record_corrupt`) have no
  creation time and sort after every dated row; they are `available: false`.
  Rows owned by a pending restart (`restart_pending`) or a pending
  finalization (`finalization_pending`) are shown with their current metadata
  but `available: false`; a lifecycle command, not the listing, completes them.
- `limit` defaults to 25 and may not exceed 100. `next_cursor` is an opaque
  ordering boundary bound to the filters it was issued for; a malformed cursor,
  a cursor issued for different filters, an unknown filter key, or an unknown
  status is exit 2. Records may move between pages while attempts are created
  or removed: a page is a refreshable view, not a snapshot.
- Symlinked or non-UUID entries are skipped and counted in the
  `unsafe_entries_skipped` warning; unavailable rows hidden by an active filter
  are counted in `unavailable_records_excluded_by_filter`; an unreadable restart
  journal is `restart_journals_unreadable`. There is no cap on how many attempts
  a workspace may retain.

## History, review and action routes (web API)

All routes below require the capability token; POST routes also require the
exact loopback Origin. Attempt IDs in paths must be canonical lowercase UUIDs
and are validated before any filesystem access (422 `invalid_input`); an
unknown action or extra path segment is 404 `not_found`.

| Route | Behavior |
| --- | --- |
| `GET /api/attempts?status=&assessment_id=&cursor=&limit=` | The history listing page (`items`, `next_cursor`, `warnings`, `filters`, `limit`). Unknown or empty query keys and a non-decimal limit are 400 `invalid_query`; a malformed cursor, a cursor issued for other filters, an unknown status or a limit outside 1–100 are 422 `invalid_input` with the same message the CLI prints. An unsafe or unreadable `attempts/` directory is 404 `history_unavailable`. |
| `POST /api/attempts` | Unchanged start (201), refused with 423 `lifecycle_locked` while a live attempt is selected. |
| `GET /api/attempts/{uuid}/review?include_source=true\|false` | The stored review of that attempt as `attempt_reviews` assembles it: stored metadata, `content_identity`, `source_binding`, verified source (unless `include_source=false`), score, issue codes. Never selects, repairs or rescores; an unknown attempt is 404 `session_unavailable`, a pending finalization is 503 `review_pending`. |
| `POST /api/attempts/{uuid}/abandon` body `{"expected_revision": N}` | Ends the attempt; returns `{"session", "newly_abandoned"}` (200). A repeat at the same revision returns the stored record with `newly_abandoned: false`. |
| `POST /api/attempts/{uuid}/restart` body `{"operation_id", "expected_revision", "mode"?, "drill_duration_seconds"?}` | Runs the restart transaction; 201 with `replacement_attempt_id`, `session` (the replacement), `abandoned_session`, `committed_at`, `replayed: false`. An identical repeat is 200 with `replayed: true` and `session: null`. |

Action errors: `stale_revision` and `operation_conflict` are 409 with their
CLI message, `recovery_pending` is 503 (the restart is committed; retry the
same operation ID), a terminal or live-selection refusal stays 423
`lifecycle_locked`, and body validation failures are 422 `invalid_input`.
Unauthorized requests get the existing 401/403 envelopes and never name an
attempt or path.

## Browser routes (web shell)

The browser keeps its screen in the URL path so reload, back and forward
rebuild it; the capability stays in the fragment only until `captureCapability`
removes it, and the fragment then carries only non-secret view state
(`attempt_id`, `level`, `tab`). No source text ever enters a route.

| Path | Screen | Requests on load |
| --- | --- | --- |
| `/` | Practice library: exercise cards with readiness/setup from the bootstrap `catalog`, the selected session summary with an explicit resume action, the History entry, one start form whose confirmation is the only place that posts `/api/attempts`. | `GET /api/bootstrap`, `GET /manifest.json` |
| `/attempt/{uuid}` | A cold load (reload, back, forward, typed address) shows the continue screen: exercise, status, format and server deadline with "Reconnect to active session" or "View final session" and Back to library. Only that explicit action requests the source and opens the editor or the read-only view. Loading never mutates anything; an unknown UUID is "Attempt not found" with Back to library. | bootstrap; `GET /api/time` only when the UUID is not the selected session. After the explicit action: `GET /api/time`, `GET /api/source` for that attempt only |
| `/history` | Attempt history: exercise/status filters, rows per page (the control offers 10/25/50/100, the fragment accepts 1–100, default 25), newest-first rows with status, format, start time, result summary, review availability and per-row unavailability with issue codes, aggregate warnings for skipped entries, Newest/Older paging with a refresh note on older pages, Review and (for the selected active attempt only) Resume. Filters and cursor live in the fragment (`#status=&assessment_id=&cursor=&limit=`); a malformed fragment value falls back to the default with a visible notice, and a cursor the server rejects shows "Show newest". | bootstrap, `GET /api/attempts?…` only |
| `/history/review/{uuid}` | Read-only review: stored metadata (exercise, pinned content version or "unavailable (legacy record)", status, format, timing, record version), the result labelled honestly ("Final result" only for a submission; "Last practice result" for expired/ended attempts, from `score` or `practice_score`), legacy banners for `submitted_source_binding_unavailable`, `submitted_source_was_unreadable`, `legacy_source_unavailable` and missing content identity, and the source with its binding named (submitted bytes with digest, current file "not proven submitted", or "Saved work (not a submission)" read by explicit id). "Retry this exercise" is disabled with the reason when the exercise is not installed or needs setup; otherwise a confirmation dialog states the mode and any content-version difference; with a live attempt it offers Resume active attempt / End it and start a new attempt / Cancel and never displaces silently. Opening a review never selects the attempt. | bootstrap, `GET /api/attempts/{uuid}/review`, plus `GET /api/source?attempt_id=` for a never-submitted attempt |

### Attempt actions in the browser and their CLI equivalents

The attempt screen's action bar carries three distinct lifecycle controls, each
behind a confirmation dialog, and every one runs under the attempt's operation
lock (an in-flight save, Run Tests, Submit or another lifecycle action disables
them). Before End or Restart the editor buffer is flushed; when the latest text
cannot be saved (failed save or unresolved conflict) a second dialog asks for an
explicit "Discard unsaved edits" decision, and cancelling keeps the attempt
untouched.

| Control | Effect | CLI equivalent |
| --- | --- | --- |
| Reset source | `POST /api/source/reset` replaces the current source with the attempt baseline; the attempt ID, status, revision and timer are unchanged. | No CLI command: edit the attempt's `simulation.py` and save with the editor or `resume`. |
| End attempt | `POST /api/attempts/{uuid}/abandon` at the revision read from a fresh `/api/time`; the attempt becomes `abandoned` (shown as "Ended"), saved work stays readable. | `abandon --attempt <uuid> --expected-revision N` |
| Restart | `POST /api/attempts/{uuid}/restart` with an operation UUID minted once per confirmed restart and reused for every retry (stale revision mints a new one); the replacement opens directly at `/attempt/<replacement>`. | `restart --attempt <uuid> --expected-revision N [--operation-id UUID]` |

Failures map to visible, retryable states: `stale_revision` and
`lifecycle_locked` refresh the view from `/api/time` (a terminal attempt renders
read-only), `operation_conflict` and `recovery_pending` ask for the same
Restart again, and an unreachable server keeps the operation ID for the retry.

The server serves `index.html` (with the shell Content-Security-Policy) for `/`,
`/index.html`, and every path under `/attempt` or `/history` without a query
string; the path never selects a file, so the client's route validation decides
between a screen and "Page not found" with Back to library. All other paths
remain flat asset names or 404.

## Stable exits

| Exit | Meaning |
| --- | --- |
| 0 | Command completed, including expired `status`/`time` and every successfully finalized `submit`, even when stored groups failed or errored. |
| 2 | Invalid input, including malformed identifiers, unsupported schemas, invalid profiles, or invalid durations. |
| 3 | Session unavailable or corrupt, including no valid active pointer, malformed persisted state, a saved assessment that no longer matches the registry, or a committed restart whose publication is still pending. |
| 4 | Illegal lifecycle operation or lock contention, including a stale expected revision or a restart operation ID reused with different arguments. |
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
├── abandon [--json] [--workspace-root PATH] [--attempt UUID]
│           --expected-revision N
├── restart [--json] [--workspace-root PATH] [--attempt UUID]
│           --expected-revision N [--operation-id UUID]
│           [--mode {full,drill}] [--drill-duration-seconds SECONDS]
├── history [--json] [--workspace-root PATH]
│           [--status {active,expired,submitted,abandoned}] [--assessment ID]
│           [--cursor CURSOR] [--limit N]
├── review  [--json] [--workspace-root PATH] --attempt UUID [--no-source]
├── context [--json] [--workspace-root PATH] [--attempt UUID]
            [--format {markdown,json}]
└── web     [--json] [--workspace-root PATH] [--port PORT] [--no-open]
```

`history` prints one page of the attempt history listing described below and
`review` prints one attempt's stored review (see "Submission review record");
both are read-only, take no lifecycle lock, and never change the active
selection. `review` requires an explicit `--attempt`: it never resolves the
active pointer. Both exit 2 for a malformed cursor, unknown filter or unknown
status, with the same message the web API returns.

`abandon` ends the selected active attempt explicitly: its state becomes
`abandoned` with `ended_at`, the reason `ended`, and the last practice score;
nothing is scored, deleted, or submitted. `restart` does the same with the
reason `restarted` and creates a replacement in one recoverable operation (see
"Restart transaction"); the replacement defaults to the old attempt's
assessment and profile and is always pinned to the installed content.
`--expected-revision` is required on both: it is the revision the decision was
made against, and a different current revision is a stale-state conflict
(exit 4, code `stale_revision`) rather than an action on state the caller never
saw. A repeat `abandon` at the same expected revision returns the stored record
with `newly_abandoned: false`. `restart --operation-id` is the idempotency key;
when omitted the CLI mints one and echoes it as `operation_id` so a retry after
a failed response can reuse it and receive the original replacement
(`replayed: true`, `session: null`). `--drill-duration-seconds` requires
`--mode drill`.

Live-selection policy (D001), identical for CLI and browser: a plain `start`
never displaces a selected attempt that is still active (exit 4, code
`live_selection`); the user resumes it, or ends or restarts it first. Naming a
different attempt with `resume --attempt` while the selected one is live is the
same conflict. Terminal and non-selected attempts stay discoverable and
reviewable; an explicit `resume --attempt` also repairs an unreadable pointer.
Source reset is a different action: it changes only the current attempt's
source, never its ID, timer, or selection.

Error envelopes carry the exit-code family name (`invalid_input`,
`session_unavailable`, `illegal_lifecycle`, `candidate_failure`) unless a more
specific stable code applies: `stale_revision`, `operation_conflict`,
`live_selection` (all exit 4), and `recovery_pending` (exit 3).

Common options are intentionally after the subcommand. `--workspace-root`
defaults to the current working directory. `--attempt` must be a canonical,
lowercase UUID. An explicit `--attempt` is passed to the application adapter
and takes precedence over the active pointer; the CLI never selects the newest
directory or guesses an attempt from a timestamp. `start --mode full` rejects
`--drill-duration-seconds`, and every supplied duration must be positive.

`fetch`, `start`, `resume`, `status`, `time`, `task`, `test`, `submit`, and
`context` use production application adapters. `web` binds only to
`127.0.0.1`, emits a capability URL whose token stays in the URL fragment, and
blocks until stopped. Tokens are URL-safe ASCII capabilities carrying at least
256 bits. `--no-open` suppresses the injectable browser opener. Browser
evaluation responses include `newly_submitted`, which is true only for the
request that first finalizes an attempt.

Use `--port 0 --no-open` for a safe operator launch when an available port
should be selected and the URL will be opened manually:

```sh
codesignal-sim web --workspace-root PATH --port 0 --no-open
python3 -m codesignal_practice_simulator web --workspace-root PATH --port 0 --no-open
```

The entire printed URL is a private, per-launch capability. Keep its fragment
when opening it locally, but do not store or share it. The fragment is not part
of an HTTP URL; after loading, the browser sends its value to the same
loopback origin as the `X-Simulator-Token` header, not an `Authorization`
header. It can therefore appear in captured request diagnostics. Restarting
`web` rotates that capability. The new server reconnects to the selected
attempt's durable state; it does not reset, extend, or create a duplicate
attempt.

The browser entry flow requires confirmation. Only confirmation creates an
attempt and starts its server-authoritative timer. The timer cannot be paused,
extended, or reset by the browser. An expired browser session is read-only:
its source and stored results remain available, but **Submit** is disabled.
The CLI `submit --workspace-root "$workspace"` remains available for that
expired state and finalizes it once. A browser refresh or reconnect after that
CLI action presents the stored submitted result.

`test` and `submit` use the
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

## Browser source document and concurrency

The browser source document is candidate-owned. It autosaves debounced edits
through compare-and-swap revisions (ETags), rather than letting a client
overwrite a newer source copy. A stale save or action receives a conflict:
the browser preserves local text and requires an explicit choice to reload the
server version or copy the local version after refreshing its revision.
Candidate-only history is bounded and supports explicit reset and restore.

Final (`expired` or `submitted`) sessions reject source mutation. A `test` or
`submit` request that carries source content for an expired or abandoned
attempt is refused as read-only (exit 4; HTTP 423) instead of being silently
dropped, and nothing is written. Content identical to the saved source is not
a mutation: it is ignored, and an expired `submit` still finalizes the saved
revision once. A request against an already submitted attempt returns the
committed result whatever it carries, and never saves or rescores. Source and
history ownership still belongs to the candidate: an agent must ask explicit
permission before reading either and separately before editing source. Browser
or CLI access does not grant permission to inspect fixtures, copied tests,
reference, solution, study, or hidden-test material.

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
