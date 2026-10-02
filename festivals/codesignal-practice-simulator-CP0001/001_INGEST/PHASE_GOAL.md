---
fest_type: phase
fest_id: 001_INGEST
fest_name: INGEST
fest_parent: codesignal-practice-simulator-CP0001
fest_order: 1
fest_status: completed
fest_created: 2026-09-08T14:45:08.814109-06:00
fest_updated: 2026-09-08T14:51:53.315621-06:00
fest_phase_type: ingest
fest_tracking: true
---


# Phase Goal: Source and Requirements Ingest

**Phase:** 001_INGEST | **Status:** Pending | **Type:** Ingest

## Phase Objective

**Primary Goal:** Ingest and structure input materials into actionable specifications

**Context:** The approved objective, an inspection of the existing
`workflow/explore/codesignal-industry-coding-framework` project, and the
JobSearch submodule convention are structured here so later implementation
tasks preserve the assessment while adding a durable simulator lifecycle.

## Input Sources

Place all raw input materials in `input_specs/`:

- [x] Approved objective: private `lancekrogers/codesignal-practice-simulator`,
      campaign destination, migration scope, command surface, session safety,
      and end-to-end test requirements
- [x] Existing practice project: timed harness, assessment fixture, solutions,
      study material, Just recipes, notes, and requirements under
      `workflow/explore/codesignal-industry-coding-framework`
- [x] Campaign integration evidence: root `.gitmodules`, existing
      `projects/` gitlinks, and current exploration work-item metadata

## Expected Outputs

The following structured documents will be created in `output_specs/`:

| Output | Purpose |
|--------|---------|
| `purpose.md` | Festival purpose, success criteria, motivation |
| `requirements.md` | Prioritized requirements (P0/P1/P2) with traceability |
| `constraints.md` | Technical and process constraints |
| `context.md` | Prior art, related systems, key references |

## Success Criteria

This ingest phase is complete when:

- [ ] All input sources reviewed and understood
- [ ] Output specs created following standard structure
- [ ] User has approved the structured output
- [ ] No unresolved questions or ambiguities

## Workflow

This phase uses step-based workflow guidance. See `WORKFLOW.md` for the step-by-step process.

Use `fest next` to see the current step.
Use `fest workflow advance` to move to the next step.

## Notes

The source contains a generated `.venv/`, which is explicitly excluded from
migration. The vendored assessment identifies an upstream repository and
commit; implementation must verify and record its license/provenance before
creating the private destination. Full and drill session contracts are planned
now; no source migration, GitHub action, or product implementation happens in
this phase.

---

*Ingest phases transform unstructured input into structured specifications ready for planning.*
