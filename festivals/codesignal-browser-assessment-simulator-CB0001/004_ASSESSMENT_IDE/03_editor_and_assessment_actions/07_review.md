---
fest_type: gate
fest_id: 07_review.md
fest_name: Code Review
fest_parent: 03_editor_and_assessment_actions
fest_order: 7
fest_status: completed
fest_autonomy: low
fest_gate_id: review
fest_gate_type: review
fest_managed: true
fest_created: 2026-09-09T03:25:43.875992-06:00
fest_updated: 2026-09-09T18:16:13.582309-06:00
fest_tracking: true
fest_version: "1.0"
---


# Gate: Code Review

Review all code changes in this sequence for quality, correctness, and standards compliance.

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

Run an independent Cursor CLI review after tests pass. The reviewer must inspect
the actual diff and relevant surrounding code, must not edit files, and must
challenge correctness, maintainability, backward compatibility, security,
candidate-content isolation, and the sequence goal. Use a fresh Cursor session,
for example:

```bash
cursor-agent -p --mode ask --trust --model gpt-5.6-luna-high \
  "Review the current uncommitted sequence diff against its Festival goal. Do not edit. Report critical, major, minor, and test-gap findings with exact file anchors. Explicitly assess FETCH_ONLY isolation and whether a human can maintain the code."
```

Document the command/model, reviewed diff base, findings, and dispositions in
`results/review.md`. “No findings” is valid only with a written rationale.

**Critical Issues:** (must fix)

**Suggestions:** (should consider)
