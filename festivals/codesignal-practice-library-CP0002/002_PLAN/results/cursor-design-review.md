# Cursor focused design review — 2026-09-11

One read-only Cursor ask-mode call used claude-4.6-sonnet-medium-thinking to review
D001/D002 only. Exited 0; no files changed or tests run by the reviewer.

## Incorporated

Completion receipt lookup must precede incomplete-transaction state verification.
Otherwise replay after a replacement progresses beyond its initial state can
incorrectly appear corrupt. D001 now requires request fingerprint validation,
idempotent return of the original replacement ID, and no pointer reselection or
state rewriting on completed replay. Add replay-after-submit and
replay-after-another-restart tests to the journal task.

## Clarified rather than accepted as a proven defect

The reviewer hypothesized old v1 binaries might misparse v2 data. The inspected
current SessionState validator already checks schema version before other fields
(models.py:352), and a future release cannot change already-installed binaries.
D001 now explicitly promises strict version-first dispatch in the new client,
unknown-version no-write errors, and one-way legacy-read compatibility; concurrent
old/new writers are unsupported. This was a compatibility clarification, not a
confirmed existing corruption bug or a promise of retroactive old-client safety.

## Scope

No additional blockers reported for the proposed lock order, timer anchoring,
read-only review, or source/result binding. This is design review, not executed
proof. Implementation must exercise the listed crash/concurrency paths.
