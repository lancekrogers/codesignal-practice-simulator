# Festival Rules: CodeSignal Practice Library

## Authority and data

- Follow project AGENTS.md. This is simulator development, not permission to read
  or edit real candidate source/history, protected cache, or reference material.
- Audit implementation code; verify using first-party synthetic workspaces.
- Preserve existing attempts, fixture provenance, and unrelated user changes.
- Restart must not silently delete, submit, or reset the old attempt's timer.
- Distinguish source reset, leaving a view, abandonment, and fresh restart.
- Additional original content must not reproduce proprietary assessment questions.

## Architecture

Extend the existing application, lifecycle, persistence, registry, and bundled UI.
Keep server-side lifecycle/scoring authoritative and CLI/browser rules consistent.
Bind reviewed results to the submitted source and assessment version.
History listings expose metadata only; load source on explicit user review.
Bound reads/listing; preserve capability checks, path validation, and symlink
protection. Include needed original content in offline distribution.
Avoid new runners, arbitrary coverage quotas, or unrelated rewrites.

## Execution and evidence

Drive fest next; record real workflow/task completion. Do not mark approval gates
complete without approval. Create implementation sequences only after design;
each task needs verified file:line anchors, behavior/error cases, and evidence.
Before changing code, create one dedicated project worktree and relink the
festival. Execution now uses the linked cp0002-practice-library worktree;
the original checkout remains outside implementation scope.
Use fest commit for execution; root pointer updates remain explicit.
Delegate only when explicitly authorized.

Use project Just recipes, canonical tests, isolated browser privacy reporters, and
offline package checks. Exercise duplicate restart/submit, concurrent tabs,
interrupted writes, corrupt/missing entries, save conflicts, legacy sessions, and
stale assessment versions. Prove persisted outcomes, not just UI success.
Structural validation alone does not prove product quality.
