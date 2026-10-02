---
fest_type: gate
fest_id: 06_iterate.md
fest_name: Review Results and Iterate
fest_parent: 01_browser_harness
fest_order: 6
fest_status: completed
fest_autonomy: medium
fest_gate_id: iterate
fest_gate_type: iterate
fest_managed: true
fest_created: 2026-09-09T03:25:43.880924-06:00
fest_updated: 2026-09-10T09:32:26.980132-06:00
fest_tracking: true
fest_version: "1.0"
---


# Gate: Review Results and Iterate

Address all findings from testing and code review. Iterate until the sequence meets quality standards.

## Findings to Address

### From Testing

- [ ] Copy every failed assertion, warning requiring action, or missing evidence
  from `results/testing.md`; write `None` with rationale when empty

### From Code Review

- [ ] Copy every critical, major, minor, and test-gap item from
  `results/review.md`; write `None` with rationale when empty

## Iteration

For each finding:

1. Fix the issue
2. Re-run affected tests
3. Verify linting passes
4. Record the exact fix and rerun evidence in `results/iteration.md`
5. Re-run the independent Cursor reviewer when a fix materially changes design,
   security, persistence, API contracts, or browser state behavior

## Definition of Done

- [ ] All critical findings fixed
- [ ] All tests pass after changes
- [ ] Linting passes
- [ ] Code review findings addressed
- [ ] No P0/P1 requirement was deferred and no exclusion was relaxed
- [ ] `git diff --check` passes and `git status --short` contains no attempt data,
  dependency cache, secret, FETCH_ONLY content, or unexpected generated artifact
- [ ] Ready to commit
