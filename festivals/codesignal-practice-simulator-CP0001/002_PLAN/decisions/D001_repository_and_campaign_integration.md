# D001: Private Repository, Provenance, and Campaign Integration

**Status:** accepted<br>
**Date:** 2026-09-08

## Context

The source is a local exploration artifact rather than a durable project. Its
README records a vendored upstream assessment from
`PaulLockett/CodeSignal_Practice_Industry_Coding_Framework` at commit
`6aab304`. The approved destination is the private GitHub repository
`lancekrogers/codesignal-practice-simulator`, used by the JobSearch campaign
at `projects/codesignal-practice-simulator`. Existing campaign projects use
Git submodules, so the integration must preserve that convention.

The upstream repository is not licensed for copying: GitHub returns
`licenseInfo: null`, and `GET /license` at commit `6aab304` returns 404.
Therefore “migrate the existing workflow” means transfer only user-authored
simulator, study, notes, scripts, and solution assets that are not
byte-for-byte upstream/vendor material. Generated virtual environments,
bytecode caches, personal attempts, and `SOURCE/.workitem` are also excluded.
A simple unverified copy would make both the ownership boundary and fixture
integrity unknowable.

## Options

### Option A: Leave the project under `workflow/explore`
- **Pros:** No migration work or external repository setup.
- **Cons:** Does not provide the approved private repository, submodule
  integration, durable project ownership, or clear separation of exploration
  from reusable tooling.

### Option B: Create a private standalone repository, verify the transfer, then add it as a campaign submodule
- **Pros:** Matches the approved name/destination; permits focused project
  history; follows existing campaign conventions; supports a migration manifest
  and clean-clone verification.
- **Cons:** Requires careful provenance review, source inventory, submodule
  registration, and staged retirement of the exploration directory.

### Option C: Copy the source into the superproject without a submodule
- **Pros:** One checkout and no submodule initialization.
- **Cons:** Conflicts with the `projects/` convention, conflates campaign and
  product history, and fails the approved repository destination.

## Decision

Choose Option B. During implementation, first inventory and compare source
files with the pinned upstream snapshot. The tracked manifest records each
path, checksum, classification, and upstream provenance. Only non-verbatim,
user-authored records have normalized, unique project destinations. The
current user-authored explore `README.md` is included at
`docs/legacy/explore-README.md`; the root product README remains separately
authored. Exact upstream/vendor records—including upstream `README.md`
represented locally as `assessment/vendor-readme.md`,
`assessment/file_storage/**`, verbatim `solution/test_simulation.py`, upstream
`requirements.txt`, and every other exact upstream match—are `exclude` with
null destinations.
Then create the approved private remote, prove it with `gh repo view lancekrogers/codesignal-practice-simulator --json visibility` returning `PRIVATE`, initialize the destination repository,
and copy the verified source boundaries. Only after the new repository passes
legacy regression tests and a clean clone check may the JobSearch superproject
add its submodule entry and update the exploration work-item references.

The migration is ordered as a reversible preflight: classify the source tree,
record the include/exclude manifest and checksums, record the license finding,
and prepare local validation commands. Its separate preflight record has
exactly one final PASS/BLOCKED decision, and PASS requires
`license decision: FETCH_ONLY`, null destinations for vendor records, and safe
mappings for user-authored records. A retry archives a BLOCKED record without
changing it, resets 003.01.01, and creates fresh canonical evidence.
Only then may execution create the private remote and destination repository.
The project tracks a standard-library fetch script and provenance manifest,
not vendor bytes. The manifest declares one seven-record fetch set: upstream
`README.md` → cache `vendor-readme.md`, plus upstream
`practice_assessments/file_storage/{level1.md,level2.md,level3.md,level4.md,simulation.py,test_simulation.py}`
→ matching cache `assessment/file_storage/` paths, all under
`.cache/codesignal-fixtures/6aab304/`. At user runtime the script downloads or
offline-materializes every declared record, checks every SHA-256, and fails
closed. Attempts copy only the six validated assessment inputs. Every
clean-clone validation materializes this whole set, including
`vendor-readme.md`, from a temporary local source or mocked downloader.
The superproject is the final integration step.

`SOURCE/.workitem` is excluded from the project manifest with a null
destination and is never copied into the destination repository. 003.02.02 is
the sole owner of its campaign disposition after the committed campaign clone
passes: it records the existing work-item ID/ref, source path, durable project
path, and the decided `retained` outcome in campaign-integration evidence.
It does not edit the source-local `.workitem` in place or invent fields in its
schema. The JobSearch campaign maintainer owns any future retirement/update
through a separately authorized campaign-maintenance action, never the project
migration.
The old exploration directory is neither deleted nor repurposed until the
transfer and submodule checks pass.

## Consequences

- The implementation task must not use destructive cleanup or alter unrelated
  superproject changes.
- `.venv/`, caches, and runtime attempts stay excluded. The manifest lists
  included user-authored mappings and hashes, plus excluded fetch-only vendor
  paths/hashes with null destinations. `SOURCE/.workitem` is also excluded.
- Root README and provenance explain the no-license FETCH_ONLY boundary.
- `.githooks/pre-commit` and `.githooks/pre-push` invoke a manifest-driven
  scanner after 003.01.03 stages the manifest and configures
  `core.hooksPath=.githooks`. It computes every staged-index and `HEAD` blob
  hash and rejects a known vendor hash or a forbidden vendor path; tests use
  temporary repositories to prove both scopes.
- The assessment is never imported or tracked. It is a validated local cache
  at runtime, so no permission to privately copy it is assumed or required.
- The submodule and private remote require clean-clone and `git submodule`
  initialization checks in the final review; a remote URL is never accepted as
  private-visibility proof.
- Bootstrap commits the scaffold, renames and pushes `main` with upstream
  tracking, then proves that the remote's default branch can be freshly cloned
  before the campaign is changed. Content transfer subsequently commits and
  pushes all included user-authored content to `main`, verifies local `HEAD`
  equals `origin/main`, and only then permits campaign gitlink creation.
- Planning creates no remote, changes no submodule, and copies no source; all
  external and filesystem migration actions belong to the approved execution
  phase after preflight evidence exists.
