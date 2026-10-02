---
fest_type: task
fest_id: 02_implement_read_api_and_static_serving.md
fest_name: implement read api and static serving
fest_parent: 03_local_web_api
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:28.366014-06:00
fest_updated: 2026-09-09T05:46:11.460194-06:00
fest_tracking: true
---


# Task: implement read API and static serving

## Objective

Implement the authoritative read-only browser contract and safe static delivery for bootstrap, session/time, copied prompts, candidate source, and source history.

## Requirements

- [ ] Create `src/codesignal_practice_simulator/web/routes.py` read handlers for `GET /api/bootstrap`, `/api/session`, `/api/time`, `/api/prompts/{1..4}`, `/api/source`, and `/api/source/history` with UUID/query validation.
- [ ] Use `RuntimeApplication` services: lifecycle/status/time, `PromptService.read_prompt`, `CandidateDocumentService`, and safe context/score serializers; bootstrap must never start an attempt.
- [ ] Return `{ok,data}` or `{ok:false,error:{code,message}}` envelopes with stable status mappings, no-store API headers, no-sniff/referrer policy, and explicit static MIME/cache policy.

## Implementation

Follow these steps in order:

1. Define route parsing and response helpers in `src/codesignal_practice_simulator/web/responses.py`; reject missing/duplicate/unknown query values and map domain errors without exposing exception text or paths.
2. Have bootstrap return assessment metadata, duration profiles, four-level labels, first-party rules, and an optional selected durable session; use `LifecycleService.status/time` only when a selection exists.
3. Read prompts only through `PromptService.read_prompt`, and read source/history only through `CandidateDocumentService`; bound prompt/source/history payloads to the API contract.
4. Add `tests/test_web_server.py` cases for no-attempt bootstrap, selected active/expired/submitted sessions, prompt levels, source ETag, history metadata, missing/corrupt state, static assets, traversal, HEAD/GET policy, and headers.

### Safety and content isolation

Assert response bodies never contain cache roots, `solution/`, `study/`, `notes/`, vendor/reference bytes, raw test modules, or scorer commands. Only copied `levelN.md` prompts may be returned.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] Every D004 read route returns the documented envelope and authoritative state.
- [ ] Bootstrap does not create state or advance time, and refresh reads durable selected attempts.
- [ ] HTTP read/static tests pass for success, malformed selectors, forbidden resources, headers, cache policy, and content isolation.
