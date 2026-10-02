---
fest_type: task
fest_id: 03_verify_deterministic_harness.md
fest_name: verify deterministic harness
fest_parent: 01_browser_harness
fest_order: 3
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:31.058635-06:00
fest_updated: 2026-09-09T22:34:42.439508-06:00
fest_tracking: true
---


# Task: verify deterministic harness

## Objective

Validate that the browser fixture, clock controls, cleanup, network denial, and diagnostics are themselves deterministic before adding full journeys.

## Requirements

- [x] Run the same harness smoke repeatedly with the same synthetic fixture and assert stable route/resource behavior and state transitions.
- [x] Advance the injected clock through active, expiry, and final states without wall-clock sleeps or real fixture dependencies.
- [x] Force server/page failure and verify trace/screenshot/log cleanup and redaction behavior.

## Implementation

Follow these steps in order:

1. Add a small `browser-tests/harness.spec.ts` that loads bootstrap twice, starts a drill attempt, advances fake time, and closes/reopens the server fixture.
2. Use the fixture's authoritative polling helper to assert deadline/expiry; do not patch DOM timers or local storage to simulate lifecycle.
3. Trigger an intentional 500/console error in a controlled test and assert failure artifacts are produced in the configured temporary output then removed by cleanup.
4. Run the harness spec multiple times, `npm run check`, and the Python fixture/server focused tests.

### Safety and content isolation

Keep failure fixtures synthetic and avoid storing full response bodies, tokens, source, or prompt text in artifacts.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [x] Repeated harness runs are deterministic without wall-clock timing dependence.
- [x] Injected clock, restart, cleanup, network denial, and failure diagnostics behave as specified.
- [x] Harness and focused Python checks pass with no repository artifact leakage.
