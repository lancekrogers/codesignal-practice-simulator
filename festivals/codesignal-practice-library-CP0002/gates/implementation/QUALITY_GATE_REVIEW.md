---
# Template metadata (for fest CLI discovery)
id: QUALITY_GATE_REVIEW
aliases:
  - code-review
  - qg-review
description: Standard quality gate task for code review

# Fest document metadata (becomes document frontmatter)
fest_type: gate
fest_id: {{ .GateID }}
fest_name: Code Review
fest_parent: {{ .SequenceID }}
fest_order: {{ .TaskNumber }}
fest_gate_type: review
fest_autonomy: low
fest_status: pending
fest_tracking: true
fest_created: {{ .created_date }}
---

# Gate: Code Review

Review all code changes in this sequence for quality, correctness, and standards compliance.

## CP0002 review focus

Use a bounded read-only Cursor reviewer as authorized by the user. Routine
reviews may use Composer; reserve higher-reasoning review for persistence/races.
Check D001 restart identity/replay and lock order, D002 scored-source integrity
and non-mutating legacy review, D003 content isolation/versioning, and D004
metadata-only history/navigation. Each blocking finding needs a reachable trigger,
execution path and user impact. Record model, scope, findings and disposition in
results/review.md; do not equate a reviewer verdict with runtime verification.

## Review Checklist

### Code Quality

- [ ] Code is readable and well-organized
- [ ] Functions are focused (single responsibility)
- [ ] Naming is clear and consistent
- [ ] No unnecessary complexity or duplication

### Standards Compliance

- [ ] Linting passes without warnings
- [ ] Formatting is consistent
- [ ] Project conventions are followed

### Error Handling & Security

- [ ] Errors are handled appropriately
- [ ] No secrets in code
- [ ] Input validation present where needed
- [ ] No obvious security issues

### Alignment

- [ ] Changes align with sequence goal
- [ ] No scope creep beyond what was requested

## Findings

Document any issues that must be addressed before commit.

**Critical Issues:** (must fix)

**Suggestions:** (should consider)
