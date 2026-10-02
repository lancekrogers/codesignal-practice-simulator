---
fest_type: gate
fest_id: 06_fest_commit.md
fest_name: Fest Commit Changes
fest_parent: 01_versioned_catalog
fest_order: 6
fest_status: completed
fest_autonomy: high
fest_gate_id: fest-commit
fest_gate_type: commit
fest_managed: true
fest_created: 2026-09-11T14:35:07.333668-06:00
fest_updated: 2026-09-12T20:20:31.076817-06:00
fest_tracking: true
fest_version: "1.0"
---


# Gate: Commit Sequence Changes

Commit all changes from this sequence using the `fest commit` command.

CP0002 must use its dedicated implementation worktree, not the audit checkout.
Inspect `fest commit --help`, project/root status, and staged scope first. The
wrapper can stage linked project edits and a campaign pointer: never capture
unrelated user changes or silently synchronize a gitlink. Use `--no-root` for
project-only delivery when root publication is not intended; preserve festival
progress locally until a separately scoped root commit is arranged. Do not add
AI coauthor trailers. Never mark a commit gate complete without an actual commit.

## Pre-Commit Checklist

- [ ] All tests pass
- [ ] Linting is clean
- [ ] No debug code or temporary files
- [ ] No secrets or credentials in staged changes

## Commit Command

You **MUST** use `fest commit` — not `git commit`. The `fest commit` command tags
commits with task reference IDs for tracking and metrics.

```bash
fest commit -m "<type>: <summary>"
```

**CRITICAL:** Do NOT use `git commit`, `git add && git commit`, or any other git
commit workflow. Always use `fest commit` so task references are preserved.

## Commit Message Format

```
<type>: <concise summary of changes>

<what changed — list concrete modifications>

<why it changed — purpose and motivation>
```

**Types:** `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

The message should describe WHAT changed and WHY. Be specific about files,
functions, or features that were added, modified, or removed.

## Ethical Requirements

The following practices are **prohibited** in commit messages:

- NO "Co-authored-by" tags for AI assistants
- NO AI tool attribution or advertisements
- NO links to AI services or products

## Definition of Done

- [ ] Pre-commit checklist verified
- [ ] Commit created with `fest commit` (not `git commit`)
- [ ] Message describes what changed and why
- [ ] No prohibited content in commit message
