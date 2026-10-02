---
fest_type: task
fest_id: 02_implement_autosave_conflicts_history_and_reset.md
fest_name: implement autosave conflicts history and reset
fest_parent: 03_editor_and_assessment_actions
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:29.891453-06:00
fest_updated: 2026-09-09T15:02:43.354666-06:00
fest_tracking: true
---


# Task: implement autosave conflicts history and reset

## Objective

Implement durable debounced source editing with ETag conflict recovery, candidate-only history/restore, and explicit reset.

## Requirements

- [ ] `webui/src/state.ts` must track `clean|dirty|saving|conflict|failed`, one in-flight save, current ETag, and the user's unsaved buffer.
- [ ] `webui/src/api.ts` must send `If-Match` to `/api/source`, map 409 to a preserved-buffer conflict UI, and call history/reset routes with explicit confirmation.
- [ ] Test/submit must flush pending save first; expiry/submission must stop autosave and make the editor/history/reset controls read-only.

## Implementation

Follow these steps in order:

1. On Monaco content change, debounce `saveSource()` and cancel/reuse queued saves so only one request is in flight; update ETag only from the authoritative success response.
2. On 409, keep the local model untouched, fetch/display the server version or offer copy/reload, and require an explicit user choice before replacing either version.
3. Render bounded history metadata/previews from `GET /api/source/history`, and route restore/reset through confirmation dialogs and the current ETag; reload the model only after success.
4. Add browser tests with a second HTTP client causing a stale ETag, then verify recovery, refresh persistence, history preview/restore, reset baseline, and final-state lock.

### Safety and content isolation

History and reset only use the selected attempt's candidate source. Never auto-merge, silently overwrite, expose event logs/tests/reference material, or allow writes after expiry/submission.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] Autosave survives refresh and exposes clean/saving/conflict/failed states accurately.
- [ ] Stale writes preserve the user's buffer and require explicit resolution; restore/reset are confirmed and CAS-guarded.
- [ ] Focused browser and API tests pass for save races, history content isolation, refresh recovery, expiry, and submission locks.
