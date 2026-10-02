---
fest_type: task
fest_id: 03_implement_source_history_reset_and_restore.md
fest_name: implement source history reset and restore
fest_parent: 02_candidate_documents
fest_order: 3
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:27.973371-06:00
fest_updated: 2026-09-09T04:58:07.956592-06:00
fest_tracking: true
---


# Task: implement source history reset and restore

## Objective

Complete bounded attempt-local source history, explicit restore, and initial-source reset through the same CAS and atomic-write path.

## Requirements

- [ ] Implement `list_history`, `preview_history`, `restore`, and `reset` on `CandidateDocumentService` using opaque UUID snapshot IDs and the current ETag.
- [ ] Retain the newest 50 distinct predecessor hashes, deduplicate orphan duplicate snapshots, and prune only after a successful replacement.
- [ ] Restore and reset must require a matching ETag, validate snapshot ownership/content, record a predecessor, and reject expired/submitted attempts.

## Implementation

Follow these steps in order:

1. Store snapshots under an attempt-local `.candidate-history/` directory with schema version, snapshot UUID, timestamp, operation, prior/new hashes, and prior UTF-8 content; reject symlinked directory/records.
2. Implement `list_history` sorted newest-first and synthesize the current source as the newest view when needed; expose previews only through the service, never through arbitrary file reads.
3. Route restore and reset through a private `_replace_locked` helper used by CAS save so ordering, ETag checks, atomic replacement, history retention, and error mapping cannot drift.
4. Add tests for multiple revisions, duplicate hashes, newest-50 pruning, restore-to-prior, reset-to-initial, stale restore/reset, corrupt snapshot, wrong attempt UUID, and final lifecycle states.

### Safety and content isolation

History may contain only candidate `simulation.py` content. Never list event logs, prompts, tests, `.scoring`, solution, study, or vendor paths; do not conflate source snapshots with lifecycle events.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] History listing/preview returns bounded metadata and candidate content only for explicit snapshot requests.
- [ ] Restore/reset are CAS-guarded, active-only, idempotently safe on retries, and preserve the lifecycle revision/event log.
- [ ] Retention, corruption, deduplication, and failure-injection tests pass.
