# In-flight coordinator review — task 02

Resolve these before accepting the installed-wheel proof:

1. Default Playwright reporters leave the allowed `.last-run.json` metadata in
   the output root. The new unconditional `if output.exists(): raise` will fail
   even after a clean suite. Use the existing cleanliness policy to reject real
   retained artifacts, then remove the owned output; do not override reporters.
2. The new global `subprocess.run(timeout=300)` can kill only npm while its
   Playwright descendants keep running. Preserve the prior unbounded outer
   runner (tests/fixtures have their own bounds), or implement/test whole-tree
   cleanup; do not add an arbitrary timeout that leaves processes behind.
3. Add a focused regression for actual installed continuity subprocess cwd and
   environment. A standalone package-origin probe alone would still pass if
   `continuity_controls` regressed to injecting checkout `src` into PYTHONPATH.
   Clear inherited PYTHONHOME as well as PYTHONPATH consistently for installed
   browser and CLI children.
4. Reuse the existing forbidden-artifact policy or retain its full set:
   the new archive set omits __pycache__, build, dist, .tmp and several existing
   cache/output classes. Verify sdist static bytes as well as its member names.
5. Be explicit that real console/module `web --no-open` probes launch and serve
   the unmodified wheel; synthetic cache injection is used by the separate
   installed browser fixture for the full start/edit/test/submit journey. Do not
   replace the pinned wheel manifest and call it the same artifact.

Observed during the first installed suite: the retained failure directory named
the existing `harness` streaming-before-body-finish test. Classify and reproduce
that failure; it is not by itself proof of a wheel-runtime defect.

These notes are not a completed review gate or authorization to weaken any
provenance, privacy, or offline assertion.
