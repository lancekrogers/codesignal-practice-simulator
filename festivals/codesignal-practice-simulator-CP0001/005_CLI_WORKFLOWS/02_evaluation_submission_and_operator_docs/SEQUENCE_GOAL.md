---
fest_type: sequence
fest_id: 02_evaluation_submission_and_operator_docs
fest_name: evaluation_submission_and_operator_docs
fest_parent: 005_CLI_WORKFLOWS
fest_order: 2
fest_status: completed
fest_created: 2026-09-08T16:23:17.524193-06:00
fest_updated: 2026-09-08T22:39:14.445797-06:00
fest_tracking: true
fest_working_dir: .
---


# Sequence Goal: Evaluation, Submission, and Operator Documentation

**Sequence:** 02_evaluation_submission_and_operator_docs | **Phase:** 005_CLI_WORKFLOWS | **Status:** Complete

## Sequence Objective

Expose safe evaluation, final submission, and derived context commands, then publish accurate CLI-first operator and compatibility guidance.

## Required Deliverables

- [x] **Evaluation/finality commands**: partial-credit `test`, idempotent `submit`, and safe `context`.
- [x] **Lifecycle guarantees**: final sessions refuse mutation but retain safe read-only views.
- [x] **Operator documentation**: installation, profiles, errors, safety, and optional Just shortcuts are accurate.

## Task Alignment

| Task | Objective |
|------|-----------|
| 01_expose_test_submit_and_context_safely | Wire evaluation/finality to services without reference leakage. |
| 02_publish_operator_and_compatibility_documentation | Make the CLI—not Just—the stable public contract. |

## Dependencies and Risks

**Prerequisite:** `01_command_interface_and_live_session`.<br>
**Provides:** complete candidate/operator workflow for verification.<br>
**Risk:** final-state mutation or misleading safety claims. **Mitigation:** service-layer transitions, idempotency tests, and documentation that never claims a sandbox.

## Completion and Gates

- [x] Run every task Verify block and retain outcomes.
- [x] Pass all sequence quality gates before handing off to verification.

Evidence: commit `c206300`; 136-test full suite under both interpreters; live
evaluation/submission byte-identity flow and documentation examples passed;
independent final judges approved implementation and documentation with no
remaining findings.
