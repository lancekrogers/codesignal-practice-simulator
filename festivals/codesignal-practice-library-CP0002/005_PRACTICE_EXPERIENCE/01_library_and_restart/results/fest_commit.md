# Commit gate — 005/01_library_and_restart

Committed with `fest commit --no-root` from the festival directory into the
linked worktree `projects/worktrees/codesignal-practice-simulator/cp0002-practice-library`
(branch `cp0002-practice-library`). No root pointer update, no gitlink
synchronization, no push.

    c72c8ab [jobsearch:c46efcc1-FE-CP0002] feat: routed practice library with catalog readiness and End/Restart/Reset attempt controls

Scope inspected before committing: every change in the worktree belonged to
this sequence (route model, library and continue screens, lifecycle actions,
server shell routing, docs, browser specs, static-route test, and the rebuilt
bundled assets under `web/static/`, which are tracked package inputs). The
worktree is clean after the commit. Festival files remain uncommitted at the
campaign root pending a separately scoped root commit; the `projects/*`
submodule pointers were not touched.
