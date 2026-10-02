# Versioned model foundation

Implemented by Cursor Composer 2.5 with coordinator review/corrections.

Changes: strict session/event version dispatch; session/v2 with explicit
abandonment and pinned content identity; event/v2; immutable review model;
in-memory legacy adapter with unknown identity explicitly unavailable; bounded
1 MiB session reads; supported-version checks before durable writes.
Existing v1 serialization remains unchanged. Added 24 synthetic tests.

Coordinator corrections: reject inconsistent review deadline/profile duration;
bound session reads through the injected filesystem and prove oversized/malformed
records fail without mutation. No real candidate data read or changed.

Actual verification:

    python3 -m unittest tests.test_attempt_models_v2 tests.test_models \
      tests.test_persistence tests.test_lifecycle tests.test_workspace \
      tests.test_application tests.test_workspace_pointer_recovery -q

106 tests passed after the final size-limit write guard; git diff --check passed.
The writer now rejects a record larger than its reader supports before publication,
preserving the previous readable record (one additional negative-path test).

Broader follow-up before that final guard: just check unit ran 319 tests successfully (one skipped:
archive build check requires an interpreter with the optional build package).
The initial run had 11 asset-build failures because this new worktree lacked
node_modules. After just build deps installed the locked nine packages,
just check frontend passed and the complete unit rerun passed. No asset source
changes were needed. This does not replace the later full release/package gate.

Staged integration: production lifecycle writers intentionally remain v1 until
submission/restart/provider tasks supply real identities and recoverable v2
transactions. Do not fabricate hashes or claim repeat/history UI is implemented.
02_submission_capture (renumbered 03 on 2026-09-11) must add immutable source member/state review binding and
v2 submission/missing-event recovery; 004/01 activates validated provider-based
creation. Review/history tasks own bounded non-repairing detail/event boundaries.
The new review model currently holds a digest, not the immutable source member.

Files: models.py, errors.py, persistence.py, filesystem.py, and
tests/test_attempt_models_v2.py. No sequence commit yet; gate follows all three
implementation tasks plus testing/review/iteration.
