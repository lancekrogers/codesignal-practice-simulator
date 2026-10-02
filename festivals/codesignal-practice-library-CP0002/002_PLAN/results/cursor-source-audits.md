# Cursor source audits — 2026-09-11

Two bounded read-only Cursor sub-agent calls used composer-2.5 in ask mode.
Both exited 0. No force flag, source edits, tests, or nested agents were requested.
Inputs were production source only; candidate/cache/reference material excluded.
Billing/credit consumption was not measured, so no savings figure is claimed.

## Lifecycle/persistence audit

Confirmed workspace→attempt lock order and non-reentrant locks; submission WAL
recovers state/event without rescoring; ordinary status/time paths can repair
events; source reads can also traverse recovery. Score state lacks an explicit
source digest. Expired submission currently ignores supplied source payload.

Accepted amendments: readonly review must avoid recovery/read side effects;
capture and score must bind one explicit attempt/revision across processes;
expired source payloads must not be silently discarded; long scoring must not
hold the workspace-wide lock. Verified against workspace.py:223/:239,
application.py:371/:418, lifecycle.py:315 and persistence.py:172.

Rejected suggestion: represent abandonment as expiry and clear active.json.
That misrepresents user intent, leaves old work resubmittable as expired, and
does not satisfy durable abandonment/restart identity. D001 uses explicit v2 state
with v1-compatible readers and a recoverable restart journal instead.
Rejected digest-only event proposal as the sole new review artifact: it detects
changes but does not preserve the original submitted bytes. D002 records both.

## Catalog/history audit

Confirmed registry/bootstrap hardcoding, whole-cache validation, and fixed runner
entry point. Source history is distinct from attempt history. Accepted the runner
contract finding after checking scoring.py:128/:193: original exercise checks
must provide TestSimulateCodingFramework.test_group_1..4.

Rejected a registry-union legacy cache and embedding all attempt history inside
bootstrap: originals must run without fetching File Storage and listing must be
bounded/paginated. D003 separates validated providers; D004 uses a listing route.
The auditor called the new assessment CP0002; this is the festival ID, not an
exercise ID. No such assessment ID was adopted.

These are design inputs, not proof that implementation or user outcomes work.
