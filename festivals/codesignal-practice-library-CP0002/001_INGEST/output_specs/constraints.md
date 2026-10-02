# Constraints

## Existing system

Extend the Python application/lifecycle/persistence/assessment registry and
locally bundled TypeScript/Monaco UI. Maintain common CLI/browser semantics.
Preserve current File Storage provenance and isolated scoring. New original
content requires an explicit package/content boundary, not loosening fetched
fixture validation to accept arbitrary files.

## Safety and compatibility

Use implementation code and synthetic fixtures only. Do not inspect actual
candidate source/history, caches, copied tests, or protected reference content.
Do not manually mutate live session.json, events.jsonl, locks, or active.json.
No deleting old attempts or implicitly submitting them during restart.
Keep capability-scoped loopback access, bounded input/listing, symlink/path
checks, optimistic concurrency, and safe errors. History metadata must not
eagerly include source or private diagnostics.

Audit which historical fields truly exist. An independently immutable scored
source snapshot is a design question, not assumed proven by a saved source file.
Specify assessment version identity so future catalog changes do not reinterpret
past submissions. Prove compatibility/recovery on synthetic legacy sessions.

## Workflow

The owning checkout has unrelated user edits; leave them unchanged.
Before implementation, create one dedicated project worktree and relink CP0002.
Use fest next, traceable fest commits, review gates, and project Just recipes.
No automatic campaign gitlink sync or PR merge. No arbitrary new runner,
coverage quotas, hosted services, or dependency upgrades.
