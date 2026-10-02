# Decisions Index

Registry of architecture decisions made during planning.

| ID | Decision | Status | Date |
|----|----------|--------|------|
| [D001](D001_repository_and_campaign_integration.md) | Private repository, provenance, and campaign integration | accepted | 2026-09-08 |
| [D002](D002_python_package_and_cli.md) | Python package, CLI, and attempt layout | accepted | 2026-09-08 |
| [D003](D003_session_state_and_agent_boundary.md) | Per-attempt state, persistence, and lifecycle | accepted | 2026-09-08 |
| [D004](D004_agent_safe_coaching.md) | Agent-safe coaching and evaluation boundary | accepted | 2026-09-08 |

## Status Values

- `proposed` — Under consideration
- `accepted` — Approved and final
- `superseded` — Replaced by a later decision

The accepted decisions jointly define repository ownership, package and CLI
contracts, authoritative session state, and the candidate/agent safety
boundary.
