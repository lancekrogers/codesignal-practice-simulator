# Planning Gaps and Decisions

## Resolved product interpretations

No product question requires another user interruption. The user explicitly
approved a browser application that is as close as practical to the real
CodeSignal candidate experience and delegated routine decisions to the agent
and judge.

The following choices are therefore safe engineering decisions:

- Build a local single-user application, not a hosted multi-user clone.
- Match consequential layout and behavior without copied branding or assets.
- Treat the existing four-level Python/file-storage assessment as the only
  supported assessment and language in this release.
- Use server state as the lifecycle authority and browser storage only for
  disposable editor preferences.

## Decisions the architecture must make

1. **Editor packaging.** Monaco Editor 0.56.0 is the current npm release and is
   MIT licensed. Bundle it locally with a locked npm dependency and reproducible
   build; ship the built runtime assets inside the Python wheel. A plain textarea
   fallback would miss the requested assessment-IDE fidelity.
2. **Web runtime.** Use the standard-library `ThreadingHTTPServer` and narrow
   route handlers. The app needs no general web framework, templates, database,
   authentication system, or runtime Node installation.
3. **Composition boundary.** Extract the private `_RuntimeApplication` in
   `cli.py` into a public application container/factory shared by CLI and web
   transports. Domain behavior stays in existing services.
4. **Candidate document ownership.** Add a locked service that alone resolves,
   reads, atomically writes, resets, and revisions the registered
   `simulation.py`. HTTP handlers never accept filesystem paths.
5. **Concurrency.** Use the SHA-256 of persisted source bytes as an ETag. Every
   write/restore/reset uses optimistic concurrency and the existing attempt
   lock; test and submit first persist the editor snapshot and then evaluate it.
6. **History representation.** Store bounded attempt-local source snapshots and
   metadata separately from lifecycle events. History is source recovery, not
   keystroke replay.
7. **Capability scope.** Generate an unguessable per-server token, carry it in
   the initial URL, move it into a same-tab request header, and remove it from
   the address bar. Require the token and a matching loopback `Origin` for every
   mutation. This defends against drive-by browser requests, not malicious
   processes running as the same local user.
8. **Browser delivery.** Serve a small static HTML/CSS/JavaScript shell and
   Monaco resources as Python package data. The runtime performs no network
   fetches and sets a restrictive CSP.
9. **Testing.** Keep domain tests in `unittest`, add transport/API tests against
   temporary workspaces, and add an isolated Playwright suite for the candidate
   journey. Browser tests use synthetic fixture material and injected clocks.

## Known implementation risks

- Monaco adds a large generated asset. License/provenance, package-data rules,
  worker paths, wheel contents, and offline startup need explicit verification.
- Autosave, test, timeout, and submit can race. All final actions must use one
  coherent persisted snapshot and return idempotent domain results.
- The current scorer output was designed for terminal use. The web contract
  must return bounded, candidate-safe structured fields rather than raw internal
  paths or commands.
- Refresh and server restart must distinguish “no attempt,” “active attempt,”
  “expired attempt,” and “submitted attempt” without starting or extending time.

## Evidence reviewed

- All ingest outputs and their official behavior references.
- Repository package/test structure and current `pyproject.toml` package-data
  boundary.
- Cursor Agent repository architecture review anchored to current service files.
- Local Node 26.7.0/npm 11.19.0 availability and npm registry metadata for
  `monaco-editor@0.56.0` (MIT).
