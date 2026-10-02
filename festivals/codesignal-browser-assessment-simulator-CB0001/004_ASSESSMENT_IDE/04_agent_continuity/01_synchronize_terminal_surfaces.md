---
fest_type: task
fest_id: 01_synchronize_terminal_surfaces.md
fest_name: synchronize terminal surfaces
fest_parent: 04_agent_continuity
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:30.383002-06:00
fest_updated: 2026-09-09T20:14:39.994339-06:00
fest_tracking: true
---


# Task: synchronize terminal surfaces

## Objective

Ensure browser lifecycle operations refresh the existing derived `STATUS.md` and safe context surfaces through the shared application boundary.

## Requirements

- [x] Route web start/status/time/test/submit through `RuntimeApplication` methods that invoke `DerivedStatusService.refresh()` with the same semantics as CLI paths.
- [x] Keep `AttemptContextService.read`, `render_json`, and `render_markdown` limited to session/score/event/legal-command fields.
- [x] Add tests proving browser actions update status without changing authoritative state beyond the intended lifecycle operation.

## Implementation

Follow these steps in order:

1. Audit `src/codesignal_practice_simulator/application.py` methods against current `cli.py` implementations and centralize any missing refresh call; do not have HTTP handlers open `STATUS.md` directly.
2. Use `tests/test_rendering.py` patterns to assert generated status contains assessment/lifecycle/score/event/legal-command data and excludes source, tests, prompts, cache, and study content.
3. Add a web test that starts, observes time, runs test, and submits through the server, then reads `STATUS.md` and `context --format json` with the existing CLI.
4. Run `python3 -m unittest tests.test_rendering tests.test_application tests.test_web_server -v` and a real-process browser/CLI rehearsal.

### Safety and content isolation

Never manually mutate generated status or structured lifecycle files. Derived refresh is best effort and must not make a failed browser action appear successful.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [x] Every browser lifecycle mutation refreshes the same safe derived surfaces as CLI operations.
- [x] Context/status tests prove no candidate/reference/test bytes or raw paths leak.
- [x] A real-process rehearsal observes the same attempt from browser and CLI without direct file edits.
