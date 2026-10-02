# D004: Loopback Capability and Narrow JSON API

**Status:** accepted
**Date:** 2026-09-09

## Context

A local HTTP listener can still receive cross-origin browser requests or expose
files accidentally. The app is a same-user practice tool, not a hardened remote
execution service.

## Options

### Trust loopback alone

- **Pros:** simplest URL.
- **Cons:** vulnerable to drive-by browser requests and accidental broad APIs.

### Accounts/cookies/CSRF framework

- **Pros:** conventional hosted security model.
- **Cons:** inappropriate complexity and misleading guarantees for a local app.

### Per-launch capability plus Origin validation

- **Pros:** small, explicit, testable boundary suited to loopback use.
- **Cons:** other processes under the same OS user remain trusted.

## Decision

Bind only to `127.0.0.1` on an ephemeral/default configurable port. Launch
`http://127.0.0.1:<port>/#token=<256-bit secret>`; JavaScript moves the token to
`sessionStorage` and removes the fragment. Every `/api/*` request requires
`X-Simulator-Token`; every mutation also requires exact
`Origin: http://127.0.0.1:<port>`. Do not enable CORS.

Routes are fixed, methods are allowlisted, request bodies are JSON and capped,
and attempt IDs are UUID values rather than paths:

- `GET /api/bootstrap`
- `POST /api/attempts`
- `GET /api/session?attempt_id=` and `GET /api/time?attempt_id=`
- `GET /api/prompts/{1..4}?attempt_id=`
- `GET|PUT /api/source?attempt_id=`
- `GET /api/source/history?attempt_id=`
- `POST /api/source/reset` and `POST /api/source/restore`
- `POST /api/test` and `POST /api/submit`

Success uses `{ "ok": true, "data": ... }`. Errors use
`{ "ok": false, "error": { "code": "...", "message": "..." } }` with
stable 400/401/403/404/409/413/422/423/500 mappings. Candidate-caused test
failure remains a successful HTTP exchange with failed group results.

All responses set no-sniff and referrer policy. API/state responses use
`Cache-Control: no-store`; fingerprinted assets may be immutable. HTML sets a
restrictive CSP, frame denial, and no permissions. There is no arbitrary file,
command, upload, template, proxy, websocket, or directory-listing route.

## Consequences

- Restart creates a new capability while durable selected attempt state remains.
- Documentation clearly states the same-local-user threat boundary.
- Route tests enumerate rejected methods, origins, tokens, paths, oversized
  bodies, malformed JSON, symlinks, and content leaks.
