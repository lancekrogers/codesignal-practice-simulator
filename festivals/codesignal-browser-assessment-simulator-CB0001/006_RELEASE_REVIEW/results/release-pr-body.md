## Summary

Adds a local browser assessment simulator over the existing CLI lifecycle and
scoring services: timed entry and editor, source autosave/history/reset/restore,
practice checks, final submission, and refresh/restart recovery.

The server is loopback-only with a per-launch capability and fixed API/static
allowlists. Browser assets are packaged for offline runtime. Coaching uses safe
derived context; source/history access still requires candidate permission.
This is local practice, not official hidden-test or OS-sandbox equivalence.

Independent review caught and remediated repeated-content history loss and
sustained-output timeout starvation, with failing-before/passing-after tests.

## Verification

- Canonical `just verify`:289 tests plus4 explicit end-to-end tests passed.
- Isolated installed-wheel browser suite:171passed;94sdist/49wheel members,
  14static members,13verified assets; console and module entry points checked.
- Focused remediation matrix:46tests each on Python3.10,3.11,3.12 passed;
  full canonical run on Python3.14. Python3.13/otherOSes not exercised.
- Fresh local project clone:289+4passed; targeted campaign clone smoke passed.
- Architecture and security re-review found no unresolved implementation defect.
- Final independent UI review:171 checkout cases and a focused interaction
  probe passed; temporary probe defects diagnosed, no product defect found.

CB0001 release records contain the final UI/gate/remote reproduction evidence.
No fetched assessment/reference bytes, attempts, caches, tokens, dependency
directories or temporary browser artifacts are included in the changes.
