---
fest_type: task
fest_id: 04_verify_api_security_and_isolation.md
fest_name: verify api security and isolation
fest_parent: 03_local_web_api
fest_order: 4
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:28.770852-06:00
fest_updated: 2026-09-09T05:46:11.975722-06:00
fest_tracking: true
---


# Task: verify API security and isolation

## Objective

Challenge the complete HTTP boundary with malformed, hostile, concurrent, and content-isolation inputs before browser integration.

## Requirements

- [ ] Enumerate invalid tokens, Origins, methods, paths, encoded traversal, UUIDs, ETags, content types, JSON, and oversized bodies.
- [ ] Assert security headers: restrictive CSP, frame denial, no-sniff, referrer policy, no permissions, no-store API/state, and immutable fingerprinted assets where applicable.
- [ ] Prove no route or static asset exposes arbitrary files, commands, solution/study/vendor/reference bytes, raw scorer internals, or candidate data from another attempt.

## Implementation

Follow these steps in order:

1. Extend `tests/test_web_server.py` with a table of HTTP requests against a temporary real server; inspect status, envelope code, headers, and bounded body for each rejection.
2. Create synthetic forbidden files outside the registered candidate/prompt set and attempt encoded path variants, directory names, symlinks, and alternate methods; assert 404/405 without leakage.
3. Use two attempts and two tokens to prove capability is per launch while selected-attempt UUID and source/history data remain scoped; exercise stale save and concurrent submit.
4. Run `python3 -m unittest tests.test_web_server tests.test_candidate_documents tests.test_scoring tests.test_rendering -v` and save only aggregate evidence.

### Safety and content isolation

Do not use real FETCH_ONLY fixture bytes in response assertions; use unique synthetic sentinels and assert they never appear. Do not log capability tokens or candidate source.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] All D004 route, method, token, Origin, body, header, and path cases have explicit assertions.
- [ ] Cross-attempt, scorer, and static-content isolation tests pass without raw internal errors.
- [ ] The complete phase-003-focused suite is green and the API is ready for UI consumption.
