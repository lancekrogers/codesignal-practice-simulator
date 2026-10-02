# D003 — Versioned catalog with separate validated input providers

Status: proposed for plan approval. Resolves G5; R1/R2/R8/R11.
Anchors: assessments.py:56/:88, application.py:174/:343,
workspace.py:116/:329, scoring.py:241 (under src/codesignal_practice_simulator/).

## Choice

Keep the existing registry and isolated scorer; extend definitions with stable ID,
content version, digest, description, four-level metadata, profiles, and input
provider kind. Version/digest identify prompts, starter, tests, and runner contract,
not merely a display title. Attempts pin that identity at creation.

Two narrow validated input providers:
- pinned-fetched: existing File Storage cache/provenance validation unchanged;
- packaged-original: bundled original assessment resources and declared hashes,
  readable from installed packages, validated before staging an attempt.

The provider supplies only allowlisted candidate-facing files and the compatible
runner inputs. Resolve the selected provider before validation: original exercises
must work without fetching File Storage. Never bypass validation merely because
an assessment is “built in.” Detect missing resources, tampering and incompatible
versions before any new attempt or abandonment commit intent.

Rejected: putting all content into the legacy fetch manifest, browser-authored
test scripts, arbitrary user paths as registered content, or one global fetch
requirement for unrelated original exercises.

## Version and compatibility

Catalog enumeration is read-only and lists installed definitions with availability
and explicit setup reasons. File Storage can be visible but needs fetch; originals
are available offline. Existing v1 File Storage records use legacy metadata for
review and a known legacy identity adapter for allowed operations; never rewrite
old metadata to today's version. Definition removal must not hide old results.

A retry uses the current installed version by default, clearly labeled if it
differs from the prior attempt. Continuing/scoring an existing active attempt
requires its pinned compatible inputs, not silent replacement with current tests.

## Content package

Each exercise has four original progressive prompt files, deterministic starter,
four-group checks, and machine-readable content metadata. Preserve the established
simulation.py/test_simulation.py convention initially and extend the common runner
only where demonstrated necessary. Include resources in wheel/sdist allowlists;
do not accidentally ship development solutions or unrelated fixtures.

The current runner loads
test_simulation.TestSimulateCodingFramework.test_group_1 through test_group_4
(scoring.py:193). Original checks must implement that exact entry-point contract
initially, not merely reuse the filenames. Validate all four methods at build/test
time. This avoids broadening dynamic import targets or changing legacy scoring.

Content correctness tests include a first-party development oracle, deliberate
incomplete/wrong implementations, progression and boundary cases. Development
solutions are not candidate-distributed resources. Scoring tests must prove a
correct level implementation passes that level and incorrect ones are rejected.

## Amendment 2026-09-11 (execution): File Storage identity moved earlier

003/01/02_creation_identity delivers the File Storage (pinned-fetched) identity
before submission capture and restart need it: content_version
`upstream-<manifest commit>`; content_digest = SHA-256 of canonical JSON
`assessment-content/v1` {assessment_id, content_version, runner_contract, sorted
copied-file paths with declared manifest hashes}. The packaged manifest supplies
the hashes, so identity does not depend on the cache being present. Staged copies
are re-hashed before publish. The same task activates session/v2 creation and
keeps the v1 legacy identity adapter. 004/01 generalizes this into the provider
interface without changing the File Storage digest and adds packaged originals.

## Acceptance

Install a wheel outside the checkout with network disabled and no legacy cache.
Discover and complete each original exercise. Fetch-dependent File Storage remains
explicitly unavailable until setup; originals still run. Reject wrong digests,
duplicate IDs/versions, unsupported profiles, missing files, and traversal.
Rebuild twice and compare resource manifests; old review remains readable when
a catalog version disappears.
