---
fest_type: gate
fest_id: 03_testing.md
fest_name: Testing and Verification
fest_parent: 01_versioned_catalog
fest_order: 3
fest_status: completed
fest_autonomy: medium
fest_gate_id: testing
fest_gate_type: testing
fest_managed: true
fest_created: 2026-09-11T14:35:07.332896-06:00
fest_updated: 2026-09-12T20:08:49.780007-06:00
fest_tracking: true
fest_version: "1.0"
---


# Gate: Testing and Verification

Verify all functionality implemented in this sequence works correctly.

## CP0002 verification contract

Read the sequence tasks and D001–D005. Run focused Python/CLI/API tests for the
changed behavior using synthetic temporary workspaces; prove persisted data and
negative paths. At integration gates run `just verify` with its documented build
prerequisites. UI sequences additionally run `just check frontend`, rebuild with
`just build assets`, check `just build assets-check`, and run relevant real
journeys through `just check browser` with the locked privacy reporters.
Distribution/release runs `just check wheel` and the full browser suite.
Record commands, results, and tested failure boundaries in results/testing.md.
Never inspect real candidate attempts or waive provenance checks to get green.
There is no arbitrary coverage threshold; demonstrate each acceptance criterion.

## Test Categories

### Unit Tests

- [ ] All unit tests pass
- [ ] New/modified code has test coverage
- [ ] Tests are meaningful (not just coverage padding)

### Integration Tests

- [ ] Integration tests pass
- [ ] Components work together correctly

### Error Handling

- [ ] Invalid inputs are rejected gracefully
- [ ] Error messages are clear and actionable
- [ ] Recovery paths work correctly

## Verification

- [ ] Build completes without warnings
- [ ] No regressions introduced
- [ ] Coverage meets project requirements
