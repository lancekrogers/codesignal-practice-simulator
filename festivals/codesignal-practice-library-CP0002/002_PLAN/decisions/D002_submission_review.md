# D002 — Immutable review records and non-mutating legacy reads

Status: proposed for plan approval. Resolves G2/G4; R5–R8.
Anchors: models.py:338, models.py:521, persistence.py:172, lifecycle.py:315,
candidate_documents.py:52 (all under src/codesignal_practice_simulator/).

## Choice

New submissions publish a versioned immutable review record with attempt ID,
assessment identity/version/content digest, submitted source digest and bytes
(or an immutable digest-checked member), score summary, safe per-level outcomes,
start/deadline/submitted timestamps, and profile. No raw candidate stdout or
invented official hidden-test claims.

Extend the existing write-ahead submission transaction to cover review bytes,
state, and event. Recovery publishes the exact previously recorded result and
never reruns the scorer. The submitted state's review digest identifies its record.
Hash mismatches are corruption, not permission to regenerate the result.

Rejected: displaying current simulation.py as proven submitted source, rescoring
on review, or maintaining a separate mutable browser-local submission database.

## Capture and concurrency

Use the existing application/evaluation service and persistence locks. Save with
expected ETag, capture source, and evaluate that same revision under one
cross-process attempt synchronization boundary; do not rely on only an in-process
application mutex. Where runner isolation needs a materialized snapshot, use a
transaction-owned immutable scoring workspace with the existing -I/-S/environment,
bounded output, and process-group constraints. Do not introduce a second scorer.
Verify scored bytes/digest before committing. Same-user arbitrary filesystem
tampering is not made impossible; detected changes must not produce a falsely
bound review record.

Expired submit must not silently ignore caller-provided source. Reject a mutation
payload for expired/abandoned sessions with a terminal/read-only error; explicit
expired submit without new source may finalize the saved revision as before.
Repeated submitted requests return the existing committed result, not a new
capture of the current file. This closes the payload ambiguity observed at
application.py:418–429; document and test the response contract change.

## Legacy behavior

Read v1 state directly through validated, bounded, non-repairing readers.
A v1 submitted attempt can display stored score/timestamps and separately
available legacy source with an explicit “submitted-source binding unavailable”
label. Missing detail is unavailable, not zero or failed. Do not create baselines,
history snapshots, migrated sessions, or missing events as a side effect of GET.
Do not require the current catalog entry to render stored metadata/results.
Mutation/scoring still require a valid installed assessment definition.

## Amendment 2026-09-11 (execution): identity and source-binding axes

Recorded after 003/01/01 showed v1 records cannot carry creation-time identity
(see 003_ATTEMPT_LIFECYCLE/01_schema_and_review/results/submission_dependency.md).
Reviews report three independent axes; none is inferred from another:

- stored_metadata: what the session file holds (assessment id/name/levels,
  profile, status, timestamps, score). Always shown when the record is valid.
- content_identity: `pinned` (v2 attempts created by 003/01/02 onward, verified
  against staged bytes) or `unavailable` (v1 attempts; also v1 records upgraded
  by restart/abandon). Never looked up from today's registry or manifest.
- source_binding: `captured` (immutable review.json written by the submission
  WAL and verified against its state), `not_captured` (submitted before capture
  existed, e.g. an old-release submission or a replayed submission-recovery/v1),
  or `not_applicable` (no submission).

A v1 attempt submitted by this release gets `captured` source with `unavailable`
content identity. Task order cannot invent pins for old records; the
creation-identity task precedes capture only so that new attempts have real pins.

## History/read boundary

Metadata-only listing never loads source. Detail requires an explicit attempt ID
and loads source only for the requested review. Read attempts by validated UUID
directory names, reject symlinks/traversal, enforce byte limits, and verify record
identity matches directory identity. Read/recheck revisions or digest-checked
immutable records to avoid mixed generations; a changing record returns retryable
unavailability rather than a Frankenstein response.

History/read requests do not change active.json, expire sessions on disk, repair
journals, or initialize source history. An overdue active record can display an
effective expired status with persisted status separately documented.

## Tests

Assert complete directory hashes unchanged by legacy/terminal review and listing;
no rescore calls; source and result remain bound across save/submit races and
recovery; removed catalog versions and missing legacy source remain understandable;
digest tampering/oversized files/symlinks fail safely. Test review while another
attempt stays active and its original deadline continues.
