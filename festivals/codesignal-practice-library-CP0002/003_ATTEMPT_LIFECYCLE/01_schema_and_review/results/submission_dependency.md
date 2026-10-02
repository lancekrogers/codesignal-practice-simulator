# Submission capture dependency — unresolved before implementation

Task 003/01/02 remains pending. No submission-capture code has been changed.

A Cursor Sonnet 4.6 medium-thinking delegation was stopped after returning no
result or code changes; it is not accepted review evidence. A replacement bounded
read-only Composer 2.5 check confirmed the coordinator's dependency concern:

- v1 SessionState persists AssessmentMetadata only (ID/name/level count).
- AssessmentDefinition has no content version or digest.
- Persisted-definition lookup compares metadata against today's registry, not a
  creation-time content pin.
- Packaged fetch metadata has upstream/file hashes, but those do not prove a
  persisted historical identity for an already-existing v1 attempt.
- PinnedAssessment/ReviewRecord require identity that must not be fabricated.

Required plan repair before continuing:

1. Bring the provider/creation identity dependency from 004/01 ahead of production
   submission capture, or introduce an explicitly staged interface with activation
   after both sides pass integration. Preserve working lifecycle commands: merely
   emitting v2 now is unsafe because recovery still rejects v2.
2. Specify legacy review fields independently: stored metadata, unavailable
   historical content identity, and whether submitted-source bytes were actually
   captured. Never relabel a current file as verified historical submission bytes.
   Moving task order alone cannot invent pins for old v1 records.
3. Update executable dependencies and decisions, validate with fest, then resume
   the next task. Do not mark capture complete on the strength of model tests.

No product choice is needed for this technical repair. D005's proposed exercise
topics remain a separate user choice before content authoring.
All Cursor jobs have exited; no background implementation remains.

## Resolution (2026-09-11, coordinator)

Chose option 1: move the identity work ahead instead of staging an inactive
interface, because restart (003/02/01) also creates attempts and would otherwise
mint v1 replacements.

- Inserted 02_creation_identity with `fest create task --after 1`; capture,
  review and gates renumbered to 03–08. File Storage identity comes from the
  packaged manifest hashes (upstream commit 6aab304) plus the runner contract,
  re-verified against staged bytes. The same task makes lifecycle, WAL,
  missing-event recovery and transports handle v1 and v2 before creation
  switches to v2, which covers the "recovery still rejects v2" hazard.
- Specified the legacy review fields as three independent axes (D002
  amendment): stored metadata, content identity pinned/unavailable, source
  binding captured/not_captured/not_applicable. No old v1 record gets a pin.
- 03_submission_capture now defines the review member, v1/v2 state binding, WAL
  publication order, scored-bytes re-verification and payload rules.
- 003/02/01 upgrades an abandoned/restarted v1 record to a v2 legacy-identity
  variant (content identity unavailable), since session/v1 has no abandoned status.
- 004/01/01 generalizes the existing File Storage identity into providers
  without changing its digest.

Validation after the repair is recorded in CONTEXT.md.
