---
fest_type: phase_gate
fest_id: 005_CLI_WORKFLOWS-GATE
fest_parent: 005_CLI_WORKFLOWS
---

# Implementation Phase Gate

This gate verifies the implementation phase achieved its goal and produced working deliverables.

---

## Step 1: PHASE GOAL — Verify Goal Achievement

**Question:** Does the implementation satisfy the PHASE_GOAL.md objectives? Were all required deliverables produced?

**Actions:**
1. Re-read PHASE_GOAL.md and compare stated objectives against actual results
2. Verify each required deliverable exists and is functional
3. Confirm the implementation solves the problem the phase was created for

**Checkpoint:** APPROVAL REQUIRED — Confirm phase goal is met

**Evidence:** Complete CLI surface is pushed in `a852b73` and `c206300`;
`PHASE_GOAL.md` records the functional and verification evidence.

---

## Step 2: SEQUENCE OUTCOMES — Verify Sequence Goals Met

**Question:** Did each sequence achieve its stated goal? Do actual results match each SEQUENCE_GOAL?

**Actions:**
1. Compare each sequence's output against its SEQUENCE_GOAL.md
2. Verify all sequence-level quality gates passed
3. Confirm no sequences were skipped or left incomplete

**Checkpoint:** APPROVAL REQUIRED — Confirm all sequence goals achieved

**Evidence:** Both sequence frontmatter records are completed, their goal
checklists and quality gates are complete, and each has an independent Cursor
approval with no unresolved findings.

---

## Step 3: QUALITY — Verify Build and Test Health

**Question:** Do the planned Python CLI, unit, and fetch/cache verification commands pass with no regressions?

**Actions:**
1. From `/workspace/campaign/projects/codesignal-practice-simulator`, run:

   ```sh
   python -m unittest tests.test_cli -v
   python -m unittest discover -s tests -v
   python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope tracked
   python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope fixture-cache
   python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary
   python solution/test_spec.py
   git diff --check
   git status --short
   ```

2. Confirm console and module entry points, human/JSON envelopes, exit codes, and selected-session behavior are covered.
3. Confirm all declared cache records are present, the staged-and-HEAD
   boundary scanner passes, and the diff contains no tracked vendor bytes or
   unrelated campaign change.

**Checkpoint:** APPROVAL REQUIRED — Confirm build and tests are green

**Evidence:** 136 unit/end-to-end tests pass under both interpreters;
console/module parity, `just verify`, all three manifest scopes, both hooks,
specification/staged/study checks, and whitespace checks pass.

---

## Step 4: COMPLETENESS — Verify Nothing Left Behind

**Question:** Are all tasks done, all gates passed, and all review feedback addressed?

**Actions:**
1. Confirm every task is marked complete
2. Verify code review findings were incorporated or explicitly deferred with justification
3. Check that iterate gates resolved all flagged issues

**Checkpoint:** APPROVAL REQUIRED — Confirm completeness

**Evidence:** Every phase-005 task and sequence gate is complete; all review
findings are recorded as resolved. The aggregate legacy verification script is
correctly scheduled for phase 006 rather than left incomplete here.

---

## Gate State Tracking

| Step | Status | Notes |
|------|--------|-------|
| 1. PHASE GOAL | [x] evidence verified | Deliverables functional; see `results/phase-quality-evidence.md` |
| 2. SEQUENCE OUTCOMES | [x] evidence verified | Both completed sequence goals and gates are documented |
| 3. QUALITY | [x] evidence verified | 136 tests under both interpreters; all boundary checks pass |
| 4. COMPLETENESS | [x] evidence verified | All phase tasks/gates done and findings resolved |
