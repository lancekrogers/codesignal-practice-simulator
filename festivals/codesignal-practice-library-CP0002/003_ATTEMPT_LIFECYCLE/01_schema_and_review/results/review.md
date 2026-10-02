# Sequence code review — 003/01_schema_and_review

## Scope and reviewers

- Delegated reviewer: Cursor `claude-sonnet-5-thinking-high`, read-only plan
  mode, bounded to this worktree's `git diff` plus the four new test modules and
  `attempt_reviews.py`. Higher reasoning was used because the sequence is
  persistence and race code, as the gate requires. It ran ~12.5 minutes, read
  the diff, ran the suite itself (it reported 360 passed / 1 skipped / 238
  subtests) and built standalone repros for both findings it reported.
- Coordinator review: independent re-read of the recovery ordering, the submit
  path and the application payload path. The coordinator wrote the code under
  review, so the delegated review is the independent check.

A reviewer verdict is not runtime verification; evidence is in results/testing.md.

## Findings and dispositions

**F1 — blocking (reviewer). Review boundary displayed unprotected fields.**
`attempt_reviews.py` sourced the assessment, profile and start/deadline
timestamps from `session.json` even when a digest-verified `review.json` was
present, and `_require_matching_review` did not compare those fields. Trigger:
submit normally, then hand-edit only `session.json`'s `assessment` block; the
review returned the fabricated content identity with no issue flagged. Impact:
the immutable record existed but was not the source of truth for what the
review showed, defeating the tamper-evidence the pin is for. D002 allows
same-user tampering to be possible but requires detected changes not to produce
a falsely bound review. ACCEPTED — fixed in 07_iterate.

**F2 — non-blocking (reviewer). New review reader leaked absolute paths.**
`persistence.read_review` / `_read_review_bytes` embedded the full path in error
messages, while `attempt_reviews.py` deliberately uses only the attempt ID. The
same pattern pre-exists elsewhere in `persistence.py`; the objection is that new
code extended it. Local same-user CLI and loopback-only web limit the exposure.
ACCEPTED for the new code only — fixed in 07_iterate; the pre-existing messages
are left alone as out of scope.

**F3 — non-blocking (coordinator). Byte-strict review comparison could strand an
attempt.** `_publish_review_locked` compared raw bytes, so a reformatted but
semantically identical `review.json` written while a WAL was pending made every
later command fail closed forever. The review service already compares content,
not formatting. Trigger: pending `.submission-recovery.json`, then something
rewrites `review.json` with identical fields and different whitespace. ACCEPTED
— fixed in 07_iterate by comparing parsed records; differing content stays
corruption.

**F4 — nit (coordinator). Terminal payload check can misreport a concurrent
submit.** In `application._reject_terminal_source_mutation`, if another process
finalizes between the status observation and the saved-source read, a repeat
submit carrying a payload gets a read-only error where the contract says to
return the committed result. Rare and non-destructive. ACCEPTED — fixed in
07_iterate by re-checking terminal status inside that path.

**F5 — forward dependency, no change now (coordinator).**
`rendering._next_legal_commands` treats any status outside active/expired/
submitted as unavailable, so an `abandoned` record will fail the context view.
`abandoned` cannot exist yet; 003/02_restart_and_abandon introduces it and owns
this. Recorded so it is not discovered as a regression later.

## Areas the reviewer checked and found clean

Lock ordering and cross-process races in submit and recovery (submission is
serialized by the flock attempt lock; the review is published before the state
flips to submitted; every reader checks the pending marker first and fails
closed with `ReviewPendingError`); no scorer re-invocation during recovery; no
v1 record gaining a fabricated identity; `attempt_reviews.py` taking no lock,
creating no baseline and never running recovery; and the durability ordering of
`_publish_review_locked` / `_atomic_bytes` (write temp, flush, rename, flush
directory) with idempotent replay.

The reviewer correctly classified `rendering`'s context path as using the
pre-existing selection-time WAL completion rather than a new read-path write.

## Process note

Two `cursor-agent` processes from earlier sessions (started roughly two days
ago) were still running on this machine during the review. They are unrelated
to this job, which exited cleanly; they were left alone rather than killed. The
earlier claim that all Cursor jobs had exited is therefore not accurate.
