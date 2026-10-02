# Documentation coordinator check

Review these against the final draft before task completion (not all are
necessarily present after the implementation agent's own checks):

- Distinguish URL fragment handling from API authorization: the browser does not
  send the fragment as part of an HTTP URL, but the app sends its capability in
  the same-origin authorization header. Do not imply the token never travels in
  requests or cannot enter diagnostic logs.
- The wheel does pin fixture metadata/hashes; it does not carry fixture bytes.
  Avoid “does not pin” and “bundled visible and synthetic checks” if those imply
  the wheel contains assessment/test sources.
- Show the expired-submit fallback with `--workspace-root "$workspace"` rather
  than a bare command that might target the operator's current directory.
- Explain exact Python build/test prerequisites for documented package commands
  on a fresh venv (including setuptools with no-isolation builds), not only npm.
- Cleanup instructions should identify the owned temporary directory and avoid
  presenting a broad unresolved-variable deletion as a routine next step.
- `Copy local version` really invokes keepLocal/CAS save, not a clipboard action;
  preserve the correct explanation already present in the draft.

The production source, assets and pinned manifest must remain unchanged by this
documentation task. Rerun documentation checks after any correction.
