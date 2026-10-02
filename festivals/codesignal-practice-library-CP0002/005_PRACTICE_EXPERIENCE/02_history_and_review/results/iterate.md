# Iterate gate — 005/02_history_and_review

Decision: all five review findings accepted and fixed in place; no new tasks
needed.

## Changes made

- F1 (blocking): `webui/src/review_state.ts` enforces the binding/source
  agreement in both directions and rejects `practice_score` on any
  non-ended attempt. The tampered-payload journey in `review_screen.spec.mjs`
  now also feeds a `captured` binding with a `legacy_unbound` view and asserts
  the error screen with no source viewer.
- F2: `webui/src/history_screen.ts` assigns the refreshed bootstrap only after
  the request is confirmed current.
- F3: both `history_screen.ts` and `review_screen.ts` fall back to the screen
  heading when the previously focused control is gone or disabled;
  `history_screen.spec.mjs` asserts the heading focus after Older reaches the
  last page.
- F4: `docs/cli-contract.md` rows-per-page wording corrected (control
  10/25/50/100, fragment 1–100, default 25).
- F5: `webui/src/history_state.ts` rejects a practice result on a non-ended
  row and a final score on an ended row.
- Bundle rebuilt.

## Verification after the changes

    just build assets                                   rebuilt
    just build assets-check                             manifest verified
    npx playwright test history_screen review_screen library_routes --reporter=list   16 passed
    just check browser (locked privacy reporters)       197 passed, 0 failed
    python3 -m unittest tests.test_documentation        OK
    git diff --check                                    clean

The unit suite (455 OK) ran on the code immediately before these client-only
and docs-only changes; no Python changed in this iteration.

## Another iteration?

No. Both tasks meet their Done When criteria; the sequence goal (history with
filters, pagination, availability and preserved navigation state; read-only
review with honest legacy/expired/ended presentation and safe Retry) is
demonstrated in the results files. Carried follow-ups for 006 are unchanged
(`recover_restarts()` at startup, orphan staging housekeeping, wheel proof).
