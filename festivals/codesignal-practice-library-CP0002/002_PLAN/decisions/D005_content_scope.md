# D005 — Initial content proposal

Status: awaiting user topic/count preference; not a technical blocker to planning.

Keep File Storage. Propose two new original four-level Python exercises:
- In-Memory Records: basic records/fields, deterministic filtering, expiry, and
  time-consistent snapshots/restoration.
- Account Ledger: accounts and transfers, aggregate rankings, scheduled operations,
  and historical balances with explicit identity/time rules.

These are topic/progression proposals, not copied CodeSignal specifications.
Before authoring, define exact signatures, return/error conventions, ordering,
time units, level dependencies, examples, and deterministic correctness contracts.
Retain full 90-minute and drill modes initially to match the existing runner.

Alternative: user-supplied licensed/owned exercises. That requires explicit source
and redistribution terms and must not be inferred from a request for more tests.

The user has been asked once in this planning turn to confirm these three initial
assessments. Record the response here before content implementation. Do not claim
a local model's plan approval constitutes the user's content preference.

## Resolution (2026-09-12, coordinator on the user's delegation)

Status: decided. The user, asked at the end of 003/02, delegated the open
decisions to the coordinator ("make these decisions yourself, think about the
intent"). Decision: the initial content set is the three assessments above —
File Storage (existing) plus the two original Python tracks, In-Memory Records
and Account Ledger — in full 90-minute and drill modes.

Rationale: the request's intent is repeatable practice across multiple
assessments in the same four-level stateful-system shape that the existing
runner and UI already handle; both tracks fit that shape and exercise
progressively harder state, time and identity rules the way File Storage does.
They are original topic/progression proposals, so no licensing or
redistribution question arises. The user-supplied-exercise alternative stays
available later through the catalog and input-provider seam (D003/004-01)
without changing this decision. 004/02_original_content must still define the
exact signatures, conventions, examples and deterministic correctness
contracts before authoring, as required above.
