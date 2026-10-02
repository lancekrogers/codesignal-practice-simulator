---
fest_type: task
fest_id: 02_implement_candidate_read_and_cas_save.md
fest_name: implement candidate read and cas save
fest_parent: 02_candidate_documents
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:27.858038-06:00
fest_updated: 2026-09-09T04:58:07.699145-06:00
fest_tracking: true
---


# Task: implement candidate read and CAS save

## Objective

Implement locked candidate-source reads and optimistic-concurrency saves that atomically replace only the selected attempt's registered `simulation.py`.

## Requirements

- [ ] Add `CandidateDocumentService.read(attempt_id)` and `save(attempt_id, content, if_match)` with regular-file/symlink, UTF-8, 256 KiB, active/unexpired, and canonical ETag checks.
- [ ] Acquire selection through `WorkspaceManager.selected_attempt()` or the documented equivalent, then use `Persistence.attempt_lock` without acquiring locks in reverse order.
- [ ] Write an immutable predecessor snapshot before atomic replacement; map stale ETags to a typed conflict carrying the current document/ETag without overwriting the user's version.

## Implementation

Follow these steps in order:

1. Resolve the selected session and `AssessmentDefinition` under the existing workspace/attempt lock discipline; derive `attempt / definition.candidate_filename` and reject anything not a regular non-symlink file.
2. Read bytes, decode strict UTF-8, enforce the byte limit, compute `sha256:<hex>`, and return a `CandidateDocument` with attempt ID, filename, content, revision, and ETag.
3. For save, validate canonical `if_match`, compare it with the persisted ETag, create an immutable predecessor JSON snapshot atomically, then call `Filesystem.write_bytes`, `flush_file`, `replace`, and `flush_directory` using a sibling temporary file.
4. Add focused tests for happy read/save plus stale ETag, simultaneous writes, invalid UTF-8, 256 KiB + 1, symlink swaps, missing files, expiry, submission, and arbitrary filename/path attempts.

### Safety and content isolation

The handler must never pass a path; the service must derive one filename from the registered assessment. Never follow symlinks, accept lifecycle-final writes, or return internal filesystem paths in errors.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] A successful save returns the new content and ETag and leaves a recoverable predecessor.
- [ ] A stale save returns a typed conflict/current ETag and leaves the persisted source byte-for-byte unchanged.
- [ ] All focused document/persistence tests pass, including race and unsafe-file cases.
