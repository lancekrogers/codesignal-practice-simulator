---
fest_type: task
fest_id: 02_cover_test_expiry_submit_and_restart_journey.md
fest_name: cover test expiry submit and restart journey
fest_parent: 02_candidate_journeys
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:31.314856-06:00
fest_updated: 2026-09-10T10:55:06.444188-06:00
fest_tracking: true
---


# Task: cover test expiry submit and restart journey

## Objective

Cover practice test outcomes, save/evaluation races, server expiry, submit confirmation/idempotency, final results, restart, and terminal sync.

## Requirements

- [ ] Exercise passing and intentionally failing four-group practice checks, bounded output, and candidate-failure semantics.
- [ ] Advance the injected clock to expiry, assert illegal mutations are disabled, then verify allowed timeout submission and immutable final result.
- [ ] Confirm cancel/confirm submit, repeated submit, refresh/restart, and safe `STATUS.md`/`context --format json` synchronization.

## Implementation

Follow these steps in order:

1. Use synthetic candidate/test modules from the fixture builder to produce pass/fail outcomes; assert failure is represented as score data rather than an HTTP transport error.
2. Start a save/test race with a controlled response, advance fake time to deadline, and assert the server snapshot—not the client countdown alone—decides expiry and final action legality.
3. Submit once, repeat through API/UI after reload and process restart, and compare stored score/result documents while confirming no second scoring event.
4. Run `npm run test:browser -- actions expiry submit restart` plus `python3 -m unittest tests.test_lifecycle tests.test_rendering -v`.

### Safety and content isolation

Do not expose raw test code, scorer argv, reference bytes, or official hidden-test claims. Keep output capped and artifacts redacted.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] Pass/fail test semantics, expiry locking, confirmation, timeout submission, repeat idempotency, and final immutability pass.
- [ ] Refresh/restart shows the stored state and terminal safe surfaces match browser state.
- [ ] Race and candidate-failure tests are deterministic under the injected clock.
