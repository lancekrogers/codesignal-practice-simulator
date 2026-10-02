---
fest_type: task
fest_id: 03_implement_mutation_api.md
fest_name: implement mutation api
fest_parent: 03_local_web_api
fest_order: 3
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:28.665248-06:00
fest_updated: 2026-09-09T05:46:11.720441-06:00
fest_tracking: true
---


# Task: implement mutation API

## Objective

Connect browser start, CAS save, reset/restore, test, and submit actions to the shared application and candidate-document services with coherent authoritative responses.

## Requirements

- [ ] Implement `POST /api/attempts`, `PUT /api/source`, `POST /api/source/reset`, `/api/source/restore`, `/api/test`, and `/api/submit` with strict JSON schemas and body-size limits.
- [ ] Require `X-Simulator-Token` for every API request and exact loopback `Origin` for every mutation; require `If-Match` for source replacement/reset/restore.
- [ ] Flush source through CAS before test/submit, serialize one authoritative session/time/source/score response, preserve candidate-failure as a successful HTTP exchange, and preserve submit idempotency.

## Implementation

Follow these steps in order:

1. Add `src/codesignal_practice_simulator/web/security.py` request checks for token, Origin, content type, body cap, JSON decoding, canonical UUIDs, and method allowlists before route dispatch.
2. Map start to `RuntimeApplication.start`, source mutations to `CandidateDocumentService`, test to `EvaluationService.test` while preserving candidate failure data, and submit to `EvaluationService.submit`; call derived-status refresh after browser actions.
3. Build one response serializer that returns session/time/source ETag/score/status fields needed by `webui/src/state.ts` without raw paths, commands, or unbounded output.
4. Add tests for success, stale ETag 409, expired/submitted 423/409 policy, invalid JSON/fields 400/422, candidate-failure result, repeat submit, and concurrent mutation.

### Safety and content isolation

Never accept a candidate path, command, upload, or reference selector. Test that coaching text cannot be executed or scored and that test output is bounded/sanitized before serialization.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] All listed mutation routes enforce the token/Origin/schema/ETag contract and call only the intended service.
- [ ] Run/test failure and submit/repeat-submit responses are distinguishable and stable.
- [ ] Focused web mutation, lifecycle, candidate-document, and CLI suites pass together.
