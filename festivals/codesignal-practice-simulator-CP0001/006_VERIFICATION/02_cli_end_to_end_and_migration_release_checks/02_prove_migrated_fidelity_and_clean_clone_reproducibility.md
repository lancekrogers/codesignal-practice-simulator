---
fest_type: task
fest_id: 02_prove_migrated_fidelity_and_clean_clone_reproducibility.md
fest_name: prove_migrated_fidelity_and_clean_clone_reproducibility
fest_parent: 02_cli_end_to_end_and_migration_release_checks
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-08T16:23:47.673066-06:00
fest_tracking: true
---

# Task: 006.02.02 — Prove Migrated Fidelity and Clean-Clone Reproducibility

## Objective

Create one reproducible verification route for safe migration fidelity,
fetch-only setup, clean project clones, and clean campaign submodules.

## File anchors

Existing anchors are the manifest/provenance, fetch/verify scripts,
user-authored solution/study content, migration tests, optional Just recipe,
campaign `.gitmodules`, and project remote. Create/update the lawful
verification runner, migration tests, optional recipe, and optional CI.

## Ordered implementation steps

1. Implement `scripts/run_legacy_checks.py` as the canonical direct-Python
   local sequence: tracked-mapping verification, cache-hash verification,
   lawful user-authored suites, and explicit study checker. Print setup
   guidance for an absent/invalid cache; do not execute tracked upstream tests.
2. Make `just verify` invoke that sequence plus the complete test suite only
   as an optional compatibility recipe. Add CI only if private-repository CI
   is enabled; it must call the same direct Python command on Python 3.10.
3. Allocate a per-run temporary directory. Clone PROJECT, install it, and run
   offline setup against a temporary local source fixture or mocked downloader
   that materializes all seven manifest records: upstream `README.md` to cache
   `vendor-readme.md` and all six `practice_assessments/file_storage/` paths.
   Verify every cache record before canonical verification. Never copy that
   fixture into the clone's Git tree.
4. Clone CAMPAIGN separately, initialize recursively, install its submodule,
   exercise the same complete temporary setup seam, and run the same
   verification route. Confirm repository visibility is PRIVATE.
5. Record clone commands, outputs, all seven cache hashes, compatibility
   profile, and all setup prerequisites.

## Error paths

Missing setup/cache must produce actionable guidance; it is not a core
simulator success. Hash mismatch, tracked vendor byte, public visibility,
clean-clone/submodule failure, prior-clone dependency, or CI-only dependency
blocks release.

## Do-not-mutate boundaries

Do not change cache bytes, hide network-dependent tests, track vendor bytes,
delete SOURCE, or modify unrelated CAMPAIGN state.

## Verification and evidence

Run from the directory named in the commands. Save complete output and exit codes to `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/006_VERIFICATION/02_cli_end_to_end_and_migration_release_checks/results/02_prove_migrated_fidelity_and_clean_clone_reproducibility.md`; a nonzero exit is blocking unless stated below.

```sh
PROJECT="/workspace/campaign/projects/codesignal-practice-simulator"
CAMPAIGN="/workspace/campaign"
SOURCE="/workspace/campaign/workflow/explore/codesignal-industry-coding-framework"
EVIDENCE="/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/006_VERIFICATION/02_cli_end_to_end_and_migration_release_checks/results/02_prove_migrated_fidelity_and_clean_clone_reproducibility.md"
mkdir -p "$(dirname "$EVIDENCE")"
set -e
set -o pipefail
RUN_DIR="$(mktemp -d)"
trap 'rm -rf -- "$RUN_DIR"' EXIT HUP INT TERM
PROJECT_CLONE="$RUN_DIR/project"
CAMPAIGN_CLONE="$RUN_DIR/campaign"
FIXTURE_SOURCE="$RUN_DIR/fixture-source"
run_verification() {
    (
        cd "$1"
        python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope tracked
        python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope fixture-cache
        python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary
        python3 scripts/run_legacy_checks.py
        python3 -m unittest discover -s tests -v
        git diff --check
        git status --short
    )
}
{
git clone --no-local "$PROJECT" "$PROJECT_CLONE"
python3 -m pip install -e "$PROJECT_CLONE"
mkdir -p "$FIXTURE_SOURCE/practice_assessments/file_storage"
cp "$SOURCE/assessment/vendor-readme.md" "$FIXTURE_SOURCE/README.md"
cp -R "$SOURCE/assessment/file_storage/." "$FIXTURE_SOURCE/practice_assessments/file_storage/"
(cd "$PROJECT_CLONE" && python3 scripts/fetch_fixture.py --manifest docs/migration-manifest.json --source "$FIXTURE_SOURCE")
run_verification "$PROJECT_CLONE"
gh repo view lancekrogers/codesignal-practice-simulator --json visibility --jq .visibility | grep -qx PRIVATE
git clone --no-local "$CAMPAIGN" "$CAMPAIGN_CLONE"
git -C "$CAMPAIGN_CLONE" submodule update --init --recursive
SUBMODULE_CLONE="$CAMPAIGN_CLONE/projects/codesignal-practice-simulator"
test -e "$SUBMODULE_CLONE/.git"
python3 -m pip install -e "$SUBMODULE_CLONE"
(cd "$SUBMODULE_CLONE" && python3 scripts/fetch_fixture.py --manifest docs/migration-manifest.json --source "$FIXTURE_SOURCE")
run_verification "$SUBMODULE_CLONE"
# Optional compatibility check; it is not a clean-clone prerequisite or
# authoritative verification route.
if command -v just >/dev/null 2>&1; then
    (cd "$SUBMODULE_CLONE" && just verify)
fi
} 2>&1 | tee "$EVIDENCE"
```

Expected result: the commands produce the stated success output and `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/006_VERIFICATION/02_cli_end_to_end_and_migration_release_checks/results/02_prove_migrated_fidelity_and_clean_clone_reproducibility.md` records it.

## Definition of done

- [x] Canonical verification separately checks tracked mappings and cache
  hashes for every declared fetch record, plus the staged/HEAD Git boundary;
  Just is optional compatibility coverage.
- [x] Fresh project and campaign clones exercise fetch/setup from a temporary
  local source or mocked downloader that includes `vendor-readme.md` and
  reproduce all direct-Python evidence.
- [x] This task creates and cleans up its own per-run project and campaign clones.
- [x] Visibility proof reports PRIVATE.
- [x] No CI-only/developer-only condition, tracked vendor byte, or unapproved
  source/cache change remains.
