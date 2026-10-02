# CP0002 implementation-plan presentation

## Plan

Deliver the complete practice workflow in ordered phases:
1. Versioned attempts, immutable submission review, recoverable restart/abandon,
   and metadata history APIs.
2. Versioned catalog with independent validated packaged-original inputs.
3. Complete original exercises, then library/restart/history/review browser flows.
4. Crash/concurrency/legacy/browser/offline verification and release review.

plan/IMPLEMENTATION_PLAN.md defines each sequence/task, source anchors, failure
cases, dependency ordering, quality gates and R1–R11 evidence mapping.
decisions/INDEX.md links the five decision records; inputs/gaps.md is addressed
by those records and explicit content choice below.

## Key decisions

- Preserve old records using strict v1 readers; new records carry explicit v2
  state/content identity. No bulk or read-triggered migration.
- Abandon is distinct from expiry/submission. Restart journals old and replacement
  records with a stable operation ID; completed replay never reselects old work.
- New submissions preserve exact scored source/result identity. Legacy review
  labels unavailable binding honestly and never silently rescores or writes.
- Keep File Storage fetch validation intact. Original exercises run offline from
  separately validated package resources using the existing runner contract.
- History is bounded metadata listing, separate from source history and active
  selection. User explicitly opens source only in review.

## Review evidence

Two Cursor Composer 2.5 read-only source audits and one focused Sonnet 4.6
thinking design review completed. Findings and accepted/rejected suggestions are
in results/cursor-source-audits.md and results/cursor-design-review.md.
The restart completed-replay amendment is incorporated. No runtime tests or
implementation are claimed complete by this plan review.

## Open content preference / execution boundary

The user asked for multiple assessments and approved continued planning. Proposed
initial set: File Storage, In-Memory Records, Account Ledger. A non-blocking
question was sent this turn; no explicit topic/count reply is recorded yet.
Architecture scaffolding may proceed, but 004/02/01 must record the content choice
before authoring. Do not represent this judge's approval as that user choice.
No additional languages, hosted services, or destructive data deletion is planned.

## Approval question

Is this plan ready for implementation-task scaffolding, with the explicit content
selection prerequisite retained before content authoring? Review restart/source
integrity and requirement coverage; reject with concrete missing contracts rather
than treating a structural validation score as proof of implementation.
