# Task 01 focused independent review

Cursor CLI, fresh read-only session, `gpt-5.6-luna-high`, reviewed the new
`webui/tests/candidate_journey.spec.mjs` against existing helpers and runtime.
Base: `be5389b`; the implementation agent was still verifying its additions.

Findings to resolve before task completion:

1. Restart used `EntryPage.open`, which asserts fresh-entry text and prevents
   reaching reconnect assertions for a persisted active attempt. Use navigation
   followed by the existing reconnect assertion.
2. History checks verified hash syntax and inequality, but should independently
   calculate hashes from the synthetic candidate content and compare the chain.
3. The first-party rules assertion should include optimistic concurrency and
   latest-saved-source terms, not just timer/no-pause wording.

The coordinator additionally requires an explicit persisted indentation assertion
for the Python-editing test; its title alone is not evidence of indentation.

## Disposition — 2026-09-10

All findings are resolved:

1. **Restart navigation and identity — resolved.** Restart uses `page.goto`,
   accepts either the reconnect action or an already-rendered editor, and
   compares `main[data-attempt-id]` with the original
   `started.data.session.attempt_id`. It also polls the public source envelope
   for the synthetic marker before stopping the fixture process, eliminating a
   stale “Saved snapshot” race.
2. **Independent history hashes — resolved.** The test builds the first and
   second exact buffers from the actual synthetic start content, calculates
   SHA-256 values independently with `node:crypto`, and compares both snapshot
   links plus the current content/ETag.
3. **All first-party rule terms — resolved.** The pre-start region now asserts
   authoritative/no-pause timing, optimistic concurrency, and latest-saved
   source behavior, plus the confirmation dialog's immediate no-pause warning.
4. **Persisted Python indentation — resolved.** The editor journey polls the
   public source API and requires the expected synthetic function body with
   its automatically completed brackets and four leading spaces.
5. **Syntax and bracket reliability — resolved.** Assertions poll computed
   leaf-token text/styles, normalize Monaco non-breaking spaces, and tolerate
   punctuation split across or combined within token spans. Bracket input uses
   typed input so Monaco's real auto-closing path is exercised. The
   `bracketMatching` contribution and rebuilt assets remain in place.

### Verification record

- Initial focused iteration: 1 failed, 4 passed; the sanitized editor failure
  led to the token normalization and typed-bracket fixes.
- Restart isolation before the persisted-source wait: 1 failed; after the
  source-envelope poll: 1 passed.
- `npm run test:browser -- tests/candidate_journey.spec.mjs` — 5 passed.
- `npm run test:browser -- tests/candidate_journey.spec.mjs tests/editor.spec.mjs tests/source_save.spec.mjs` — 26 passed.
- `npm run check` — passed.
- `git diff --check` — exit 0.
- Reviewed coordinator reuse evidence:
  `ASSET_BUILDER=/private/tmp/cb0001-release.HTxOTs/builder/bin/python just verify`
  — 275 discovered tests plus 4 explicit end-to-end tests passed, no skips,
  with all recorded legacy checks passing.

The reviewed task-01 reuse mapping is recorded in
`01_cover_entry_editor_and_recovery_journey.md`. No reporter override, real
candidate/FETCH_ONLY read, commit, or task/workflow status mutation was used.
