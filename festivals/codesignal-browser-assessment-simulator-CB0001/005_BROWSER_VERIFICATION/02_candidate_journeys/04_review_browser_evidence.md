---
fest_type: task
fest_id: 04_review_browser_evidence.md
fest_name: review browser evidence
fest_parent: 02_candidate_journeys
fest_order: 4
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:31.761455-06:00
fest_updated: 2026-09-10T11:10:46.615587-06:00
fest_tracking: true
---


# Task: review browser evidence

## Objective

Review the real-browser artifacts and map every covered requirement to a reproducible test and result without overstating what the local simulator proves.

## Requirements

- [ ] Create an evidence index under the existing verification-results convention that maps B01-B20 and exclusions B21-B25 to commands, specs, and observed outcomes.
- [ ] Inspect failed traces/screenshots/logs only as needed, remove successful-run artifacts, and redact capability/source/prompt content.
- [ ] Identify uncovered or flaky criteria as pending findings for remediation; do not mark implementation or phase status complete.

## Implementation

Follow these steps in order:

1. Read the Playwright report, test names, and focused Python outputs; map each requirement to a concrete visible/API/package assertion and note the synthetic fixture/clock used.
2. For each failure, classify product defect, harness defect, environment limitation, or documentation mismatch and link it to the exact planned source/test path.
3. Run the smallest reproducer, then the journey spec again; preserve only failure evidence required for review and scrub tokens/attempt data.
4. Run the phase-005 journey command and a no-forbidden-content scan over retained evidence.

### Safety and content isolation

Evidence must not retain candidate source, FETCH_ONLY bytes, copied tests, solution/study/vendor content, secrets, node_modules, or full capability URLs.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] An evidence index covers each in-scope requirement and names the exact test/command.
- [ ] All failures have a disposition and no material gap is silently labeled passed.
- [ ] Retained artifacts are minimal, redacted, and clean-clone safe.
