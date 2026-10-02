---
fest_type: task
fest_id: 02_restart_ux.md
fest_name: restart_ux
fest_parent: 01_library_and_restart
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-11T14:32:19.009153-06:00
fest_updated: 2026-09-12T21:53:45.658151-06:00
fest_tracking: true
---


# Task: restart_ux

## Objective

Add distinct End attempt and Restart controls with confirmations through existing attempt runtime operation locks, preserving Reset source meaning and ensuring saved old code is never lost while unsaved buffer requires save-or-discard.

## Requirements

- [ ] Read and apply **D001_attempt_lifecycle.md** (restart vs reset, save/race rules) and **D004_history_api_and_ux.md** (attempt screen controls, confirmations).
- [ ] Add End attempt (abandon) and Restart UI with explicit copy: saved old work kept, new timer only in replacement attempt, unsaved text must be saved or discarded.
- [ ] Retain Reset source control with distinct labeling from restart/abandon.
- [ ] Route actions through operation locks/APIs from 003/02; include operation UUID and expected revision in restart requests.
- [ ] Surface busy/conflict/stale/recovery-pending states with actionable retry/dismiss paths.
- [ ] Synthetic browser tests verify old bytes/status plus new ID/deadline, duplicate clicks, server restart during operation; document CLI alternatives.

## Implementation

1. **Attempt toolbar** — Add buttons wired to POST abandon/restart endpoints; disable during in-flight operations.
2. **Confirm dialogs** — Restart dialog explains preservation rules; End attempt confirms abandonment without scoring.
3. **Unsaved buffer gate** — Block restart until autosave completes or user explicitly discards unsaved editor text (D001 UI wait rule).
4. **Error mapping** — Map 409/conflict, recovery-pending, and stale revision responses to visible UI states with retry.
5. **CLI discoverability** — Link or document equivalent CLI commands in UI help or docs snippet.
6. **Browser tests** — Playwright/synthetic tests: save source, restart, assert old attempt directory bytes unchanged and new attempt active with fresh deadline; duplicate click idempotency; kill server mid-operation then recover.

### Affected files

- `webui/src/app.ts` and attempt view components
- `webui/tests/` Playwright specs (locked privacy reporters)
- `docs/cli-contract.md` (CLI parity note)

### Negative cases to prove

- Restart with unsaved editor text blocked until explicit discard.
- Submit in flight blocks conflicting restart with stale error.
- Duplicate restart clicks do not create two replacements.
- Reset source does not change attempt ID or abandon status.

### Commands and evidence

```bash
just check browser  # inspect project Justfile
just check browser --grep restart
```

## Done When

- [ ] All requirements met
- [ ] End/Restart/Reset are distinct, confirmed, and respect operation locks
- [ ] Synthetic browser tests prove old bytes preserved and idempotent restart behavior
