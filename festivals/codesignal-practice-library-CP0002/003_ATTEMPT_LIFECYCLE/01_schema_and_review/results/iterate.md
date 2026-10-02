# Iteration on review findings — 003/01_schema_and_review

All four accepted findings from results/review.md are fixed. F5 stays with
003/02 by design.

## F1 (blocking) — the verified review is now the source of truth

`attempt_reviews.py` builds the returned assessment, profile, start, deadline,
submitted timestamp and score from the review record whenever one exists, and
`_require_matching_review` now also compares assessment, profile, started_at and
deadline_at against the session. Editing `session.json` under a submitted
attempt no longer changes what the review shows; it is reported as corruption.

New test: `test_verified_review_outranks_an_edited_session_record` performs the
reviewer's exact repro (edit only `assessment.content_version`/`content_digest`
in `session.json`) and requires a corruption error. A second test asserts the
returned profile and timing equal the recorded review's. Mutation check:
removing the added cross-check makes the repro test fail.

## F2 (non-blocking) — new review errors name the attempt, not the path

`read_review`, `_read_review_bytes` and the publish mismatch now identify the
attempt by directory name. New test asserts a corrupted member's error contains
the attempt ID and not the workspace path. Pre-existing path-bearing messages
elsewhere in `persistence.py` were left alone as out of scope.

## F3 (non-blocking) — a reformatted review no longer strands an attempt

`_publish_review_locked` compares the parsed record when the bytes differ, so an
identical record in a different byte layout completes recovery instead of
failing closed forever. Unreadable or differing content is still corruption:
`_published_review_matches` treats a parse failure as no match.

New test: `test_recovery_accepts_a_reformatted_but_identical_review` reformats
the published member while a WAL is pending and requires recovery to complete
with the scorer spy armed. Mutation check: removing the tolerance fails it.
`test_recovery_fails_closed_when_a_published_review_differs` still passes.

## F4 (nit) — a concurrent finalization returns the committed result

`_reject_terminal_source_mutation` re-checks status and returns when the attempt
is already submitted, so a repeat submit carrying a payload gets the committed
result instead of a read-only error. New test covers the sequence.

## Verification after iteration

    just check unit        364 tests, OK (1 skipped)
    just check browser     175 passed, 0 failed
    git diff --check       clean

Mutation checks re-run for both new guards; each mutant was killed.
