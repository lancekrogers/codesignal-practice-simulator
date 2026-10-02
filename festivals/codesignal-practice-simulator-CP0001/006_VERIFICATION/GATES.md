---
fest_type: phase_gate
fest_id: 006_VERIFICATION-GATE
fest_parent: 006_VERIFICATION
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

**Evidence:** `PHASE_GOAL.md` and `results/phase-quality-evidence.md` enumerate
the completed deliverables and passing functional proof.

---

## Step 2: SEQUENCE OUTCOMES — Verify Sequence Goals Met

**Question:** Did each sequence achieve its stated goal? Do actual results match each SEQUENCE_GOAL?

**Actions:**
1. Compare each sequence's output against its SEQUENCE_GOAL.md
2. Verify all sequence-level quality gates passed
3. Confirm no sequences were skipped or left incomplete

**Checkpoint:** APPROVAL REQUIRED — Confirm all sequence goals achieved

**Evidence:** Both sequence frontmatter records and all 11 task/gate records
are complete; their result files record the matching outcomes.

---

## Step 3: QUALITY — Verify Build and Test Health

**Question:** Do the planned Python unit, end-to-end, migration, and legacy verification commands pass with no regressions?

**Actions:**
1. From `/workspace/campaign/projects/codesignal-practice-simulator`, run:

   ```sh
   python -m unittest discover -s tests -v
   python -m unittest tests.test_end_to_end -v
   python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope tracked
   python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope fixture-cache
   python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary
   python scripts/run_legacy_checks.py
   git diff --check
   git status --short
   ```

2. Rehearse the documented clean-clone commands and record evidence for both project and campaign clones.
3. Confirm every declared cache record, including `vendor-readme.md`, remains
   byte-verified; the staged-and-HEAD scanner passes; no vendor byte is
   tracked; and no unrelated campaign change is present.

**Checkpoint:** APPROVAL REQUIRED — Confirm build and tests are green

**Evidence:** 158 tests, explicit E2E, all three manifest scopes, the canonical
legacy runner, direct solution/study checks, clean-clone rehearsals, and diff
checks pass. Exact hashes and profiles are in the result files.

---

## Step 4: COMPLETENESS — Verify Nothing Left Behind

**Question:** Are all tasks done, all gates passed, and all review feedback addressed?

**Actions:**
1. Confirm every task is marked complete
2. Verify code review findings were incorporated or explicitly deferred with justification
3. Check that iterate gates resolved all flagged issues

**Checkpoint:** APPROVAL REQUIRED — Confirm completeness

**Evidence:** Sequence 01 is 5/5 and sequence 02 is 6/6. Concrete deliverables
are the three sequence result files plus `results/phase-quality-evidence.md`.
The sequence-02 iterate gate records both judge findings as resolved with
regression coverage; no review finding is deferred.

---

## Gate State Tracking

| Step | Status | Notes |
|------|--------|-------|
| 1. PHASE GOAL | [x] evidence verified | Goal achievement verified |
| 2. SEQUENCE OUTCOMES | [x] evidence verified | Both sequences and all quality gates complete |
| 3. QUALITY | [x] evidence verified | 158 tests and every planned verifier pass |
| 4. COMPLETENESS | [x] evidence verified | 11/11 tasks/gates done; all findings resolved |
