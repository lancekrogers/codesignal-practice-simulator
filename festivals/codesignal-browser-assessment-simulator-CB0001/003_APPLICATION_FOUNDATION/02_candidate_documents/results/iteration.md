# Candidate Document Iteration

All material findings were addressed:

- Split JSON-safe contracts, storage primitives, and orchestration into
  `candidate_document_models.py`, `candidate_document_storage.py`, and
  `candidate_documents.py`, with public re-exports.
- Added strict text normalization and stable domain-error conversion.
- Added public `Persistence.atomic_json` instead of private-method coupling.
- Added durable monotonic operation order, duplicate-order corruption checks,
  deterministic listing/pruning, and recoverable snapshot-before-source order.
- Replaced global service serialization with attempt-scoped lock behavior and
  independent-service race tests.
- Strengthened reset, final-state, missing-file, symlink, ownership, exact
  forbidden-byte, history, orphan, serialization, and crash tests.
- Ensured final attempts are rejected before legacy baseline creation.
- Split tests into cohesive files below 500 lines.

Final rerun: 24 focused and 187 full tests passed; legacy, compile, and diff
checks passed. No P0/P1 requirement was deferred and no exclusion was relaxed.
The sequence is commit-ready.
