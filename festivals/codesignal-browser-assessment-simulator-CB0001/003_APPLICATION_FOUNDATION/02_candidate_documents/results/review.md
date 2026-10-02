# Candidate Document Independent Reviews

Three fresh read-only Cursor reviews challenged the diff.

## First review

Rejected commit readiness for bytes leaking into JSON-facing models,
nondeterministic UUID ordering when timestamps tie, a 775-line mixed-responsibility
module, missing-source/error normalization, overly broad service locking, and
gaps in concurrency/crash/lifecycle/content-isolation tests.

## Second review

Confirmed the first refactor resolved JSON safety and module size, but found the
claimed monotonic order was still not persisted and several negative tests were
partial. Those issues were repaired with durable operation order and stronger
coverage.

## Third/final review

Found one remaining material issue: rejected mutations on final legacy attempts
could create `.candidate-initial.json` before the mutability check. The final
repair moved final-state validation ahead of legacy initialization and added
complete-tree byte-equality tests for save/restore/reset on expired/submitted
attempts.

The reviewer also described check-then-read symlink swapping by a malicious
same-user process. This is accepted within D004's documented threat boundary:
ordinary symlinks are rejected, while hostile processes running as the same OS
user are not claimed to be sandboxed. No browser/API surface can request a path.

Pre-existing `workspace.py`/`persistence.py` file-size debt was not expanded into
an unrelated refactor; every new file and function obeys the festival limits.
