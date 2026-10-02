---
# Gate metadata (for fest CLI discovery)
id: QUALITY_GATE_ITERATE
aliases:
  - review-iterate
  - qg-iterate
description: Standard quality gate task for addressing review findings and iterating

# Fest document metadata (becomes document frontmatter)
fest_type: gate
fest_id: <no value>
fest_name: Review Results and Iterate
fest_parent: <no value>
fest_order: <no value>
fest_gate_type: iterate
fest_autonomy: medium
fest_status: pending
fest_tracking: true
fest_created: 2026-09-08T14:45:08-06:00
---

# Gate: Review Results and Iterate

Address all findings from testing and code review. Iterate until the sequence meets quality standards.

## Findings to Address

### From Testing

- [ ] (list findings from testing gate)

### From Code Review

- [ ] (list findings from review gate)

## Iteration

For each finding:

1. Fix the issue
2. Re-run the applicable Python command from the testing gate, including
   `python -m unittest discover -s tests -v` when the full suite exists.
3. Run `python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope tracked`,
   `--scope fixture-cache`, and `--scope git-boundary` when the manifest/cache
   exists, then run `git diff --check`.

## Definition of Done

- [ ] All critical findings fixed
- [ ] Applicable implementation-plan Python verification commands pass after changes.
- [ ] The manifest remains verified, cache hashes are unchanged, and no vendor
  file is tracked; the staged-and-HEAD Git boundary passes.
- [ ] `git diff --check` passes.
- [ ] Code review findings addressed
- [ ] Ready to commit
