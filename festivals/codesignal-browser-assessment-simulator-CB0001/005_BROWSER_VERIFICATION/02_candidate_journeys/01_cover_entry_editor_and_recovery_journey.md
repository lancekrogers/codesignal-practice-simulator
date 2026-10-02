---
fest_type: task
fest_id: 01_cover_entry_editor_and_recovery_journey.md
fest_name: cover entry editor and recovery journey
fest_parent: 02_candidate_journeys
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:31.188298-06:00
fest_updated: 2026-09-10T10:47:59.501759-06:00
fest_tracking: true
---


# Task: cover entry editor and recovery journey

## Objective

Cover the active candidate journey from entry through editing, settings, navigation, autosave/conflict, history/reset, refresh, and restart recovery.

## Requirements

- [ ] Exercise full and drill entry, no-pause start, four levels/tabs, Monaco Python editing/settings, source save, and preservation across navigation.
- [ ] Cause a stale ETag with a second client and verify the conflict preserves local edits with explicit reload/copy resolution.
- [ ] Verify history preview/restore/reset, refresh recovery, process restart recovery, server-derived timer, and no unexpected network requests.

## Implementation

Follow these steps in order:

1. Compose the spec from `EntryPage`, `AssessmentPage`, and `EditorPage` helpers; assert visible roles/names and API envelopes rather than implementation classes.
2. Use fixture clock/token handles and a second HTTP client to create deterministic stale-save and restart cases; wait for `clean`/authoritative state indicators.
3. Assert Description reads only selected copied prompt, History contains candidate revisions only, Rules/Info are first-party, and navigation does not change source/deadline.
4. Run `npm run test:browser -- entry editor recovery` and review failure-only artifacts for paths/content leaks.

### Safety and content isolation

Use synthetic prompt/source sentinels and assert solution/study/vendor/reference/test bytes, tokens, and raw paths never reach DOM, API responses, screenshots, or traces.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] Entry, full/drill start, editor/settings, navigation/tabs, autosave/conflict, history/reset, refresh, and restart cases pass.
- [ ] The same durable source/deadline is recovered after refresh/restart and no client shortcut changes lifecycle.
- [ ] No forbidden content or unexpected network request appears in the journey.

## Task 01 implementation evidence — 2026-09-10

### Reviewed reuse mapping

| Task 01 behavior | Evidence and disposition |
|---|---|
| Full/drill entry, four levels/tabs, and source-preserving navigation | Reuse `editor.spec.mjs` and `navigation.spec.mjs`; `candidate_journey.spec.mjs` adds the missing visible durations and no-pause confirmation. |
| Monaco Python editing and settings | Reuse `editor.spec.mjs` and `editor_settings.spec.mjs`; the task spec adds polled syntax colors, automatic bracket completion, and four-space Python indentation verified in saved source. |
| Autosave, stale ETag, explicit reload/copy, history preview/restore/reset | Reuse `source_save.spec.mjs`; the task spec adds independent timestamp and SHA-256 chain checks against the exact synthetic buffers. |
| Refresh/restart continuity and server timer | Reuse `shell_contract.spec.mjs` and `browser_continuity.spec.mjs`; the task spec verifies the exact attempt DOM identity, deadline, and saved marker after refresh and a real fixture-server restart. |
| First-party Rules/Info and candidate-only History | Reuse `navigation.spec.mjs` and `source_save.spec.mjs`; the task spec asserts every bootstrap rule term before start. |
| Offline and forbidden-content boundaries | Reuse the existing same-origin/editor checks. Every added journey installs and asserts the shared offline request policy. No duplicate boundary mechanism was added. |

### Verification

- `npm run test:browser -- tests/candidate_journey.spec.mjs` — 5 passed.
- `npm run test:browser -- tests/candidate_journey.spec.mjs tests/editor.spec.mjs tests/source_save.spec.mjs` — 26 passed.
- `npm run check` — web UI metadata, lockfile, and license checks passed.
- `git diff --check` — exit 0.
- Reviewed coordinator checkpoint: `ASSET_BUILDER=/private/tmp/cb0001-release.HTxOTs/builder/bin/python just verify` — 275 discovered tests plus 4 explicit end-to-end tests passed, no skips; legacy checks passed.

All browser commands used the configured privacy-safe reporters without overrides.
Task/workflow status was intentionally not mutated.
