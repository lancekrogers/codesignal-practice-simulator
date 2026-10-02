# Proposed festival decomposition

Goal: a complete select → practice → submit → review → retry product with multiple
assessments and preserved history. This is the DECOMPOSE output, not permission
to scaffold or execute unresolved implementation tasks. DESIGN must resolve
inputs/gaps.md and attach exact contracts before task creation.

## 001_INGEST — Requirements and current-state audit

Workflow phase; completed through configured intake and phase judges. Produces
R1–R11, constraints, verified source anchors, and explicit content proposals.

## 002_PLAN — Architecture and execution plan

Workflow phase. Resolve lifecycle/recovery, submission review, catalog/versioning,
legacy compatibility, user flows and error states; then produce an approved
implementation plan and scaffold each sequence just in time.

## 003_ATTEMPT_LIFECYCLE — Reusable attempts with durable history

### 01_schema_and_review — Preserve and explain persisted work (R5–R8)

1. Specify and implement versioned readers for legacy/new attempt metadata,
   abandoned state, and submitted-source/result identity.
2. Add recoverable immutable submission-review storage and read-only legacy
   fallback, with unavailable-detail labels and no implicit baseline writes.
3. Verify migration fixtures, terminal immutability, missing/corrupt source,
   removed catalog definitions, and digest mismatch.

Anchors: models.py:338, persistence.py:86, lifecycle.py:315,
candidate_documents.py:52. Prefix all these with src/codesignal_practice_simulator/.

### 02_restart_and_abandon — Explicit fresh practice (R3–R4, R9)

1. Implement abandonment and restart in shared lifecycle/application services.
2. Add operation identity, lock ordering, write-ahead recovery and exact-once
   replacement publication across old/new attempts.
3. Expose explicit CLI/browser actions with safe conflict responses and no
   source-reset or in-place timer-reset ambiguity.

Anchors: lifecycle.py:82, :132, workspace.py:116, :145, application.py:299.
Depends on 01. Test every publication boundary and duplicate/concurrent request.

### 03_attempt_history_api — Browse without changing selection (R5–R7)

1. Add bounded metadata listing with validated filters/cursors and deterministic
   order; isolate invalid entries without leaking filesystem paths or source.
2. Add explicit per-attempt review responses independent of active.json and the
   currently installed catalog, keeping existing source-history semantics.
3. Verify read-only disk state and unchanged active selection during history use.

Anchors: application.py:174, :245, web/routes.py:120, :208; workspace.py:310.
Depends on 01–02; schema and restart records determine listing behavior.

## 004_ASSESSMENT_LIBRARY — More complete exercises, not placeholder cards

### 01_versioned_catalog — Separate original and fetched inputs (R1, R8, R11)

1. Extend assessment metadata/registry with stable content versions and discovery.
2. Route attempt creation through per-assessment validated input providers;
   retain pinned File Storage checks and support packaged original inputs.
3. Update bootstrap/CLI selection and package data; test offline originals and
   incompatible/missing definitions without breaking old metadata review.

Anchors: assessments.py:56, :88, application.py:174, :343,
workspace.py:116, :329. Depends on 003 schema/version contracts.

### 02_original_content — Progressive, deterministic practice (R1–R2, R11)

1. Finalize content specifications for the agreed initial tracks and four levels.
2. Author original prompts, starter modules, level checks, and metadata.
3. Validate reference behavior and boundary/error cases using first-party
   development tests; verify starter failure/progression, determinism, and
   isolated scorer compatibility for each exercise.

Proposed tracks: in-memory records and account ledger. Content count/names need
acceptance before execution. Depends on 01; no proprietary assessment copying.

## 005_PRACTICE_EXPERIENCE — Complete browser journeys

### 01_library_and_restart — Select and repeat safely (R1, R3–R4, R10)

1. Add assessment selector, active-session summary, and fresh-attempt controls.
2. Add distinct source reset/abandon/restart interactions, confirmation, save
   conflict handling, busy states and operation recovery.
3. Verify new IDs/timers and preservation of old saved source via public APIs.

Anchors: webui/src/app.ts:51, :97; application.py:174.
Depends on 003 and 004 contracts/content.

### 02_history_and_review — Revisit results without disturbing practice (R5–R10)

1. Build filterable/paginated attempt history with empty/loading/partial-error states.
2. Build read-only submission view with exact source/result metadata and honest
   legacy warnings; provide retry and return navigation.
3. Verify keyboard focus, browser navigation/reload, active selection isolation,
   and missing snapshot/version recovery in synthetic real-browser journeys.

Depends on 003 history/review APIs and 005/01 navigation model.

## 006_RELEASE_VERIFICATION — Prove the complete experience

### 01_acceptance_and_distribution — Integrated evidence (R1–R11)

1. Run migration/crash/race, content correctness, and canonical project tests.
2. Run full synthetic browser journeys for all exercise/status combinations,
   including server restart and old-attempt review during active practice.
3. Build bundled assets and verify offline installed-wheel operation outside the
   checkout; update operating, CLI/API and safety docs and requirement evidence.

Depends on all implementation sequences. Reuse current Just recipes and locked
browser harness, not a second test runner. Full data/asset boundaries remain gates.

## 007_RELEASE_REVIEW — Acceptance and remediation

Review phase: assess the actual user journey, lifecycle/data-loss risks, content
quality, architecture, and verification evidence. Resolve blocking findings,
open a ready PR, and record release status without assuming merge authorization.

## Task/gate construction rules

Every implementation sequence ends with testing, review, iterate, and fest-commit
gates. Before creating task files, expand each listed unit with exact contracts,
verified current file:line anchors, failure paths, and observable completion.
No numbered task files belong in INGEST or PLAN. Do not mark this outline as an
approved implementation plan or as completed implementation.
