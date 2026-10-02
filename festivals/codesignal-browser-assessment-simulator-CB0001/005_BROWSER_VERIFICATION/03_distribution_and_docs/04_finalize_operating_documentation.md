---
fest_type: task
fest_id: 04_finalize_operating_documentation.md
fest_name: finalize operating documentation
fest_parent: 03_distribution_and_docs
fest_order: 4
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:32.236123-06:00
fest_updated: 2026-09-10T14:48:29.090128-06:00
fest_tracking: true
---


# Task: finalize operating documentation

## Objective

Update project documentation so another user or agent can launch, operate, troubleshoot, verify, and safely clean up the browser simulator from the proven release artifacts.

## Requirements

- [ ] Update `README.md`, `docs/cli-contract.md`, `docs/agent-safety.md`, and relevant `AGENTS.md`/Just recipes with browser launch, CLI fallback, canonical verification, troubleshooting, timer semantics, data ownership, coaching, and cleanup.
- [ ] Document editable versus wheel installs, fixture FETCH_ONLY setup, package/offline assumptions, same-user threat boundary, source/history ownership, and no official hidden-test claim.
- [ ] Every command in docs must match a command proven in the matrix/clone verification; remove aspirational commands and stale layout claims.

## Implementation

Follow these steps in order:

1. Read current README, CLI contract, agent safety, drill profiles, migration/provenance docs, and `justfile` before editing; preserve the existing CLI contract and legacy workflow.
2. Add a concise browser section with `codesignal-sim web --workspace-root ... --no-open`, URL/capability handling, entry/start/timer/final semantics, and browser-versus-CLI responsibilities.
3. Add operator troubleshooting for missing fixture, port/open failure, expired/submitted read-only state, stale source conflict, Monaco asset failure, wheel/offline setup, and cleanup.
4. Run `python3 -m unittest tests.test_documentation -v`, the canonical commands cited by docs, and a link/command consistency scan against the recorded evidence.

### Safety and content isolation

Documentation must not reveal secrets, real attempt paths, copied test/reference content, or imply agents may bypass source permission or use hidden official cases.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] A clean user can follow the documented launch/browser/CLI/coaching/cleanup flow from the wheel or editable install.
- [ ] Documentation tests and command consistency checks pass against actual verification evidence.
- [ ] Docs state data ownership, timer authority, offline behavior, and same-user limitations accurately.
