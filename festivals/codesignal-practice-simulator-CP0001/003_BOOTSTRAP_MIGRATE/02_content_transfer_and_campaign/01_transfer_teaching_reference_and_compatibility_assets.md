---
fest_type: task
fest_id: 01_transfer_teaching_reference_and_compatibility_assets.md
fest_name: transfer_teaching_reference_and_compatibility_assets
fest_parent: 02_content_transfer_and_campaign
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-08T16:23:47.552521-06:00
fest_updated: 2026-09-08T19:07:15.428261-06:00
fest_tracking: true
fest_dependencies:
  - ../01_repository_and_provenance/07_fest_commit
---


# Task: 003.02.01 — Transfer Teaching, Reference, and Compatibility Assets

## Objective

Copy only approved non-verbatim user-authored content and capture
fetch-only-compatible evidence.

## File anchors

Inputs are manifest records and source paths. Only records classified
user-authored and non-verbatim have destinations; the current user-authored
explore `README.md` maps to `docs/legacy/explore-README.md`. Exact
upstream/vendor records—including upstream `README.md` represented locally as
`assessment/vendor-readme.md`, requirements, fixture paths, and explicitly
excluded verbatim `solution/test_simulation.py`—have null destinations and are
not copied. Evidence is this task’s
`results/01_transfer_teaching_reference_and_compatibility_assets.md`.

## Ordered implementation steps

1. Copy each included user-authored file to its declared destination; do not
   infer a destination or copy an excluded record.
2. Author the root README to explain the no-license FETCH_ONLY boundary,
   setup command, ignored cache, and post-attempt learning material.
3. Adapt only user-authored compatibility scripts and optional Just recipes.
4. Verify all tracked included mappings with `--scope tracked` and enforce
   `--scope git-boundary`. Use a temporary local source fixture or mocked
   downloader that supplies all seven declared upstream paths, including
   `README.md` for cache `vendor-readme.md`, to populate and verify
   `--scope fixture-cache`; never install or track upstream requirements.
5. Commit and push every transferred user-authored project file to `main`;
   mechanically verify local `HEAD` equals `refs/remotes/origin/main` before
   003.02.02 may create the campaign gitlink.
6. Record commands, exit codes, the mapped legacy-README result, remote SHA
   equality, and the Level-4 compatibility/spec distinction in the evidence
   file. On successful push, emit exactly one line for each of
   `transfer_commit_sha: <40-lowercase-hex-SHA>`,
   `transfer_remote_main_sha: <same-SHA>`, and
   `transfer_remote_equality: PASS`; these lines are the only transfer-commit
   evidence that 003.02.02 accepts.

## Error paths

A missing mapping, checksum failure, copied vendor record, or failed cache
validation blocks transfer. Record it; do not alter the cache or track vendor
files merely to turn evidence green.

## Do-not-mutate boundaries

Do not alter SOURCE, the validated local cache, candidate attempts, remote
visibility, `.gitmodules`, or unrelated campaign changes.

## Verification and evidence

Run from the directory named in the commands. Save complete output and exit codes to `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/003_BOOTSTRAP_MIGRATE/02_content_transfer_and_campaign/results/01_transfer_teaching_reference_and_compatibility_assets.md`; a nonzero exit is blocking unless stated below.

```sh
PROJECT="/workspace/campaign/projects/codesignal-practice-simulator"
EVIDENCE="/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/003_BOOTSTRAP_MIGRATE/02_content_transfer_and_campaign/results/01_transfer_teaching_reference_and_compatibility_assets.md"
SOURCE="/workspace/campaign/workflow/explore/codesignal-industry-coding-framework"
RUN_DIR="$(mktemp -d)"
trap 'rm -rf -- "$RUN_DIR"' EXIT HUP INT TERM
FIXTURE_SOURCE="$RUN_DIR/upstream-fixture"
mkdir -p "$FIXTURE_SOURCE/practice_assessments/file_storage"
cp "$SOURCE/assessment/vendor-readme.md" "$FIXTURE_SOURCE/README.md"
cp -R "$SOURCE/assessment/file_storage/." "$FIXTURE_SOURCE/practice_assessments/file_storage/"
mkdir -p "$(dirname "$EVIDENCE")"
set -e
set -o pipefail
{
cd "$PROJECT"
python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope tracked
python3 scripts/fetch_fixture.py --manifest docs/migration-manifest.json --source "$FIXTURE_SOURCE"
python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope fixture-cache
python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary
python3 solution/test_spec.py
python3 solution/test_stages.py
python3 study/check.py 4 solution/simulation.py
git add -- docs/legacy solution study notes scripts justfile justfiles README.md
git commit -m "feat: migrate user-authored practice materials"
git push origin main
TRANSFER_COMMIT_SHA="$(git rev-parse HEAD)"
TRANSFER_REMOTE_MAIN_SHA="$(git rev-parse refs/remotes/origin/main)"
test "$TRANSFER_COMMIT_SHA" = "$TRANSFER_REMOTE_MAIN_SHA"
printf 'transfer_commit_sha: %s\n' "$TRANSFER_COMMIT_SHA"
printf 'transfer_remote_main_sha: %s\n' "$TRANSFER_REMOTE_MAIN_SHA"
printf '%s\n' 'transfer_remote_equality: PASS'
git diff --check
git status --short
} 2>&1 | tee "$EVIDENCE"
```

Expected result: the commands produce the stated success output and `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/003_BOOTSTRAP_MIGRATE/02_content_transfer_and_campaign/results/01_transfer_teaching_reference_and_compatibility_assets.md` records it.

## Definition of done

- [ ] Every approved user-authored asset is mapped and hash-verified; every
  vendor record remains null-mapped and untracked.
- [ ] The root README explains setup/fetch-only boundaries.
- [ ] Cache, Git-boundary, and user-authored compatibility checks have
  recorded outcomes; every declared fetch record was materialized.
- [ ] All transferred user-authored project content is committed and pushed to
  `main`, with local `HEAD` equal to the verified remote SHA and exactly one
  successful machine-readable transfer-SHA/equality record.
- [ ] Cache, SOURCE, attempts, and campaign integration are unchanged.
