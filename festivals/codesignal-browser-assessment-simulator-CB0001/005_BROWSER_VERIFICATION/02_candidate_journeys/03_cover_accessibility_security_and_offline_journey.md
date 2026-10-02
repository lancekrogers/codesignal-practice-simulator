---
fest_type: task
fest_id: 03_cover_accessibility_security_and_offline_journey.md
fest_name: cover accessibility security and offline journey
fest_parent: 02_candidate_journeys
fest_order: 3
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:31.519305-06:00
fest_updated: 2026-09-10T11:02:42.349949-06:00
fest_tracking: true
---


# Task: cover accessibility security and offline journey

## Objective

Verify keyboard/responsive usability and the complete browser/API security, content-isolation, and runtime-offline contract.

## Requirements

- [ ] Cover keyboard-only focus order, visible focus, live regions, modal focus, reduced motion, narrow-laptop layout, and accessible names.
- [ ] Cover invalid token/Origin/method/path/body/UUID/ETag, security headers/CSP/cache policy, symlink/body/content boundaries, and forbidden routes.
- [ ] Deny external network and prove bootstrap, Monaco, workers, editing, and final state load from package/local resources only.

## Implementation

Follow these steps in order:

1. Use Playwright keyboard APIs and narrow viewport contexts with the shared page helpers; assert focus target after dialogs, save conflicts, and results.
2. Send direct HTTP probes through the fixture server for each D004 rejection and inspect status/envelope/header/body for no path/trace leakage.
3. Block all non-loopback requests, exercise Monaco worker/editor load, and scan static/API/DOM outputs for synthetic forbidden sentinels and external URLs.
4. Run `npm run test:browser -- accessibility security offline` and the focused `tests.test_web_server` suite.

### Safety and content isolation

Use synthetic sentinels only and redact tokens/source from traces. A same-user process is outside the threat model; tests must not claim cryptographic sandboxing.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] Keyboard, focus, live-region, responsive, and reduced-motion assertions pass.
- [ ] All token/origin/method/path/body/header/content-isolation probes pass with stable safe errors.
- [ ] The complete browser flow runs with zero unexpected network requests.
