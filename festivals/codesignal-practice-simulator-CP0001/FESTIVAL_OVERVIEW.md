# Festival Overview: codesignal-practice-simulator

## Problem Statement

**Current State:** The exploration directory contains a valuable but
single-assessment `file_storage` practice harness: `new_attempt.py` copies an
assessment and starts a 90-minute clock, and `scorecard.py` runs each bundled
test group independently. Its legacy `attempts/<timestamp>[_<name>]/attempt.json` is static, its JSON score is
ephemeral, `submit` does not finalize a lifecycle, and there is no unified
resume/status/context interface, append-only history, agent boundary, or
harness end-to-end coverage. The material is not yet a durable private
repository or a JobSearch project submodule.

**Desired State:** A private, provenance-aware Python project provides a
reusable local Industry Coding Framework simulator. Full sessions retain an
authentic 90-minute deadline; drill sessions use an explicitly recorded
accelerated profile. Each session owns copies from a validated ignored local
fixture cache, candidate code, validated state, JSONL events, derived status/context, and a
non-executable coaching surface. A stable CLI supports the approved lifecycle
and testable partial-credit scoring.

**Why This Matters:** The candidate can practice assessment pacing repeatedly
instead of spending preparation time rebuilding tools, and can recover an
interrupted session with evidence rather than guessing its clock or score.
Explicit separation of fixtures, candidate code, reference solutions, and
coaching preserves the learning value and prevents accidental answer leakage
during a live drill. The campaign gains a stable, private project rather than
an unintegrated exploration artifact.

## Scope

### In Scope

- Create, later in implementation, the approved private GitHub repository and
  register it as `projects/codesignal-practice-simulator` in the JobSearch
  campaign.
- Migrate only non-verbatim user-authored simulator, study, notes, scripts,
  and solution material, including the current explore README at
  `docs/legacy/explore-README.md`; the root README is newly authored. Store
  upstream URL, commit, paths, and checksums but never vendor content; exclude
  `assessment/vendor-readme.md`,
  `assessment/file_storage/**`, verbatim `solution/test_simulation.py`,
  upstream requirements, every other exact upstream file, generated
  environments, caches, and user attempts.
- Provide one pinned seven-record fetch/setup set into a Git-ignored cache:
  upstream `README.md` → `vendor-readme.md` and six
  `practice_assessments/file_storage/` files → `assessment/file_storage/`;
  validate every SHA-256, fail closed, and use a complete local `--source`
  injection seam for offline and clean-clone tests.
- Enforce the vendor boundary with pre-commit/pre-push hooks that scan every
  staged and `HEAD` blob hash plus forbidden vendor paths.
- Build full/drill attempt creation with atomic rollback under injected
  filesystem faults, lifecycle state, append-only events, isolated workspaces,
  sanitized partial-credit subprocess execution, and the approved CLI.
- Add `STATUS.md`, Markdown/JSON context, `COACHING.md`, and `AGENTS.md` with
  an explicit candidate-solution safety boundary.
- Test migration fidelity, state behavior, command behavior, and complete
  full/drill lifecycles; review privacy, provenance, usability, and campaign
  integration.

### Out of Scope

- Creating the external repository, copying/moving the exploration source, or
  changing product source during this planning run.
- Implementing a hosted CodeSignal service, remote proctoring, authentication,
  collaboration server, hidden-test service, or automatic CodeSignal
  submission.
- Claiming that a local CLI can technically prevent a privileged terminal
  agent from editing candidate files; this festival provides an operational
  safety boundary and auditable behavior instead.
- Expanding the first release beyond the `file_storage` fixture; registry
  seams may support later assessments but do not require additional content.

## Planned Phases

### 001_INGEST — Source and Requirement Ingest

Capture the approved objective, source inventory, regression anchors,
provenance constraints, campaign conventions, and prioritized requirements in
structured specifications that implementation workers can follow without
reinterpreting the request.

### 002_PLAN — Architecture and Execution Design

Turn the specifications into decisions, a dependency-aware phase/sequence/task
structure, command and schema contracts, review criteria, and customized
quality gates.

### 003_BOOTSTRAP_MIGRATE through 007_REVIEW_RELEASE

Execute the verified private-repository migration, durable session runtime,
CLI workflows, automated verification, and final quality/provenance/release
review. These phases are scaffolded during planning and executed only after
this planning run.

## Notes

The existing source's Level-4 visible test contradicts its written rollback
specification. The simulator must preserve fixture compatibility while keeping
the spec-correct reference/test mode visible and documented. The selected
implementation baseline is Python 3.10+ and the standard library; the
upstream repository has `licenseInfo: null` and its `/license` endpoint is 404
at `6aab304`, so the decision is FETCH_ONLY. The full scope and five delivery/review phases are approved, so
the normal planning approval checkpoint is recorded as satisfied.
