---
fest_type: gate
fest_id: 08_fest_commit.md
fest_name: Fest Commit Changes
fest_parent: 02_candidate_documents
fest_order: 8
fest_status: completed
fest_autonomy: high
fest_gate_id: fest-commit
fest_gate_type: commit
fest_managed: true
fest_created: 2026-09-09T03:25:43.868024-06:00
fest_updated: 2026-09-09T04:58:20.070742-06:00
fest_tracking: true
fest_version: "1.0"
---


# Gate: Commit Sequence Changes

Commit all changes from this sequence using the `fest commit` command.

## Pre-Commit Checklist

- [ ] All tests pass
- [ ] Linting is clean
- [ ] No debug code or temporary files
- [ ] No secrets or credentials in staged changes
- [ ] `results/testing.md`, `results/review.md`, and `results/iteration.md` contain
  the final sequence evidence and dispositions
- [ ] No FETCH_ONLY fixture/reference/study/vendor bytes, attempt directories,
  `node_modules`, Playwright traces, browser profiles, or build caches are staged
- [ ] Festival status identifies this sequence and the linked project worktree

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
- [ ] `git show --stat --oneline HEAD` matches the reviewed sequence scope
- [ ] `git status --short` is clean except for explicitly documented unrelated
  campaign state
