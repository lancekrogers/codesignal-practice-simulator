# D003: Locally Bundled Monaco Editor

**Status:** accepted
**Date:** 2026-09-09

## Context

The user needs realistic interview rehearsal: Python syntax, line numbers,
autocomplete, indentation, find, undo/redo, themes, font size, and tab settings.
Runtime must work offline and must not copy CodeSignal source/assets.

## Options

### Native textarea

- **Pros:** zero dependency and smallest bundle.
- **Cons:** materially unlike a coding-assessment IDE and misses requested editor
  behavior.

### CodeMirror 6

- **Pros:** smaller and modular.
- **Cons:** more assembly work for an IDE-like experience and less familiar to
  candidates used to VS Code-style editors.

### Monaco Editor

- **Pros:** mature VS Code-derived interaction, Python language support, strong
  keyboard/editing/settings fidelity, MIT license.
- **Cons:** larger generated bundle and worker/package complexity.

## Decision

Lock `monaco-editor@0.56.0` and a minimal esbuild-based development toolchain in
`package-lock.json`. Author browser source in small first-party modules, bundle
Monaco and explicit editor worker entry points, and copy generated assets into
the Python package. Runtime serves only packaged files and never requires Node
or a CDN.

Track the MIT license notice, package/version/tarball provenance, build command,
and dependency lock. Do not commit `node_modules`. Generated assets are allowed
in Git because they contain the licensed editor/application runtime, never
FETCH_ONLY assessment content.

## Consequences

- CSP must allow only self-hosted scripts/styles/workers (and `blob:` only if a
  tested Monaco worker path makes it unavoidable).
- Wheel and clean-install tests inspect and load every needed asset offline.
- A plain read-only `<pre>` fallback displays source with an actionable error if
  Monaco initialization fails; assessment mutation remains disabled rather than
  silently losing work.
