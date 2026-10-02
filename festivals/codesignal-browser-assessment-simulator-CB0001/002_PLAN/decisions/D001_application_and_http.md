# D001: Shared Application Container and Standard-Library HTTP Adapter

**Status:** accepted
**Date:** 2026-09-09

## Context

`cli.py::_RuntimeApplication` already composes the registry, workspace,
lifecycle, evaluation, prompt, derived-status, context, and scorer services.
The browser must call the same behavior without importing a CLI parser or
duplicating domain rules.

## Options

### Keep the private CLI object and call CLI commands

- **Pros:** few initial edits.
- **Cons:** string/serialization coupling, subprocess overhead, poor error
  contracts, and no safe candidate-document boundary.

### Add Flask/FastAPI and a second composition root

- **Pros:** familiar routing conveniences.
- **Cons:** a runtime dependency and duplicated wiring for a small loopback API.

### Extract a public container and use `ThreadingHTTPServer`

- **Pros:** one production object graph, standard-library runtime, direct typed
  service calls, small auditable transport.
- **Cons:** routing and JSON/error handling must be implemented carefully.

## Decision

Move `_RuntimeApplication` into a public `application.py` container/factory and
leave `CommandApplication` as the CLI-facing protocol. Add a `web/` package whose
HTTP handlers receive the public container. Handlers parse HTTP, call one
application method, serialize a stable response, and contain no lifecycle,
filesystem, or scoring policy.

## Consequences

- Existing CLI tests must prove no behavior/exit-code drift.
- The container gains candidate-document and assessment-metadata collaborators.
- The browser server can use dependency-injected clocks/workspaces in tests.
- No web-framework runtime dependency is introduced.
