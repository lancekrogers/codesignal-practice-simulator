---
fest_type: task
fest_id: 03_verify_clean_project_and_campaign_clones.md
fest_name: verify clean project and campaign clones
fest_parent: 03_distribution_and_docs
fest_order: 3
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:32.109233-06:00
fest_updated: 2026-09-10T14:38:45.048451-06:00
fest_tracking: true
---




# Task: verify clean project and campaign clones

## Objective

Rehearse the documented release from clean private project and campaign clones while preserving unrelated campaign state and excluding generated artifacts.

## Requirements

- [ ] Clone or copy the project at the reviewed commit into a clean temporary location and repeat fixture setup, editable/wheel/browser, CLI, legacy, and provenance checks.
- [ ] Rehearse the campaign-level clone/submodule pointer workflow without mutating unrelated dirty submodules or committing attempts, caches, traces, secrets, or node_modules.
- [ ] Compare clean-clone commit/hash and package/browser evidence with the reviewed local state.

## Implementation

Follow these steps in order:

1. Use `git clone`/clean worktree mechanisms outside the festival directory, inspect `git status --short`, and follow the actual project README/verification commands.
2. Set up only ignored synthetic fixture data and run the canonical commands from the clean project clone; verify all generated attempts stay untracked/ignored.
3. From a separate temporary campaign clone, verify the project pointer and festival documents are present without touching existing unrelated campaign modifications in the working tree.
4. Run tracked-path and provenance scans, record commit hashes and command results, then remove all temporary clones and generated data.

### Safety and content isolation

Do not use destructive reset/checkout commands on the user's repositories. Do not copy campaign caches or real attempt data into clean clones; never publish secrets or FETCH_ONLY bytes.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] Clean project clone reproduces the documented canonical flow and package/browser evidence.
- [ ] Campaign clone points at the reviewed project state without unrelated submodule changes or generated artifacts.
- [ ] Tracked-path, status, hash, and cleanup checks pass.
