---
fest_type: task
fest_id: 03_import_and_freeze_attributed_fixture.md
fest_name: import_and_freeze_attributed_fixture
fest_parent: 01_repository_and_provenance
fest_order: 3
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-08T16:23:47.528295-06:00
fest_updated: 2026-09-08T18:57:16.783813-06:00
fest_tracking: true
fest_dependencies:
  - 02_create_private_python_project_after_preflight
---


# Task: 003.01.03 — Implement Fetch-Only Fixture Setup and Verification

## Objective

Implement a safe, executable fixture setup path without importing or tracking
any upstream/vendor bytes.

## File anchors

Inputs are the preflight manifest and provenance draft. Create tracked
`docs/{migration-manifest.json,assessment-provenance.md}`,
`scripts/{fetch_fixture.py,verify_manifest.py}`, and
`tests/test_migration.py`. The only vendor-byte destination is the ignored
`.cache/codesignal-fixtures/6aab304/` at user runtime. The manifest declares
exactly seven fetch records: upstream `README.md` → `vendor-readme.md`, and
upstream `practice_assessments/file_storage/{level1.md,level2.md,level3.md,level4.md,simulation.py,test_simulation.py}`
→ `assessment/file_storage/{level1.md,level2.md,level3.md,level4.md,simulation.py,test_simulation.py}`.

## Ordered implementation steps

1. Copy the manifest and provenance metadata only. Document upstream URL,
   commit `6aab304`, `licenseInfo: null`, `/license` 404, `FETCH_ONLY`, cache
   location, expected paths/hashes, and the prohibition on tracked vendor bytes.
2. Implement executable `scripts/fetch_fixture.py` with standard-library
   `argparse`, `urllib`, `hashlib`, `pathlib`, and temporary/atomic operations.
   By default it fetches all seven declared files from the exact pinned raw
   GitHub URL. `--source PATH` reads an equivalent complete upstream-path tree
   for deterministic or offline tests. It validates relative paths, the
   complete set, and every hash before atomically publishing the ignored cache.
3. Fail closed: a network, path, missing-file, or hash error leaves no cache
   considered valid and exits nonzero with actionable setup guidance.
4. Implement `verify_manifest.py` with
   `--scope tracked|fixture-cache|git-boundary`. `tracked` checks included
   user-authored mappings and rejects tracked vendor paths; `fixture-cache`
   checks all seven ignored-cache files against fetch-only hashes; `git-boundary`
   computes every staged and `HEAD` blob hash and rejects any manifest-known
   vendor hash or forbidden vendor path. Both `.githooks/pre-commit` and
   `.githooks/pre-push` invoke `git-boundary`. Stage the manifest, scanner,
   tests, and hooks; then configure `git config core.hooksPath .githooks`
   before committing them, so the scanner's first enforced commit has its
   manifest available.
5. Test complete successful `--source` setup including `vendor-readme.md`,
   absent-cache setup-required behavior, incomplete local source,
   mocked-downloader failure, hash mismatch, no tracked fixture contents, and
   staged/HEAD Git-boundary hash/path rejection plus safe controls in temporary
   repositories.

## Error paths

Never fall back to unvalidated source bytes. On failure remove only the
temporary cache work area; preserve an existing valid cache and all tracked
files.

## Do-not-mutate boundaries

Never copy or add `assessment/vendor-readme.md`, `assessment/file_storage/**`,
verbatim `solution/test_simulation.py`, upstream `requirements.txt`, or another
exact upstream file to PROJECT. The fetcher may write only its ignored cache.

## Verification and evidence

```sh
PROJECT="/workspace/campaign/projects/codesignal-practice-simulator"
SOURCE="/workspace/campaign/workflow/explore/codesignal-industry-coding-framework"
RUN_DIR="$(mktemp -d)"
trap 'rm -rf -- "$RUN_DIR"' EXIT HUP INT TERM
FIXTURE_SOURCE="$RUN_DIR/upstream-fixture"
mkdir -p "$FIXTURE_SOURCE/practice_assessments/file_storage"
cp "$SOURCE/assessment/vendor-readme.md" "$FIXTURE_SOURCE/README.md"
cp -R "$SOURCE/assessment/file_storage/." "$FIXTURE_SOURCE/practice_assessments/file_storage/"
cd "$PROJECT"
set -euo pipefail
python3 scripts/fetch_fixture.py --manifest docs/migration-manifest.json --source "$FIXTURE_SOURCE"
python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope tracked
python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope fixture-cache
python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary
python3 -m unittest discover -s tests -p 'test_migration.py' -v
git add -- docs/migration-manifest.json docs/assessment-provenance.md scripts .githooks tests
git config core.hooksPath .githooks
test "$(git config --get core.hooksPath)" = .githooks
.githooks/pre-commit
git check-ignore .cache/codesignal-fixtures/6aab304/simulation.py
if git ls-files --error-unmatch assessment/file_storage/simulation.py; then
  exit 1
fi
git diff --check
```

## Definition of done

- [ ] The private repository stores provenance/hashes/paths, never vendor bytes.
- [ ] The pinned downloader and offline `--source` seam validate atomically.
- [ ] Missing or invalid setup fails closed with clear guidance.
- [ ] Tracked, cache, and staged/HEAD Git-boundary verification scopes are
  separate and covered by deterministic tests.
- [ ] Pre-commit and pre-push hooks are installed after their manifest is
  staged and enforce the Git boundary for every subsequent project commit.
