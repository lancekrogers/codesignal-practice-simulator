---
fest_type: task
fest_id: 01_implement_web_server_and_cli_launch.md
fest_name: implement web server and cli launch
fest_parent: 03_local_web_api
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:28.20859-06:00
fest_updated: 2026-09-09T05:46:11.191308-06:00
fest_tracking: true
---


# Task: implement web server and CLI launch

## Objective

Add the standard-library loopback server lifecycle and a `codesignal-sim web` command that emits a capability URL without exposing a configurable remote host.

## Requirements

- [ ] Create `src/codesignal_practice_simulator/web/server.py` with `WebServerConfig`, `WebServer`, loopback binding, ephemeral/default port selection, 256-bit capability generation/injection, and clean shutdown.
- [ ] Create `src/codesignal_practice_simulator/web/resources.py` with an explicit packaged asset manifest/MIME map and no directory traversal or runtime filesystem-root browsing.
- [ ] Extend `cli.py` parser/dispatch and the application boundary with `web --workspace-root ... [--port 0] [--no-open]`, preserving existing command behavior and making browser opening injectable.

## Implementation

Follow these steps in order:

1. Define `WebServerConfig` with fixed host `127.0.0.1`, port, workspace root, no-open flag, and injectable token/browser opener; reject non-loopback configuration before binding.
2. Implement `WebServer.start()` around `ThreadingHTTPServer`, route requests to a handler created with the `RuntimeApplication`, and return `http://127.0.0.1:<port>/#token=<secret>` while keeping the secret out of logs.
3. Add `web/static/manifest.json` or an equivalent generated manifest and have `resources.py` resolve only listed package resources with `importlib.resources`; reject encoded traversal, directories, and unknown assets.
4. Add parser/factory/server tests with fake opener and a bound ephemeral port; verify shutdown releases the server and `python3 -m unittest tests.test_cli tests.test_web_server -v` passes.

### Safety and content isolation

Bind only to loopback. Do not add upload, proxy, shell, websocket, directory-listing, arbitrary file, or arbitrary command routes; capability is local-user access control, not a same-user sandbox.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] `codesignal-sim web --no-open` starts on loopback and returns a usable fragment URL.
- [ ] Static resource lookup is manifest-bound and package-resource based in editable and wheel layouts.
- [ ] CLI regression tests pass and server lifecycle tests prove clean shutdown without leaked threads.
