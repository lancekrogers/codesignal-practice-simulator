---
fest_type: task
fest_id: 02_document_safe_coaching_workflow.md
fest_name: document safe coaching workflow
fest_parent: 04_agent_continuity
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:30.5062-06:00
fest_updated: 2026-09-09T20:21:50.165459-06:00
fest_tracking: true
---


# Task: document safe coaching workflow

## Objective

Document the parallel browser/terminal practice workflow and explicit permission boundary for agent coaching.

## Requirements

- [x] Update project `AGENTS.md`, attempt template text in `workspace.py`, `COACHING.md` guidance, `docs/agent-safety.md`, and README sections as planned by phase 004.
- [x] Tell agents to read derived context/`STATUS.md` first, use candidate-owned `COACHING.md` for notes, ask before reading source/history, and never use reference/study/vendor material during timed work.
- [x] Explain that browser UI, direct CLI, scoring, timer, data ownership, and same-user threat limitations are separate concepts.

## Implementation

Follow these steps in order:

1. Compare current `AGENTS.md`, `workspace.py::_AGENTS`, `rendering.py`, `docs/agent-safety.md`, and README wording; preserve existing policies while adding browser-specific commands and examples.
2. Add a short sequence: launch browser, inspect safe context, ask permission before source access, write only candidate-approved coaching, and verify browser state through server/CLI surfaces.
3. Add post-attempt boundaries and explicitly prohibit importing coaching into `simulation.py`, executing coaching, hidden-test claims, or manual edits to session/events/status/locks.
4. Run `python3 -m unittest tests.test_documentation tests.test_workspace tests.test_rendering -v` and scan docs for contradictory claims.

### Safety and content isolation

Documentation is an operational policy, not a cryptographic sandbox. It must not imply same-user processes are isolated or authorize access to protected materials.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [x] Root and generated attempt guidance agree on the safe default and explicit permission rule.
- [x] Docs distinguish browser/CLI surfaces, timer/scoring authority, coaching ownership, and post-attempt learning.
- [x] Documentation tests and a manual contradiction scan pass.
