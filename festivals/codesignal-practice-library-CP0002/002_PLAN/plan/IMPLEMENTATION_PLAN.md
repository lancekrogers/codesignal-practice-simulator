# Implementation plan — CP0002

Status: planning gates passed; implementation started in the isolated worktree.
D001–D005 are the design contracts; task-level review refinements are recorded
in ../results/cursor-scaffold-review.md.
The Cursor audits are in ../results/cursor-source-audits.md. Exact content choice
in D005 remains subject to user preference; platform tasks need not invent it.

## Outcome and ordering

Preserve the existing local Python engine and bundled UI while delivering multiple
exercises, repeatable attempts, durable history, and honest submission review.
Sequence order is 003/01 → 003/02 → 003/03 → 004/01 → 004/02 → 005/01 →
005/02 → 006/01 → 007 review. No parallel writes to the same persistence surfaces.
Once API contracts stabilize, independent read-only reviews or bounded content
work can use Cursor sub-agents with explicit file ownership and cost-conscious
models. Higher-reasoning review is reserved for lifecycle/recovery risk.

## Preparation

Before any implementation: read fresh AGENTS.md; inspect current branch/dirty state;
create a dedicated camp project worktree from the integrated baseline; relink the
festival and confirm fest next there. Do not commit user changes from the audit
checkout. Verify integration of prior navigation/shutdown fixes rather than
reimplementing them. Use fest commit for execution, with root pointer changes
explicitly controlled; inspect the wrapper scope before invoking it.

All anchors below are project-relative, inspected during planning at 7833def.
Prefix Python filenames with src/codesignal_practice_simulator/. Revalidate
anchors and conventions before edits. Proposed new modules are named as proposals,
not claimed to exist.

## 003_ATTEMPT_LIFECYCLE — Durable reusable attempts

### 01_schema_and_review (D001/D002, R5–R8)

**01_versioned_models** — Extend models.py:338/:521 and persistence.py:86/:172.
Add strict v2 attempt/event/review models and v1 adapters, explicit abandonment
metadata and content identity. Old valid records remain valid in memory; unknown
versions fail with safe issue codes. No read-triggered upgrade. Add synthetic
v1/v2 serialization, invariant, malformed-data and missing-definition tests.

**02_creation_identity** (inserted 2026-09-11 by the dependency repair in
003/01/results/submission_dependency.md) — Derive File Storage content identity
from the packaged manifest hashes and runner contract, re-verify staged bytes,
make every lifecycle path handle v1 and v2, and activate session/v2 creation.
v1 attempts keep the legacy adapter and never gain an identity.

**03_submission_capture** — Extend lifecycle.py:240/:315 and application.py:371.
Bind an explicit attempt, saved revision and exact scored bytes through the
cross-process lock; extend submission WAL with an immutable review member.
Recovery replays the recorded outcome without another scorer call. Reject
expired source-mutation payloads. Record D002's independent identity and
source-binding axes. Test save/submit races, duplicate submission,
each durable write failure, missing/different review bytes and unchanged results.

**04_readonly_review_service** — Add a proposed attempt_reviews.py service using
bounded non-repairing persistence readers, not candidate_documents.py:52 or
workspace.py:239. New records return verified immutable data; legacy returns
stored summary and explicitly unbound available source. Test unchanged directory
hashes/pointer, removed assessment, malformed ID, oversized files and symlinks.

### 02_restart_and_abandon (D001, R3/R4/R9)

**01_restart_journal** — Extend workspace.py:116/:145 and persistence.py with the
D001 operation record and recovery helpers. Validate content before commit intent;
preserve old source and original timer; post-commit failures roll forward the same
replacement. Test every stage/rename/fsync boundary, mismatched replay payloads,
unexpected current revisions, and interrupted operation discovery.
Replay completed operations after their replacements have been submitted and
after a later restart; return the original ID without changing current selection.

**02_shared_lifecycle_actions** — Extend lifecycle.py:82/:132 and application.py.
Add explicit abandonment/restart, common CLI/browser live-selection policy and
safe stale/busy errors. Keep source reset separate. Add CLI parser/serialization
with shared application validation; 003/03/02 owns HTTP route wiring. Test terminal retries, stale tabs, two
processes, restart versus submit, retry after failed response and unchanged legacy
non-selected attempts. No implicit deletion or submission.

### 03_attempt_history_api (D002/D004, R5–R7)

**01_metadata_listing** — Add a proposed attempt_history.py reader at the
application boundary (application.py:174). Enumerate validated UUID directories,
metadata only, with bounded reads/page memory and deterministic cursor filtering.
Do not use operational status()/time() if they repair on read. Test empty lists,
mixed schemas, partial corruption, symlinks, moving pages, unknown filters and
no source/events/prompt reads. No retention cap or eager source loading.

**02_history_and_review_routes** — Extend web/routes.py:120/:177/:208 and CLI
commands. GET attempts lists; POST still starts; explicit UUID review uses 003/01.
Use existing capability/origin/query/error conventions. Test no active-pointer
mutation, no rescore, invalid cursors, unsafe IDs, authorization and safe errors.
Document fields and legacy warnings in docs/cli-contract.md or owning API docs.

## 004_ASSESSMENT_LIBRARY — Complete original exercises offline

### 01_versioned_catalog (D003, R1/R8/R11)

**01_input_providers** — Extend assessments.py:56/:88, workspace.py:116/:329 and
application.py:343 with a narrow provider boundary. Retain existing fetched-cache
validation and the 003/01/02 File Storage identity (digest unchanged); add
validated packaged originals through the same pinned creation path. Test
missing/tampered resources before mutation or abandonment, original startup
without legacy fetch, and legacy File Storage.

**02_catalog_and_distribution** — Replace application.py:174 hardcoded catalog,
expose metadata/readiness via fixed routes, and update CLI discovery. Extend
pyproject.toml package resources and existing packaging allowlists/checkers.
Keep history review independent of installed definitions. Test outside-checkout
wheel discovery, removed versions, duplicate identity, and wrong profiles.

### 02_original_content (D003/D005, R1/R2/R11)

**01_content_specifications** — Record user topic/count decision from D005 first.
Write original exercise specs with exact signatures, time/ordering rules, return
values, level dependencies, examples and edge cases. No copying protected content.
The proposed two tracks are In-Memory Records and Account Ledger; do not silently
substitute a festival ID as an exercise ID. Review all four progressive levels.

**02_content_and_correctness** — Author package prompts, starters, deterministic
tests and version manifests for each accepted track. Keep the fixed
test_simulation.TestSimulateCodingFramework.test_group_1..4 entry points observed
in scoring.py:193. Add development-only correct and deliberately wrong examples;
verify all levels, invalid inputs, determinism, bounded execution, and no oracle
leak in candidate-distributed resources. Reuse the existing isolated scorer.

## 005_PRACTICE_EXPERIENCE — Select, repeat, browse, review

### 01_library_and_restart (D004, R1/R3/R4/R10)

**01_routes_and_catalog_ui** — Extend webui/src/app.ts:51/:97 and existing
state/views. Add validated library/attempt/history/review navigation with reload
and back/forward reconstruction, preserving capability capture. Library shows
catalog readiness and active selection. Test keyboard focus, unknown routes,
empty/loading/failure states, no accidental timer start and metadata-only entry.

**02_restart_ux** — Add distinct End attempt and Restart controls/confirmations
through existing attempt runtime operation locks; retain Reset source meaning.
Save first or explicitly discard unsaved buffer, never lose saved old code.
Busy/conflict/stale/recovery-pending states are actionable. Synthetic browser
tests must verify old bytes/status plus new ID/deadline, duplicate clicks and
server restart during operation. Make CLI alternatives discoverable.

### 02_history_and_review (D004, R5–R10)

**01_history_screen** — Implement assessment/status filters, bounded pagination,
per-entry availability and safe partial-error display using 003/03 APIs. Preserve
filter/position through review/back. Test empty and growing collections, retries,
keyboard navigation, and that listing never requests source/history content.

**02_review_screen** — Display read-only submitted source, result summary, safe
per-level outcomes and timing/version; distinguish legacy-unbound, expired and
abandoned work. Retry uses current catalog version with a visible version-change
notice and explicit live-attempt conflict resolution. Browser/API tests prove no
old mutation/rescore or active-selection change and meaningful missing-data errors.

## 006_RELEASE_VERIFICATION — User outcome and package evidence

### 01_acceptance_and_distribution (all requirements)

**01_full_acceptance_matrix** — Run synthetic CLI/browser flows for every accepted
exercise and lifecycle outcome; legacy review, crash/restart, cross-process races,
save conflicts, stale tabs, pagination, missing content and security rejection.
Keep existing locked Playwright privacy reporters; no real candidate work.

**02_offline_and_docs** — Build/rebuild assets and install wheels outside checkout;
complete original exercises offline without legacy cache, and test File Storage
with its explicit setup. Run canonical and provenance checks. Update README,
CLI/API, safety and troubleshooting docs for every new action; record actual
commands, counts, negative-path evidence and unresolved limitations.

## 007_RELEASE_REVIEW — Independent assessment

Review phase, no numbered sequences. Judge actual requirements evidence,
lifecycle/data-loss risks, original content correctness, UI journeys and package
boundaries. Reviewers must provide reachable triggers/impact for blockers.
Fix and rerun relevant evidence, open a ready PR, and record publication status.
Do not claim merge or user approval without evidence.

## Gates and requirement coverage

Each implementation sequence ends with testing, review, iterate and fest-commit
gates. Task acceptance is behavior/evidence-based, not arbitrary quotas.

| Requirement | Delivery | Evidence |
| --- | --- | --- |
| R1/R2 library/content | 004, 005/01 | each original exercise works offline with four-level correctness |
| R3/R4 repeat/restart | 003/02, 005/01 | unique replacement, unchanged old bytes/timer, confirmed transitions |
| R5 history | 003/03, 005/02 | metadata-only pagination, legacy/corrupt/missing entry behavior |
| R6/R7 review | 003/01, 005/02 | immutable result/source, no side effects, active selection retained |
| R8 compatibility | 003/01, 004/01 | strict v1 reads, honest unavailable fields, version removal |
| R9 recovery | 003/01–02 | deterministic failures at every durable boundary, replay and races |
| R10 UX | 005 | real keyboard/mouse/reload/back/forward/restart flows |
| R11 distribution | 004, 006 | deterministic resources, wheel outside checkout, network blocked |

Canonical baseline: just verify with required build tools; just check frontend;
just build assets and just build assets-check; just check browser;
just check wheel. Inspect the current recipes before execution and preserve their
isolation/provenance requirements. Focused module tests run per task; full gates
run at integration/release. Structural fest validation alone does not count.
