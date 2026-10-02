# Input providers (D003 boundary)

Implemented by the coordinator directly on 2026-09-12 in the linked
cp0002-practice-library worktree. Uncommitted pending this sequence's
06_fest_commit gate.

## What changed

- `src/codesignal_practice_simulator/input_providers.py` (new)
  - `InputProvider` protocol: `validate(definition, filesystem)`,
    `pinned_assessment(definition)`, `declared_hash(definition, filename)`,
    `stage_file(definition, filename, destination, filesystem)`.
  - `PinnedFetchedProvider(cache)`: wraps `ValidatedFixtureCache` unchanged
    (complete seven-file validation, manifest-hash identity, `copyfile`
    staging). The File Storage digest is byte-identical to the pre-refactor
    value, asserted against a recorded fixture
    (`upstream-6aab304`, `e9cb78d1…e0e61b`).
  - `PackagedOriginalProvider(root)`: reads bundled originals under
    `<root>/<input directory>/` with a `content-manifest.json`
    (`assessment-package/v1`: `assessment_id`, slug `content_version`,
    SHA-256 per candidate-facing file). Validation requires exactly the
    candidate-facing files plus the manifest (any other file, such as a
    solution, fails), verifies every byte against the manifest, and computes
    identity with the same canonical `assessment-content/v1` digest input.
    Staging reads through the injected filesystem so failure injection and
    staged-byte re-verification apply. `installed()` locates the package's
    `resources` directory and fails closed if resources are not files.
  - `InputProviders`: kind → provider map; unknown kinds fail closed with a
    fixture-setup error; `default(cache)` = fetched provider plus installed
    originals when present.
- `assessments.py`: `provider_kind` (`pinned-fetched` | `packaged-original`,
  validated) and `description` on `AssessmentDefinition`; `cache_directory`
  segments validated; `AssessmentRegistry.definitions()`; duplicate input
  directories rejected alongside duplicate IDs.
- `workspace.py`: `providers` injection; `pinned_assessment`,
  `_validate_creation_state`, `_definition_for_pinned_session`,
  `_populate_staging` and `_verify_staged_inputs` go through the definition's
  provider; new `validate_inputs(definition)` replaces the whole-cache
  validation in `create_attempt` and `restart_attempt` (only the selected
  definition's inputs are validated, before any staging or commit intent).
- `application.py`: `registry` and `providers` injection; `_start_locked`
  validates through the workspace and adds the fetch remedy only for fetched
  content.
- `tests/test_cli.py`: the runtime helper injects the synthetic cache at
  construction (providers are built there) instead of swapping the attribute.
- `docs/cli-contract.md`: "Input providers" section.

## Deliberate decisions

- The packaged directory must contain exactly the allowlisted files plus the
  manifest: the simplest enforceable guarantee that development solutions or
  notes never reach an attempt (D003 "do not accidentally ship development
  solutions").
- No original is bundled yet (that is 004/02); the default provider set
  therefore serves fetched content and fails closed for a packaged definition,
  which is tested.
- Restart validates the replacement's inputs before touching the old attempt,
  so a tampered package cannot abandon live work.

## Negative cases proven (tests/test_input_providers.py, 11 tests)

- File Storage identity equals the recorded pre-refactor digest through the
  provider, the cache, and the workspace; legacy creation still copies six
  files from the cache and verifies them; a missing or tampered cache is still
  rejected before any attempt exists.
- Original starts offline with a never-fetched cache; staged bytes equal the
  package; manifest is not staged; status/test/restart work on it.
- Eleven package faults (tampered file, tampered manifest hash, missing
  prompt, shipped solution, stray note, wrong assessment, bad version, wrong
  schema, incomplete file list, missing manifest, unreadable manifest) each
  fail before `attempts/` exists, and File Storage is unaffected.
- Package changed between validation and staging: staged-byte check aborts,
  no attempt or staging residue, no pointer.
- Tampered package blocks restart before the old attempt is touched.
- Invalid profile/mode, unknown provider kind, provider kind mismatch, invalid
  definition kind, duplicate input directories.
- Definition removed later: status blocks with `AssessmentVersionUnavailableError`,
  review and history still show the stored result; a newer package version
  leaves the old attempt reviewable and starts fresh on the new version.
- Application: fetch remedy only for fetched content; originals start offline;
  default providers without bundled originals fail closed.

## Evidence

    python3 -m unittest tests.test_input_providers   11 tests OK
    just check unit                                  436 tests OK (1 skipped)
    python3 -m unittest tests.test_documentation     OK
    git diff --check                                 clean

Browser and frontend suites unchanged by this task; they run at the sequence
testing gate.
