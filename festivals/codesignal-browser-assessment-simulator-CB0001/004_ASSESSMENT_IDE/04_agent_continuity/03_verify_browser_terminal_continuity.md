---
fest_type: task
fest_id: 03_verify_browser_terminal_continuity.md
fest_name: verify browser terminal continuity
fest_parent: 04_agent_continuity
fest_order: 3
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:30.634019-06:00
fest_updated: 2026-09-09T20:28:55.671168-06:00
fest_tracking: true
---


# Task: verify browser terminal continuity

## Objective

Prove that browser actions and terminal-safe context observe one durable attempt while coaching remains outside candidate source and scoring.

## Requirements

- [x] Run a real process with browser server and CLI against one temporary workspace; verify start, status/time, test, and submit are visible in derived status/context.
- [x] Verify `COACHING.md` remains candidate-owned text and is not imported into source, scorer input, API responses, or final results.
- [x] Verify source/history access requires explicit test permission in the documented workflow and no generated surface contains protected content.

## Implementation

Follow these steps in order:

1. Use the phase-005 fixture to start the server and browser, perform one active flow, and invoke `codesignal-sim context --format json --attempt <id>` after each lifecycle action.
2. Write a synthetic coaching note containing a unique sentinel; assert it is absent from `simulation.py`, score output, prompts, API state, and generated `STATUS.md` unless explicitly documented as candidate-owned file text.
3. Check agent guidance files and attempt template after creation, then test expiry/submission read-only behavior from both surfaces.
4. Run `python3 -m unittest tests.test_rendering tests.test_documentation -v` and the focused browser continuity spec with network denial.

### Safety and content isolation

Use synthetic unique sentinels only; do not inspect or copy real fixture/reference/study content. Do not manually edit generated status or lifecycle files.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [x] Browser and CLI report the same attempt status/score/deadline through safe derived surfaces.
- [x] Coaching sentinel never enters candidate source, scoring, prompts, or final results.
- [x] Continuity tests pass and any browser/terminal discrepancy is recorded as a blocking finding.
