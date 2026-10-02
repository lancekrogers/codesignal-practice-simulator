# CP0002 intake presentation

## User outcome

Choose among multiple Python assessments, practice repeatedly, explicitly
abandon/restart without losing old work, browse previous attempts, and review
submitted code/results/timing in a read-only view.

## Produced specifications

- purpose.md: repeatable practice outcome and completion boundary.
- requirements.md: R1–R11, including content, history, restart, compatibility,
  save/crash/concurrency failure cases, and full-flow acceptance.
- constraints.md: existing architecture, privacy, non-destructive persistence,
  offline packaging, and isolated implementation workflow.
- context.md: source-audited findings with verified file:line anchors.

## Important findings

Submission scores and timestamps already persist. Missing history UI is not
evidence of lost submissions. The default registry contains only File Storage,
and browser start refuses an active selected attempt. Existing source history
is not a submissions list. No real candidate data was read during this audit.

## Interpretations and open decisions

Restart means preserve/abandon the old attempt and create a new ID/deadline,
not reset an existing clock or silently submit. Proposed initial content is
File Storage plus two original four-level Python exercises: in-memory records
and account ledger. Exact tracks/count remain proposed and require acceptance
before content implementation. Architecture planning must resolve version
pinning, result/source binding, recovery transactions, and safe legacy review.

## Review request

Do these specs accurately capture the requested product scope and provide a
sufficient basis for architecture planning? Approval of intake does not claim
implementation completion or settle the explicitly open content decisions.

The user approved starting this full-scope festival on 2026-09-11. The summary
and proposed catalog were presented in this session; no separate user response
to this detailed intake has been received. Use the configured approval route
honestly; do not label a local-judge result as explicit user content approval.
