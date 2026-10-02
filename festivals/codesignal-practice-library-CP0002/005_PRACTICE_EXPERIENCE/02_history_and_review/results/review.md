# Sequence code review — 005/02_history_and_review

## Scope and reviewers

- Delegated reviewer: Cursor `claude-sonnet-5-thinking-high`, read-only plan
  mode, bounded to the uncommitted diff plus the eight new files (history and
  review state/view/screen modules and their specs), generated bundle
  excluded. It ran `tests.test_attempt_reviews` and
  `tests.test_history_review_routes` (24 OK) and traced the listing, review,
  fragment, generation and retry-conflict paths against the stated invariants.
  Transcript: session scratchpad `review_005_02.txt`.
- Coordinator review: independent pass over `startRetry` (busy guard, abandon
  before start, no start after a failed abandon), dialog disposal on re-render,
  and fragment encoding into the listing query.

A reviewer verdict is not runtime verification; evidence is in results/testing.md.

## Findings and dispositions

**F1 — blocking (reviewer). The review normalizer checked the binding/source
agreement in one direction only.** A payload with `source_binding: "captured"`
and a `legacy_unbound` (or missing) source view would have rendered as
"Submitted source · exact scored bytes". Not producible by the current server,
but exactly the mislabeling the client-side integrity check exists to refuse.
ACCEPTED in 05_iterate: `normalizeReview` now requires captured ⇔ captured
view, `not_captured` ⇒ no view or a `legacy_unbound` view, `not_applicable` ⇒
no view, and `practice_score` only on an ended attempt. New assertion in
`review_screen.spec.mjs` (tampered-payload journey): such a payload is an
error screen with no source viewer.

**F2 — non-blocking (reviewer). Stale bootstrap could land in shared state.**
`history_screen.ts` assigned `state.bootstrap` before the generation check.
ACCEPTED in 05_iterate: the normalized bootstrap is assigned only after the
request is confirmed current, mirroring the review controller.

**F3 — non-blocking (reviewer). Focus dropped to `<body>` when the focused
control was re-rendered disabled** (Older at the last page, Newest at the
first, Retry while busy). ACCEPTED in 05_iterate: both controllers fall back to
the screen heading whenever the previously focused control is gone or
disabled. `history_screen.spec.mjs` asserts the heading is focused after Older
reaches the last page.

**F4 — nit (reviewer). Docs said rows per page "10–100".** ACCEPTED in
05_iterate: the control offers 10/25/50/100 and the fragment accepts 1–100;
the `/history` row now says so.

**F5 — nit (reviewer). `practice_score` was not cross-checked against status
in the history normalizer.** ACCEPTED in 05_iterate: a practice result on a
non-ended row, or a final score on an ended row, is rejected as invalid.

## Areas the reviewer checked and found clean

No mutation, rescoring or selection change outside the confirmed retry path;
history requests only the listing and bootstrap; fragment values are shape
validated and encoded; superseded listing/review/source responses are dropped;
the retry conflict path reads a fresh revision immediately before abandon, is
guarded against double clicks by `busy`, and never starts after a failed
abandon; no path or server text reaches the DOM; server `practice_score` can
only exist on an abandoned `session/v2` record and never interacts with the
verified-review-outranks-session path.
