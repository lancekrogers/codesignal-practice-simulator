---
fest_type: workflow
fest_id: 002_PLAN-WF
fest_parent: 002_PLAN
---

# Planning Phase Workflow

This document guides the agent through the planning phase. Follow these steps in order, completing each checkpoint before proceeding.

---

## Step 1: REVIEW — Understand the Inputs

**Goal:** Build comprehensive understanding of what needs to be built.

**Actions:**
1. Read all output specs from ingest phase (if exists)
2. Read research summary (if exists)
3. Identify key requirements, constraints, recommendations

**Output:** Mental model of what needs to be planned

**Checkpoint:** None — proceed to Step 2

---

## Step 2: GAP ANALYSIS — Identify What's Missing

**Goal:** Find unclear requirements or needed decisions.

**Actions:**
1. Note anything unclear or ambiguous
2. Identify decisions that need to be made
3. List questions you'd need answered
4. Create `inputs/gaps.md` if significant gaps exist

**Output:** List of gaps and questions

**Checkpoint:** If critical gaps exist, present to user for clarification

---

## Step 3: DECOMPOSE — Break Down Goals into Festival Structure

**Goal:** Transform requirements into the festival hierarchy (core methodology).

**Actions:**
1. Identify the **Festival Goal** — what the entire festival accomplishes
2. Break into **Phase Goals** — major stages of work:
   - What planning phases are needed?
   - What implementation phases are needed?
   - What review phases are needed?
3. For each phase, identify **Sequence Goals** — groups of related tasks
4. For each sequence, identify **Task Specifications** — atomic units of work
5. Document the hierarchy in `plan/STRUCTURE.md`

**Output:** Documented festival structure showing:
- Phase breakdown with goals
- Sequence breakdown within phases
- Task list within sequences
- Dependencies between components

**Checkpoint:** None — proceed to Step 4

---

## Step 4: DESIGN — Make Architecture Decisions

**Goal:** Make and document key design decisions.

**Actions:**
1. For each significant decision, document options and tradeoffs
2. Create `decisions/D###_title.md` for each decision
3. Update `decisions/INDEX.md`

**Output:** Documented architecture decisions

**Checkpoint:** None — proceed to Step 5

---

## Step 5: STRUCTURE — Create Implementation Plan Document

**Goal:** Define phases, sequences, and tasks in detail.

**Actions:**
1. Create `plan/IMPLEMENTATION_PLAN.md` with:
   - Overview of what will be implemented
   - Phases with their goals
   - Sequences within each phase
   - Tasks within each sequence
   - Dependencies and ordering

**Output:** Complete implementation plan document

**Checkpoint:** None — proceed to Step 6

---

## Step 6: PRESENT — Get User Approval

**Goal:** Verify plan is ready for implementation.

**Actions:**
1. Summarize the plan (phases, sequences, key decisions)
2. Note areas of uncertainty
3. Ask: "Is this plan ready for implementation?"

**Output:** Summary presented to user

**Checkpoint:** APPROVAL REQUIRED — Wait for user response

---

## Step 7: SCAFFOLD — Maintain Festival Structure

**Goal:** Maintain the approved festival directory structure.

**Actions:**
1. Keep the seven approved phase directories in numeric order.
2. Keep the two planned implementation sequences in each of phases 003
   through 006, with their task specifications and quality gates.
3. Keep phase, sequence, and task goals aligned with
   `plan/IMPLEMENTATION_PLAN.md` and `plan/STRUCTURE.md`.
4. Retain substantive, project-specific content in all required documents.

**Output:** The approved phase, sequence, task, and gate hierarchy.

**Checkpoint:** None — proceed to Step 8

---

## Step 8: VALIDATE — Verify Structure and Apply Gates

**Goal:** Ensure festival is structurally valid and ready for execution.

**Actions:**
1. Run `fest validate` to check festival structure
2. Fix any validation errors
3. Confirm implementation-gate commands match the Python project and
   migration-verification contracts in the implementation plan.
4. Run `fest gates apply --approve` only when an approved gate change must be
   propagated to sequences.
5. Run `fest validate` again and confirm the marker audit is zero.

**Output:** Valid festival structure ready for implementation

**Checkpoint:** None — phase ends

---

## Workflow State Tracking

| Step | Status | Notes |
|------|--------|-------|
| 1. REVIEW | [ ] pending | |
| 2. GAP ANALYSIS | [ ] pending | May checkpoint if critical gaps |
| 3. DECOMPOSE | [ ] pending | Core methodology step |
| 4. DESIGN | [ ] pending | |
| 5. STRUCTURE | [ ] pending | |
| 6. PRESENT | [ ] pending | Blocks until user approval |
| 7. SCAFFOLD | [ ] pending | Maintain approved hierarchy |
| 8. VALIDATE | [ ] pending | Run fest validate |
