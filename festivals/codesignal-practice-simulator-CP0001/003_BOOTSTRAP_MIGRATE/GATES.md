---
fest_type: phase_gate
fest_id: 003_BOOTSTRAP_MIGRATE-GATE
fest_parent: 003_BOOTSTRAP_MIGRATE
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

---

## Step 2: SEQUENCE OUTCOMES — Verify Sequence Goals Met

**Question:** Did each sequence achieve its stated goal? Do actual results match each SEQUENCE_GOAL?

**Actions:**
1. Compare each sequence's output against its SEQUENCE_GOAL.md
2. Verify all sequence-level quality gates passed
3. Confirm no sequences were skipped or left incomplete

**Checkpoint:** APPROVAL REQUIRED — Confirm all sequence goals achieved

---

## Step 3: QUALITY — Verify Build and Test Health

**Question:** Do the applicable migration, fetch/cache, and Python verification commands pass with no regressions?

**Actions:**
1. From `/workspace/campaign/projects/codesignal-practice-simulator`, run:

   ```sh
   python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope tracked
   python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope fixture-cache
   python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary
   python -m unittest discover -s tests -v
   python solution/test_spec.py
   python solution/test_stages.py
   python3 study/check.py 4 solution/simulation.py
   git diff --check
   git status --short
   ```

2. Before a listed artifact is created, run the earlier applicable command and record the justified deferral.
3. Confirm every declared cache hash (including `vendor-readme.md`) remains
   unchanged; the staged-and-HEAD scanner passes; no vendor byte is tracked;
   transferred user-authored content was pushed to `main` before gitlink
   creation; and only expected campaign integration files change.

**Checkpoint:** APPROVAL REQUIRED — Confirm build and tests are green

---

## Step 4: COMPLETENESS — Verify Nothing Left Behind

**Question:** Are all tasks done, all gates passed, and all review feedback addressed?

**Actions:**
1. Confirm every task is marked complete
2. Verify code review findings were incorporated or explicitly deferred with justification
3. Check that iterate gates resolved all flagged issues

**Checkpoint:** APPROVAL REQUIRED — Confirm completeness

---

## Gate State Tracking

| Step | Status | Notes |
|------|--------|-------|
| 1. PHASE GOAL | [ ] pending | Goal achievement verified |
| 2. SEQUENCE OUTCOMES | [ ] pending | All sequence goals met |
| 3. QUALITY | [ ] pending | Build and tests pass |
| 4. COMPLETENESS | [ ] pending | All tasks and gates done |
