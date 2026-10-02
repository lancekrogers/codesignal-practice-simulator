# User flows and state boundaries

These flows refine D001–D004. They are intended behavior, not implemented screens.

## Main practice loop

Library → choose assessment/profile → confirm start → active attempt → confirm
submission → read-only review → history or retry → fresh attempt.

The server starts the timer only on confirmed creation. Selecting a card, opening
history, or looking at old results never starts, pauses, or resets a clock.

## Entry points

| Screen/state | Primary actions | Data that must remain unchanged |
| --- | --- | --- |
| Library, no live selection | Start an available exercise; open history | All previous attempts |
| Library, live selection | Resume; explicitly end/restart; history | Old source/timer until confirmed transition |
| Active attempt | Save, test, submit, reset source, leave, end, restart | Leaving alone preserves lifecycle |
| History | Filter/page; review; resume an eligible active attempt | Current selected attempt and its deadline |
| Submitted review | Read stored result/source; retry; back to history | Submitted bytes/results and active selection |
| Expired/abandoned review | Read saved work and last practice score; retry | No fabricated submission or timer extension |
| Legacy/unavailable detail | Read available metadata/results; see precise warning | No silent upgrade, repair, or rescore |

## Restart an active attempt

1. User chooses Restart (not Reset source). Explain that the old attempt will be
   kept as abandoned and the replacement receives fresh source and a new timer.
2. Cancel preserves the local editor buffer and current session.
3. Save/flush pending edits before confirmation can commit. On conflict/failure,
   offer retry or an explicit discard-unsaved-local-text choice; never imply the
   discarded text was saved. Existing persisted source is always retained.
4. Disable duplicate transition controls while the operation is in flight. Keep
   the operation UUID across a lost response/retry; obtain the same replacement.
5. Successful response navigates to the explicit replacement ID. On an uncertain
   outcome, show recovery status rather than issuing a fresh start request.
6. A stale tab receives a conflict and reload/resume action. If submit won the
   race, offer review/retry; never reclassify a submitted attempt as abandoned.

## Review while practicing

The user can return to the library/history while the active timer continues,
open an older submission and return to the active attempt. Review routing carries
only the chosen UUID and view/filter state; it never rewrites active.json.
Retry from an old review while another attempt is live must offer resume versus
explicit end-and-start; do not hide or silently replace the live work.

## Legacy and content-version changes

Old submissions show persisted score/timing and an honest warning if exact
submitted-source binding was never stored. Missing code does not hide the score.
An unavailable old assessment version does not hide stored metadata/results.
Retry defaults to the current installed version with a visible version-change
notice. Continuing an existing attempt does not silently swap its content/tests.

## Navigation and accessibility

Support validated library/attempt/history/review routes, browser back/forward,
reload and recovery after server restart. Preserve history filters when returning
from review. On route change focus the main heading; confirmation cancellation
returns focus to its opener. Label source reset, leaving, abandonment and restart
distinctly. No source or capability is written into URLs or history state.

## Verification matrix

For each accepted exercise, cover full/drill, new/repeated attempt, submit and
review, expiry, abandon/restart, server restart and old-history navigation. Include
keyboard actions, empty/partial-error history, changed cursors, missing resources,
legacy unknown binding, save conflict, interrupted operation and stale tab races.
Assert persisted IDs, source hashes, timestamps, scores and selection through
synthetic harness evidence, not only displayed labels.
