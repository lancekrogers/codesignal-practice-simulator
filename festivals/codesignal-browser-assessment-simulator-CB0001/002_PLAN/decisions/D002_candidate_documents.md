# D002: Candidate Document Optimistic Concurrency and Recoverable History

**Status:** accepted
**Date:** 2026-09-09

## Context

The browser needs autosave, refresh recovery, reset, and source history while the
scorer continues to read the attempt's registered `simulation.py`. Lifecycle
revisions cannot safely double as source revisions.

## Options

### Let HTTP handlers read and write the file

- **Pros:** minimal code.
- **Cons:** path traversal, race, symlink, lifecycle, and history rules become
  scattered transport concerns.

### Store source in a database

- **Pros:** transactional history.
- **Cons:** introduces a second authority and migration/dependency burden.

### Dedicated file-backed candidate-document service

- **Pros:** fits the existing workspace, locks, atomic writes, scorer, and
  offline model; easy for a human to inspect.
- **Cons:** crash boundaries and bounded history need explicit design.

## Decision

Add `candidate_documents.py`. It resolves only the selected attempt and the
candidate filename from its persisted assessment definition. Reads return
UTF-8 content plus `sha256:<hex>` ETag. Saves require `If-Match`, enforce a
256-KiB limit, reject unsafe/final attempts, and run under the attempt lock.

Before any replacement, atomically create an immutable JSON history snapshot of
the prior source containing schema version, snapshot ID, timestamp, operation,
prior/new hashes, and prior content. Then atomically replace `simulation.py`.
The new content is the current history entry synthesized at read time. This
ordering ensures a successful change can always recover its predecessor; an
orphaned snapshot after a failed replacement is omitted unless its new hash
joins the current source chain. Reconstruct that chain in descending durable
operation order, visiting each record at most once so repeated hashes remain
recoverable. Omit matching no-op records from published history, and retain the
newest 50 content-changing operations. Pruning occurs after a successful
replacement and never affects candidate source correctness.

Reset uses the attempt's copied initial source digest/content captured at
creation; restore copies a validated attempt-local snapshot through the same
CAS path. Source history is separate from `events.jsonl` and never affects
lifecycle revisions.

## Consequences

- `Filesystem` receives only the narrow directory/list/stat primitives needed
  for snapshots; all safety rules stay in the service.
- Test and submit routes save with CAS first, then evaluate the persisted file.
- The API maps a stale ETag to HTTP 409 and returns the current ETag, never a
  blind overwrite.
- Terminal agents continue to see a normal `simulation.py`.
