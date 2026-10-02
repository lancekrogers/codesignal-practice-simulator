# D004 — Explicit navigation, metadata history, and review APIs

Status: proposed for plan approval. Resolves G3/G7; R1/R3–R10.
Anchors: application.py:174/:245, web/routes.py:120/:177/:208,
webui/src/app.ts:51/:97.

## Service/API boundary

Keep fixed capability-scoped same-origin JSON routes and current error envelopes.
Add catalog GET, GET /api/attempts for metadata listing (POST remains start),
GET /api/attempts/{uuid}/review, and explicit POST abandon/restart actions.
Document exact request/response validators in implementation; no arbitrary paths.
Restart carries operation UUID and expected state revision; return the durable
replacement identity or a conflict/recovery-pending response, not a new ID per retry.
Equivalent CLI commands call the same application services.

Listing includes attempt ID, stored display metadata/version if present, status,
profile, timestamps, summary score, review availability, and safe issue codes;
never source, raw test output, capability, or filesystem paths.

## Listing limits

Start with a filesystem metadata scan: no secondary database/index source of truth.
Bound each record read and each response (default 25, maximum 100 items); stream
directory entries and retain only a bounded page candidate set. Sort by creation
time then UUID descending; cursor encodes a validated ordering boundary and filter
identity. Changes during pagination may require refresh; do not promise snapshot
isolation. A total exact count is optional, not required for navigation.
Reject malformed/mismatched cursors and unknown filters. Skip unsafe entries and
report a safe aggregate warning; a valid-ID corrupt record can be represented as
unavailable without loading source. No cap on how many attempts a user may retain.

## Screens and flows

Library: exercise cards, readiness/setup, full/drill choice, active attempt resume,
and a visible History entry. Choosing start opens confirmation, not the timer.

Attempt: Back to library, clearly labeled Reset source, End attempt, and Restart.
A restart confirmation explains that saved old work is kept, timer restarts only
in a new attempt, and unsaved text must be saved or explicitly discarded.
Save conflicts and evaluations in flight prevent conflicting transitions.

History: assessment/status filters, pagination, newest-first rows and resume/review
actions. Opening review never selects that attempt as active.

Review: read-only code, stored score and per-level outcomes, version/profile/timing,
legacy warnings, Retry this assessment, and Back to history preserving filters.
Expired/abandoned attempts show saved work/last practice score honestly, not a
fabricated submission. Retry when another attempt is live routes through explicit
resume-or-abandon confirmation rather than replacing it silently.

## Navigation and error states

Use a small validated route model in app.ts; preserve capability capture and never
put source or tokens into route state. Browser back/forward and reload reconstruct
library/history/review/attempt routes. Unknown IDs, unavailable catalog versions,
corrupt entries, empty lists, failed requests and stale operations get actionable
recovery. Keyboard focus moves to screen heading; dialogs trap/restore focus.
Do not implement an unrelated frontend framework/router.

## Acceptance

Mouse/keyboard full flow, browser back/forward, reload and server restart; review
old work while a different attempt remains active; paginate/filter with changing
records; unauthorized requests and unsafe IDs; save conflict and duplicate
restart; terminal readonly enforcement verified by both UI and API rejection.
