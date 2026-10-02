# Requirements and acceptance

All P0 items belong to this festival; none are deferred to an invented phase 2.

| ID | Priority | Requirement | Observable acceptance |
| --- | --- | --- | --- |
| R1 | P0 | Assessment library | Select multiple distinct exercises with descriptions, progressive levels, and supported timing modes; wrong/removed IDs produce actionable errors. |
| R2 | P0 | Original content | Additional Python exercises include prompts, starter code, deterministic level checks and offline packaging; not just catalog placeholders. Proposed baseline: two new four-level tracks, in-memory records and account ledger, alongside File Storage. |
| R3 | P0 | Unlimited repeat practice | Repeating an exercise creates distinct attempt IDs with fresh source and server deadlines; no fixed attempt cap or manual deletion. |
| R4 | P0 | Abandon/restart | Confirm intent, preserve old attempt and saved code, mark it honestly abandoned without fabricating a submission score, and start a new attempt. Cancel leaves original work intact. |
| R5 | P0 | History | Browse metadata for active/submitted/expired/abandoned attempts, filter by assessment/status, and open a particular ID even if it is not selected. Empty/missing/corrupt entries have explicit safe behavior. |
| R6 | P0 | Submission review | Read-only submitted source, score, per-level outcomes, mode and timestamps correspond to the reviewed attempt, not today's active attempt. Legacy unavailable detail is labeled unavailable. |
| R7 | P0 | Non-mutating review | Browsing old work does not switch active selection, reset its timer, rescore it, or permit mutation of terminal attempts. |
| R8 | P0 | Data compatibility | Previously valid attempts remain readable; migration/version upgrades do not overwrite source or silently drop results. Missing assessment versions do not prevent metadata review. |
| R9 | P0 | Recoverable operations | Duplicate clicks, concurrent tabs, restart/submit races, crashes between old/new writes, and save conflicts cannot produce duplicate restarts or lose prior work. Define idempotency and recovery in PLAN. |
| R10 | P0 | Integrated UX | Library → start → practice → submit → history → review → retry works by mouse and keyboard after reload/restart. Back navigation and source-reset labels are unambiguous. |
| R11 | P0 | Offline verification | Existing plus new exercises work in installed offline distribution; synthetic tests cover lifecycle, content correctness, security, and legacy data. |

## Clarifications for planning

- Original Python problems are the recommended direction; track names/count above
  are proposed, not a claim of explicit content-spec approval.
- Restart means a fresh attempt, not extending/resetting an active timer in place.
- Source reset remains a distinct operation within one attempt.
- User review of their own saved work does not grant an agent permission to read it.
- Store only honest result detail: no invented official/hidden-test equivalence.

## Out of scope

Cloud accounts, proctoring, collaboration, additional languages, silent deletion,
and scraping proprietary assessment content. Retention is non-destructive by
default; automatic pruning is not part of this request.
