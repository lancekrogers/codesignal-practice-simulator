---
fest_type: task
fest_id: 01_define_document_contracts_and_initial_source.md
fest_name: define document contracts and initial source
fest_parent: 02_candidate_documents
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:27.737338-06:00
fest_updated: 2026-09-09T04:58:07.43207-06:00
fest_tracking: true
---


# Task: define document contracts and initial source

## Objective

Define the typed candidate-document/history contract and create a durable attempt-local initial source baseline required for safe reset.

## Requirements

- [ ] Create `src/codesignal_practice_simulator/candidate_documents.py` with immutable `CandidateDocument`, `SourceSnapshot`, and `SourceHistory` records plus stable domain errors for conflict, unsafe document, oversize, invalid UTF-8, and read-only state.
- [ ] Use `AssessmentDefinition.candidate_filename` from the persisted registry session; never accept a browser-supplied path or filename.
- [ ] Extend `WorkspaceManager._populate_staging` in `workspace.py` to capture the initial `simulation.py` bytes/digest in an attempt-local metadata file using the existing atomic filesystem primitives, with a locked legacy fallback.

## Implementation

Follow these steps in order:

1. Define explicit schema constants, 256 * 1024 byte limit, `sha256:<hex>` ETag formatter, and UUID validation helpers in `src/codesignal_practice_simulator/candidate_documents.py`; keep records JSON-safe and separate from `models.py` lifecycle revisions.
2. Add a private initial-source record such as `.candidate-initial.json` beside the copied candidate file; write it after the registered source copy and before attempt publication in `WorkspaceManager._populate_staging`.
3. For legacy attempts missing the record, initialize it under `Persistence.attempt_lock` from the regular registered candidate file, then atomically publish the baseline and document that reset uses this fallback.
4. Add `tests/test_candidate_documents.py` for record round-trips, exact size/UTF-8/ETag validation, new-attempt baseline creation, legacy initialization, and corrupt/symlink metadata rejection.

### Safety and content isolation

Only `simulation.py` may be captured. Do not baseline `test_simulation.py`, prompts, `.scoring`, reference, study, or vendor content; ensure baseline metadata contains hashes/content only for the candidate source.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] The new records and errors have deterministic serialization and reject malformed fields.
- [ ] Fresh attempts contain a recoverable initial candidate baseline; legacy initialization is locked and idempotent.
- [ ] Focused model/workspace/document tests pass without changing lifecycle session revision semantics.
