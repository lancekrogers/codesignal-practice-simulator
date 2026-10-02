# Iterate gate — 005/01_library_and_restart

Decision: one review finding accepted and fixed in place; no new tasks needed.

## Changes made

- F1 (dropped restart announcement): `webui/src/attempt_lifecycle_actions.ts`
  no longer announces before `runtime.cleanup()` disposes the live region. The
  replacement's reconnect screen (`role=status`) and attempt shell carry the
  transition for assistive technology. Bundle rebuilt.
- F2 (fragment kept across routes): left as is, with the rationale recorded in
  results/review.md (the fragment is non-secret view state and preserving it is
  what restores level/tab on "Back to library → Reconnect", an accepted
  journey).

## Verification after the change

    just build assets                                   rebuilt
    just build assets-check                             manifest verified
    npx playwright test restart_end.spec.mjs library_routes.spec.mjs   12 passed
    git diff --check                                    clean

The change touches one call inside the restart success path only; the full
suites recorded in results/testing.md (187 browser, 454 unit) ran on the code
immediately before it, and the two affected specs were rerun after it.

## Another iteration?

No. Both tasks meet their Done When criteria; the sequence goal's deliverables
(routes/catalog UI, End/Restart/Reset UX) and quality standards (no accidental
timer start, saved work preserved with an unsaved-buffer gate) are demonstrated
in the results files. Carried follow-ups stay with 005/02 and 006 as listed in
the task results.
