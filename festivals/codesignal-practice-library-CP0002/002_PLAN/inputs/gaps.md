# Gap analysis

Reviewed accepted ingest specs and CONTEXT.md. These are design decisions, not
reasons to omit parts of the requested practice workflow.

## G1 — Restart is a multi-record operation

Existing creation staging/rollback in workspace.py:145 does not cover changing
the old attempt. Define durable operation identity, lock order, interruption
points, retry behavior, and the outcome when the replacement cannot be published.
Recommended invariant: never delete the prior attempt, never silently submit it,
and never create multiple replacements for one confirmed restart. Separate
explicit abandonment from restart and preserve the original deadline.

## G2 — Terminal review needs honest result/source binding

lifecycle.py:315 journals submission state/events without an explicit scored
source snapshot in that interface. Specify where new submitted source bytes,
digest, assessment version, and result become one recoverable committed outcome.
Older attempts must show stored results and available source without claiming
a historical binding the old schema did not record. No rescoring on review.

## G3 — History must be independent of selection and current catalog

application.py:174 exposes only selected state; workspace.py:310 validates it
against the current registry. Define metadata-only listing, safe legacy reads,
filtering/sorting/pagination, and per-entry corruption handling. Viewing one old
attempt must not change active.json or disable the user's ongoing practice.
Do not use source-history APIs as an attempt index.

## G4 — Read-only must actually avoid writes

candidate_documents.py:52 and :69 initialize a baseline during read/history.
Design review paths that do not mutate legacy attempts or regenerate source.
Specify safe response behavior for a missing snapshot, unavailable assessment
version, unsupported schema, symlink, and source/result digest mismatch.

## G5 — Original exercises cannot depend on File Storage fetch

application.py:343 and workspace.py:116 validate the entire existing fixture
cache before creation. Introduce an assessment-specific validated input source
contract with separate packaged-original and pinned-fetched implementations.
Do not relax legacy cache checks. Pin content identity in attempts and prove
original exercises work from a wheel outside the checkout with no fixture fetch.

## G6 — Concrete additional content

Recommendation: two original four-level Python tracks, in-memory records and
account ledger, plus File Storage. Before authoring content, settle exact track
count, progression, supported timings, and correctness examples. The user asked
for multiple assessments; these particular track names were not explicitly
selected. Architecture/task decomposition can proceed without pretending they
were. Ask once at plan presentation if no further preference has arrived.

## G7 — UI and CLI consistency

Browser start guards live selection while CLI start differs (lifecycle.py:82).
Specify the one-active-selection policy and explicit restart semantics for both.
Handle autosave failure/conflict, test/submit in flight, stale tabs, refresh,
terminal review, and return navigation. Keep source reset distinct and labeled.

## Planning outputs required

For G1–G5/G7, record options, chosen contracts, and negative acceptance tests in
decision records. G6 remains a visible content proposal. Every requirement R1–R11
must map to an executable implementation task and a release check. Do not add a
database, hosted service, or another runner without an evidenced need.
