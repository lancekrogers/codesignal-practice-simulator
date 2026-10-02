---
fest_type: task
fest_id: 02_integrate_proven_project_into_campaign.md
fest_name: integrate_proven_project_into_campaign
fest_parent: 02_content_transfer_and_campaign
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-08T16:23:47.552878-06:00
fest_updated: 2026-09-08T19:10:19.202135-06:00
fest_tracking: true
---


# Task: 003.02.02 — Integrate the Proven Project into the Campaign

## Objective

After the transfer task has committed and pushed all user-authored project
content and clean-clone evidence passes, add only the approved private project
submodule to the campaign.

## File anchors

Existing anchors: `/workspace/campaign/projects/codesignal-practice-simulator` and its private GitHub remote, campaign-root `CAMPAIGN/.gitmodules`, `CAMPAIGN/projects/`, and this sequence’s prior evidence. `SOURCE/.workitem` is excluded source-local campaign metadata, not a project or migration anchor. Future campaign anchors: `/workspace/campaign/.gitmodules` and `/workspace/campaign/projects/codesignal-practice-simulator` gitlink. Evidence is this task’s `results/02_integrate_proven_project_into_campaign.md`.

## Ordered implementation steps

1. Before any campaign mutation, mechanically parse the prior transfer
   evidence. Require exactly one valid 40-character `transfer_commit_sha`, one
   matching `transfer_remote_main_sha`, and
   `transfer_remote_equality: PASS`; require that SHA to equal both
   `PROJECT/HEAD` and `refs/remotes/origin/main`. A scaffold-only, malformed,
   duplicate, or unpushed SHA is blocking. Allocate one per-run temporary
   directory with `mktemp -d` and an
   EXIT/HUP/INT/TERM trap that removes only that directory. Clone PROJECT below
   it, install the package, construct a temporary local fixture source (or use
   the mocked downloader test seam), run fetch/setup and direct Python
   verification commands. Confirm GitHub visibility; it must be PRIVATE.
2. Confirm PROJECT `HEAD` is the transfer-content commit published at
   `origin/main`. Snapshot `git -C CAMPAIGN status --porcelain=v1` before
   making changes; unrelated pre-existing unstaged state is baseline evidence,
   not a reason to reset/clean the campaign. Require that CAMPAIGN has no
   pre-existing staged paths, then add the approved SSH remote as the
   submodule exactly at `projects/codesignal-practice-simulator`. Inspect only
   the staged `.gitmodules` and gitlink.
3. From this task directory, use `fest commit --stage=false` to create the campaign-root integration commit. Before cloning, mechanically confirm its tree contains both `.gitmodules` and `projects/codesignal-practice-simulator`; retain the resulting campaign commit SHA as the expected submodule pointer.
4. Only after that campaign-root commit exists, clone CAMPAIGN below the per-run temporary directory, initialize recursively, and prove the cloned submodule `HEAD` equals the gitlink recorded by the committed campaign tree. Install the cloned submodule and execute the smoke command.
5. As the sole campaign-disposition owner, record in this task's integration
   evidence that `SOURCE/.workitem` with
   `id: explore-codesignal-industry-coding-framework-2026-09-08` and
   `ref: WI-117ed7` is `retained`, together with the durable path
   `projects/codesignal-practice-simulator`. Do not copy, edit, or remove that
   source-local metadata. The JobSearch campaign maintainer owns any future
   schema-valid retirement/update through a separately authorized
   campaign-maintenance action.
6. Keep SOURCE available; it is never deleted by this task.

## Error paths

If privacy is not PRIVATE, PROJECT is not synchronized to its published commit, a pre-existing staged campaign path is present, the campaign-root commit lacks either integration path, clone/submodule initialization fails, or the checked-out submodule does not match the committed gitlink, unstage/revert only the new `.gitmodules` and gitlink changes and stop. Never delete SOURCE as recovery or reset/clean pre-existing campaign state.

## Do-not-mutate boundaries

Do not modify unrelated CAMPAIGN files, existing submodules, cached fixture files,
candidate attempts, or any SOURCE content, including `.workitem`. Do not use
`git reset --hard`, `git clean`, or cleanup commands against campaign work.

## Verification and evidence

Run from the directory named in the commands. Save complete output and exit codes to `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/003_BOOTSTRAP_MIGRATE/02_content_transfer_and_campaign/results/02_integrate_proven_project_into_campaign.md`; a nonzero exit is blocking unless stated below.

```sh
CAMPAIGN="/workspace/campaign"
PROJECT="/workspace/campaign/projects/codesignal-practice-simulator"
SOURCE="/workspace/campaign/workflow/explore/codesignal-industry-coding-framework"
TASK_DIR="/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/003_BOOTSTRAP_MIGRATE/02_content_transfer_and_campaign"
EVIDENCE="/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/003_BOOTSTRAP_MIGRATE/02_content_transfer_and_campaign/results/02_integrate_proven_project_into_campaign.md"
mkdir -p "$(dirname "$EVIDENCE")"
set -e
set -o pipefail
RUN_DIR="$(mktemp -d)"
trap 'rm -rf -- "$RUN_DIR"' EXIT HUP INT TERM
PROJECT_CLONE="$RUN_DIR/project"
CAMPAIGN_CLONE="$RUN_DIR/campaign"
FIXTURE_SOURCE="$RUN_DIR/fixture-source"
CAMPAIGN_STATUS_BEFORE="$RUN_DIR/campaign-status-before.txt"
TRANSFER_EVIDENCE="$TASK_DIR/results/01_transfer_teaching_reference_and_compatibility_assets.md"
{
gh repo view lancekrogers/codesignal-practice-simulator --json visibility --jq .visibility | grep -qx PRIVATE
TRANSFER_COMMIT_SHA="$(python3 - "$TRANSFER_EVIDENCE" <<'PY'
import re
import sys
from pathlib import Path

required = {
    "transfer_commit_sha",
    "transfer_remote_main_sha",
    "transfer_remote_equality",
}
records = {}
for line in Path(sys.argv[1]).read_text().splitlines():
    key, separator, value = line.partition(": ")
    if key in required:
        if not separator or key in records:
            raise SystemExit(f"invalid duplicate transfer evidence field: {key}")
        records[key] = value
if set(records) != required:
    raise SystemExit("incomplete transfer evidence")
sha = records["transfer_commit_sha"]
if not re.fullmatch(r"[0-9a-f]{40}", sha):
    raise SystemExit("invalid transfer commit SHA")
if records["transfer_remote_main_sha"] != sha:
    raise SystemExit("transfer evidence remote SHA mismatch")
if records["transfer_remote_equality"] != "PASS":
    raise SystemExit("transfer evidence did not record remote equality")
print(sha)
PY
)"
test "$TRANSFER_COMMIT_SHA" = "$(git -C "$PROJECT" rev-parse HEAD)"
test "$TRANSFER_COMMIT_SHA" = "$(git -C "$PROJECT" rev-parse refs/remotes/origin/main)"
git clone --no-local "$PROJECT" "$PROJECT_CLONE"
python3 -m pip install -e "$PROJECT_CLONE"
mkdir -p "$FIXTURE_SOURCE/practice_assessments/file_storage"
cp "$SOURCE/assessment/vendor-readme.md" "$FIXTURE_SOURCE/README.md"
cp -R "$SOURCE/assessment/file_storage/." "$FIXTURE_SOURCE/practice_assessments/file_storage/"
(cd "$PROJECT_CLONE" && python3 scripts/fetch_fixture.py --manifest docs/migration-manifest.json --source "$FIXTURE_SOURCE")
(cd "$PROJECT_CLONE" && python3 -m codesignal_practice_simulator --help)
git -C "$CAMPAIGN" status --porcelain=v1 | tee "$CAMPAIGN_STATUS_BEFORE"
test -z "$(git -C "$CAMPAIGN" diff --cached --name-only)"
git -C "$CAMPAIGN" status --short
git -C "$CAMPAIGN" submodule add --name codesignal-practice-simulator git@github.com:lancekrogers/codesignal-practice-simulator.git projects/codesignal-practice-simulator
git -C "$CAMPAIGN" diff --cached --check
git -C "$CAMPAIGN" diff --cached -- .gitmodules projects/codesignal-practice-simulator
(cd "$TASK_DIR" && fest commit --stage=false -m "chore: register codesignal practice simulator submodule")
CAMPAIGN_COMMIT="$(git -C "$CAMPAIGN" rev-parse HEAD)"
git -C "$CAMPAIGN" diff-tree --no-commit-id --name-only -r "$CAMPAIGN_COMMIT" | grep -Fx .gitmodules
git -C "$CAMPAIGN" diff-tree --no-commit-id --name-only -r "$CAMPAIGN_COMMIT" | grep -Fx projects/codesignal-practice-simulator
EXPECTED_GITLINK="$(git -C "$CAMPAIGN" rev-parse "$CAMPAIGN_COMMIT:projects/codesignal-practice-simulator")"
git clone --no-local "$CAMPAIGN" "$CAMPAIGN_CLONE"
git -C "$CAMPAIGN_CLONE" submodule update --init --recursive
test "$EXPECTED_GITLINK" = "$(git -C "$CAMPAIGN_CLONE" rev-parse "HEAD:projects/codesignal-practice-simulator")"
test "$EXPECTED_GITLINK" = "$(git -C "$CAMPAIGN_CLONE/projects/codesignal-practice-simulator" rev-parse HEAD)"
python3 -m pip install -e "$CAMPAIGN_CLONE/projects/codesignal-practice-simulator"
(cd "$CAMPAIGN_CLONE/projects/codesignal-practice-simulator" && python3 scripts/fetch_fixture.py --manifest docs/migration-manifest.json --source "$FIXTURE_SOURCE")
(cd "$CAMPAIGN_CLONE/projects/codesignal-practice-simulator" && python3 -m codesignal_practice_simulator --help)
git -C "$CAMPAIGN" submodule status -- projects/codesignal-practice-simulator
git -C "$CAMPAIGN" diff --check
git -C "$CAMPAIGN" status --short
} 2>&1 | tee "$EVIDENCE"
```

Expected result: the commands produce the stated success output and `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/003_BOOTSTRAP_MIGRATE/02_content_transfer_and_campaign/results/02_integrate_proven_project_into_campaign.md` records it.

## Definition of done

- [ ] The remote visibility command emits PRIVATE.
- [ ] Fresh project and campaign clones run setup from a temporary local
  source or mocked downloader that materializes all seven fetch records,
  including `vendor-readme.md`, and pass the stated smoke checks without
  tracked vendor bytes.
- [ ] The prior transfer evidence has exactly one valid successful transfer
  SHA/equality record, and that SHA equals both local PROJECT `HEAD` and
  `origin/main` before campaign gitlink creation.
- [ ] The clean campaign clone is created only after a campaign-root commit contains `.gitmodules` and the gitlink, and its submodule `HEAD` matches that committed pointer.
- [ ] Only the intended gitlink and campaign-root `.gitmodules` changed; the
  source-local work item has a recorded campaign disposition but no mutation.
- [ ] SOURCE remains intact and its retention is recorded.
