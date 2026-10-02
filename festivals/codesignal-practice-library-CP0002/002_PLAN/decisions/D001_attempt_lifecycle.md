# D001 — Versioned attempts and recoverable restart

Status: proposed for plan approval. Resolves G1/G7; requirements R3/R4/R8/R9.
Anchors (project-relative): src/codesignal_practice_simulator/models.py:338,
lifecycle.py:82, workspace.py:116, workspace.py:145.

## Choice and alternatives

Extend existing filesystem persistence; do not add a database or rewrite the
engine. New records use session/v2 and event/v2 with explicit abandoned state
and content identity. Keep strict v1 readers. Normalize legacy records in memory;
do not bulk-rewrite directories or upgrade records on a history GET. An explicit
lifecycle mutation can upgrade a v1 record through its recoverable transaction.
New software reads both versions; old binaries are not promised to read v2.

Readers in the new release dispatch on schema_version before interpreting fields
and reject unknown versions with a safe newer-client/unsupported-version message
before any mutation. Already-installed old binaries cannot be retroactively
made safe; mixed-version writers in the same workspace are unsupported and must
be documented. Compatibility means the new client preserves/reads old records,
not that every old client can operate on new state. Test unknown-version rejection
and preservation using the new implementation; do not claim an unverified old
binary migration guarantee.

Rejected: clearing active.json (leaves a hidden active attempt), silently submitting
(scores work the user chose to abandon), or resetting deadlines in place (erases
attempt identity and corrupts comparisons).

## State contract

- Active → submitted: existing confirmed scoring/finalization.
- Active → expired: authoritative deadline elapsed.
- Active → abandoned: explicit user action; original start/deadline unchanged.
- Expired/submitted/abandoned are never made active again.
- Expired may be finalized once using existing explicit submit semantics.
- Retry from any terminal state creates a new ID and fresh initial source.
- Restart of the selected active attempt abandons it and creates a replacement.
- Source Reset only resets source within the current attempt.
- Plain start must not silently replace a selected live attempt in either CLI or
  browser. Existing legacy non-selected active attempts remain discoverable;
  selecting one while another is live requires an explicit conflict resolution.
- Abandoned records carry ended_at and reason, and preserve any last practice
  score labeled as practice, never as a final submitted result.

## Restart transaction

Use one caller-supplied operation UUID plus expected old attempt ID/revision.
Canonical request identity includes target assessment/version/profile and old ID.
Reusing a UUID with different arguments is a conflict; duplicate identical requests
resolve to the same replacement ID. Persist completed operation identity, not
only an ephemeral journal.

Lock order for multi-record writes: workspace lock, then old-attempt lock, then
transaction-owned replacement. Never acquire workspace lock from an already-held
attempt lock. Factor locked helpers instead of nesting public reentrant commands.
All workspace-selection mutations reconcile pending restart journals first.

1. Validate selected ID/revision, old status, requested content/profile and storage
   boundaries. Prepare the replacement using transaction-owned staging.
2. Persist a checksummed write-ahead commit intent containing old prior/final
   states, operation identity, replacement identity/state, event IDs, and expected
   pointer. This durable intent is the commit point.
3. Publish old abandoned state/event, replacement directory, then active pointer.
   Record completion before pruning only transaction-owned staging/journal residue.
4. Before commit intent, failure leaves the old attempt active and selectable.
   After commit intent, recovery rolls forward exactly that operation; never
   deletes prior work or creates a different replacement. Report pending recovery
   honestly if storage remains unavailable.
5. Recovery verifies each current record is an allowed prior/target state before
   writing. Unexpected state/corruption fails closed; no blind rollback over
   another attempt. Preserve evidence for operator repair.

Before step 5 state verification, check for an existing completed operation record
and verify its request fingerprint. Matching completion returns the original
replacement identity without rewriting/reselecting it, even if the replacement
has since been submitted or another attempt is selected. Different arguments
still conflict. Only incomplete operations need prior/target state verification.
Keep completion receipt authoritative and immutable after publication.

New timer starts at the server timestamp committed with the replacement; a
delayed recovery does not extend it. Metadata/history reads do not run recovery:
report affected records as temporarily unavailable/pending. Explicit mutations
and server recovery entrypoints own repair.

## Save and race rules

UI waits for autosave; conflict/failure blocks restart unless the user explicitly
chooses to discard unsaved browser text. Saved source in the old attempt remains.
Submit versus restart is serialized by the old-attempt lock: the loser sees a
stale-state conflict, not an implicit second action. Repeated clicks across tabs
cannot create two replacements. Score execution and source writes must use the
same attempt synchronization boundary.

Long-running scoring holds only the chosen attempt lock, not the workspace-wide
lock (workspace.py:223). Resolve implicit selection once under workspace lock,
then pass the explicit ID throughout capture/score/commit. Never acquire workspace
lock while holding that attempt lock. Restart may wait for scoring, but needs a
bounded lock-acquisition failure response rather than freezing unrelated sessions.

## Proof obligations

Inject failures before/after every journal/state/event/rename/pointer/flush boundary.
Assert old source bytes survive, one replacement exists for one operation, and
selection is correct after recovery. Test stale revisions, duplicate and changed
payload UUIDs, v1 mutation, terminal retries, and independent CLI/browser processes.
