# Implementation Plan: CodeSignal Practice Simulator

**Planning scope:** This document defines the execution work. It does not
create a GitHub repository or remote, copy/move the source tree, modify product
code, add a submodule, or change existing campaign work.

The factual operator approval record is
[`../inputs/operator_approval.md`](../inputs/operator_approval.md). It records
approval of the private repository, campaign destination, full migration scope,
and five-phase plan, along with the completion directive, checkpoint
delegation, and incorporation of subsequent judge-feedback remediation passes.

## Execution Coordinates

| Symbol | Exact path |
| --- | --- |
| `SOURCE` | `/workspace/campaign/workflow/explore/codesignal-industry-coding-framework` |
| `PROJECT` | `/workspace/campaign/projects/codesignal-practice-simulator` |
| `CAMPAIGN` | `/workspace/campaign` |
| `FESTIVAL` | `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001` |

`PROJECT` does not exist during planning. It may be created only by
003.01.02 after 003.01.01 has recorded passing preflight evidence. All paths
below are relative to the named coordinate unless stated otherwise.

## Contracts Established Before Implementation

### Ownership and fetch-only boundary

- GitHub reports `licenseInfo: null` and `GET /license` returns 404 for
  `PaulLockett/CodeSignal_Practice_Industry_Coding_Framework` at `6aab304`.
  The mandatory decision is `FETCH_ONLY`: no exact upstream/vendor byte,
  including the local `assessment/vendor-readme.md` copy of upstream
  `README.md`, `assessment/file_storage/**`, verbatim
  `solution/test_simulation.py`, upstream `requirements.txt`, or any other
  byte-identical file, may enter Git history.
- `PROJECT/.cache/codesignal-fixtures/6aab304/**` is a Git-ignored,
  hash-validated local cache. Only `scripts/fetch_fixture.py` writes it; no
  simulator command mutates it. Attempts copy their assessment inputs only
  after cache validation succeeds.
- A candidate session may mutate only its selected
  `PROJECT/attempts/<attempt-id>/**`, excluding its structured state, event,
  lock, and generated-status files, which only the CLI owns.
- `simulation.py` in an attempt is candidate-controlled. Commands never
  rewrite it after `start`.
- `COACHING.md` is a candidate-owned non-executable collaboration surface.
  `STATUS.md` is CLI-generated; neither participates in scoring.
- `session.json`, `events.jsonl`, active pointer, and locks are CLI-owned and
  must never be manually edited. `session.json` is authoritative; Markdown is
  never parsed as state.
- Do not reset, clean, amend, or otherwise rewrite unrelated changes in
  `CAMPAIGN`. Keep commits focused and preserve the old exploration directory
  until migration and submodule evidence pass.
- `SOURCE/.workitem` is source-local campaign metadata. The manifest records
  it as `exclude` with a null destination; no project-migration task copies or
  edits it. After the committed clean-clone check, 003.02.02 owns recording its
  decided `retained` campaign disposition using its existing ID/ref. The
  JobSearch campaign maintainer owns any future source-local metadata edit or
  removal through a separately authorized campaign-maintenance action, not a
  permitted migration mutation.
- The schema-version 2 migration manifest is the transfer contract. Every
  record has source path, byte length, SHA-256, classification, and reason.
  Included user-authored records map to normalized, unique destinations,
  including `SOURCE/README.md` → `docs/legacy/explore-README.md`; the root
  `README.md` is new product documentation. Exact vendor/upstream records are
  `exclude` with a null destination. A cache path is present only for its
  separately enumerated seven-record fetch set; every other exact
  upstream/vendor record has `cache_path: null`. The fetch set is below
  `.cache/codesignal-fixtures/6aab304/`: upstream `README.md` →
  `vendor-readme.md`, and upstream
  `practice_assessments/file_storage/{level1.md,level2.md,level3.md,level4.md,simulation.py,test_simulation.py}`
  → `assessment/file_storage/{level1.md,level2.md,level3.md,level4.md,simulation.py,test_simulation.py}`.
  The manifest records upstream URL/commit and every expected SHA-256 but no
  vendor content. Its verifier separately checks tracked included assets,
  fetched-cache hashes, and Git's staged and `HEAD` blob inventories.
- After 003.01.03 stages the manifest, it configures
  `core.hooksPath=.githooks`. Both pre-commit and pre-push call the
  manifest-driven scanner, which computes every index and `HEAD` blob hash and
  rejects every known vendor hash and forbidden vendor path. The preceding
  scaffold commit has no transferred content and occurs before the manifest.

### Planned destination layout

```text
PROJECT/
  pyproject.toml
  README.md
  docs/{cli-contract.md,assessment-provenance.md,drill-profiles.md,
        migration-manifest.json}
  src/codesignal_practice_simulator/
    __init__.py  __main__.py  cli.py  errors.py
    models.py    clock.py     persistence.py  workspace.py
    lifecycle.py assessment.py scoring.py rendering.py
  solution/{simulation.py,test_spec.py,test_stages.py,
            stages/**}
  study/{README.md,starter.py,check.py,level1.py,level2.py,level3.py,level4.py}
  notes/{walkthrough.md,level4-rollback-discrepancy.md}
  scripts/{fetch_fixture.py,verify_manifest.py,run_legacy_checks.py}
  justfile  justfiles/{practice.just,verify.just}
  tests/{test_models.py,test_persistence.py,test_workspace.py,
         test_lifecycle.py,test_scoring.py,test_rendering.py,test_cli.py,
         test_end_to_end.py,test_migration.py}
  .cache/codesignal-fixtures/       # ignored fetched vendor bytes
  attempts/                         # ignored runtime data
```

The simulator package, manifest verifier, and fetch script use Python 3.10+
standard-library components. No upstream `requirements.txt` is tracked. The
validated cached `simulation.py` is copied as the candidate starter; it is not
used as the simulator package.

### Command and error contract

The authoritative interface is `codesignal-sim` and its exact equivalent
`python -m codesignal_practice_simulator`. Commands are `start`, `resume`,
`status`, `time`, `task`, `test`, `submit`, and `context`. Every command has
human output and `--json`; all JSON responses include a version field and
either a result or a structured error.

| Exit | Meaning | Examples |
| --- | --- | --- |
| 0 | Command succeeded | status rendered; test ran; idempotent submit returned stored result |
| 2 | Invalid command input | unknown assessment, invalid duration, malformed selector |
| 3 | Session unavailable or corrupt | no active pointer, missing attempt, invalid `session.json` |
| 4 | Illegal lifecycle/concurrency action | test after expiry, resume submitted attempt, lock held |
| 5 | Candidate tests ran but one or more level groups failed | score is still persisted and reported |

`start` accepts `--mode full|drill`, `--assessment file_storage`, optional
`--workspace-root PATH`, and optional drill-duration override. Full always
persists 90 minutes. Drill defaults to named `drill-30m`, persists its 30-minute
effective duration, and never claims to be an authentic full assessment. An
explicit `--attempt ID` takes precedence over the workspace-root active pointer;
no command guesses the newest directory.

### State and scoring contract

`session.json` has a versioned schema with attempt/assessment identity, mode,
profile, duration, UTC start/deadline, lifecycle (`active`, `expired`,
`submitted`), revision, latest score, and submission metadata. Mutations take
the attempt lock, validate the current revision and legal transition, write and
flush a temporary sibling, then atomically replace `session.json`. They append
one versioned event containing event ID, revision, UTC timestamp, safe command
arguments, event name, and outcome. A following locked command writes a
recovery event if a completed state revision lacks its event. Readers reject
malformed state and non-final malformed JSONL records but ignore one incomplete
trailing JSONL record.

Scoring launches every `test_group_1` through `test_group_4` independently as
`<absolute-interpreter> -I -S <attempt>/.scoring/run_group.py <group>`, with
the selected attempt as `cwd`. The attempt-local bootstrap validates its own
location, then replaces application import paths with only the copied attempt
candidate/test directory while retaining only the interpreter's standard
library paths required to run Python; it adds no project, editable-install,
user-site, cache, solution, study, reference, or environment-derived path.
The child receives a minimal environment that omits `PYTHONPATH` and all
Python site/configuration variables. Tests prove that an installed editable
project sentinel, a hostile `PYTHONPATH` sentinel, and a loose reference
sentinel cannot import. It reports all per-level results, passed-level count,
and highest contiguous pass. A crash or failure in one group must not suppress
later groups. The fixture-compatible rollback behavior is retained for
candidates; prose-correct rollback remains a separate educational/
specification test profile.

## Phase 003 — BOOTSTRAP_MIGRATE

**Entry dependency:** 002 planning documents accepted.<br>
**Exit dependency:** a private project exists, contains verified imported
material, passes legacy verification, and is registered safely as the campaign
submodule.<br>
**Never do before preflight passes:** create the remote, publish imported
material, add a submodule, or retire `SOURCE`.

### Sequence 003.01 — repository_and_provenance

**Depends on:** 002_PLAN.<br>
**Produces:** preflight evidence, a private repository scaffold, and frozen
fixture provenance.

#### Task 003.01.01 — Inventory source and approve the migration boundary

**Sources:** `SOURCE/README.md`, `.gitignore`,
`assessment/vendor-readme.md`, `assessment/file_storage/**`,
`requirements.txt`, `scripts/**`, `solution/**`, `study/**`, `notes/**`,
`justfile`, and `justfiles/**`; `SOURCE/.workitem` is enumerated solely as
excluded source-local campaign metadata.<br>
**Destinations:** `FESTIVAL/003_BOOTSTRAP_MIGRATE/01_repository_and_provenance/results/migration-manifest.json`,
`migration-preflight.md`, and `assessment-provenance-draft.md`. `PROJECT` does
not exist during this preflight; task 003.01.03 copies the approved manifest
and provenance draft into the project after repository creation.

1. Enumerate every regular file under `SOURCE`, compare it against the pinned
   upstream commit, and classify it as included user-authored, fetch-only
   vendor, or excluded generated/metadata. Record `source_path`, byte length,
   SHA-256, classification, and reason for every record. Included
   user-authored destinations are normalized and unique. Every vendor path has
   a null destination. Only the seven exact source records in the separately
   enumerated fetch set have an expected ignored-cache path: local
   `assessment/vendor-readme.md` (the upstream `README.md`) and the six
   `assessment/file_storage/{level1.md,level2.md,level3.md,level4.md,simulation.py,test_simulation.py}`
   files. Verbatim `solution/test_simulation.py`, upstream `requirements.txt`,
   and every other exact upstream match have `cache_path: null`. Exclude
   `.venv/**`, `__pycache__/**`, `*.pyc`,
   `attempts/**`, generated `RESULT.md`/`STATUS.md`, other local practice
   outputs, and `SOURCE/.workitem` as source-local campaign metadata. The
   inventory universe is every regular file returned by
   `sorted(path for path in SOURCE.rglob('*') if path.is_file())`; preflight
   evidence and temporary siblings remain under `FESTIVAL`, outside `SOURCE`,
   so they cannot enter that universe. Classify the current
   `SOURCE/README.md` as user-authored and map it to immutable
   `PROJECT/docs/legacy/explore-README.md`, never the newly authored root
   README; do not categorically exclude files named README.
2. Require all three preflight results to be absent. Create
   `assessment-provenance-draft.md` with the upstream URL, commit `6aab304`,
   `licenseInfo: null`, the 404 license endpoint finding, mandatory
   `FETCH_ONLY` decision, expected fetch-file paths/hashes, and safe
   user-authored mappings.
   Create the manifest and preflight from complete `mktemp`-created siblings,
   trap temporary-file cleanup on failure, and atomically link each sibling
   into place without overwriting an existing record. The immutable preflight
   records deterministic included, excluded, and fixture-subset totals.
   Preserve the finding even if the license is absent or unclear.
3. Specify exactly one seven-record fetch set with expected SHA-256 values:
   upstream `README.md` → cache `vendor-readme.md`; upstream
   `practice_assessments/file_storage/{level1.md,level2.md,level3.md,level4.md,simulation.py,test_simulation.py}`
   → cache `assessment/file_storage/{level1.md,level2.md,level3.md,level4.md,simulation.py,test_simulation.py}`,
   all relative to `.cache/codesignal-fixtures/6aab304/`. Preflight validates
   the manifest without copying vendor files. Task 003.01.03 later creates the
   fetch and verifier scripts; the verifier has separate `tracked`,
   `fixture-cache`, and Git-boundary scopes.
4. Immediately before deriving `PASS`, independently re-enumerate the full
   regular-file universe with that exact inventory expression. Compare its
   complete sorted relative-path set with the manifest's sorted
   `source_path` set, require one manifest record per path, and recompute the
   same include/exclude classification and expected destination for every
   record. Reject an added, removed, duplicated, or unclassified path, or any
   size/hash change. Run the procedure with `set -e` and `set -o pipefail`
   globally and inside its manifest function/command substitution; a failed
   project-absence or Python check records `BLOCKED` and can never produce
   `PASS`. `PASS` requires the recorded license decision to be exactly
   `FETCH_ONLY`, every vendor record to be `exclude` with a null destination,
   and every included user-authored mapping to be safe. A copied vendor file,
   missing meaningful file, or hash/classification change is a stop condition.

**Retry after BLOCKED:** Never overwrite `migration-preflight.md` or any
existing supporting record. An operator may retry only after preserving the
BLOCKED preflight under a unique immutable archival name, retaining its byte
hash, archiving any canonical manifest/provenance record that exists, attaching
new license-permission and operator-authorization evidence to task evidence,
and resetting 003.01.01 with `fest task reset <task-path> --yes`. Only then
may a fresh run atomically create canonical records. 003.01.02 mechanically
accepts one exact canonical `preflight manifest: PASS` decision line and no
BLOCKED decision.

**Error path:** Do not create the remote or destination if source access fails,
the manifest cannot be reproduced, a required input is unclassified, hashes
change during inventory, or upstream terms do not permit the intended private
copy. Record the precise blocker in `migration-preflight.md`.

**Verify:**

```sh
cd "$SOURCE"
python3 -c 'from pathlib import Path; assert Path("assessment/file_storage").is_dir()'
python3 -m hashlib 2>/dev/null || true
EVIDENCE="$FESTIVAL/003_BOOTSTRAP_MIGRATE/01_repository_and_provenance/results"
python3 - "$SOURCE" "$EVIDENCE/migration-manifest.json" <<'PY'
import hashlib, json, sys
from pathlib import Path
source, manifest_path = map(Path, sys.argv[1:])
data = json.loads(manifest_path.read_text())
assert data["schema_version"] == 2 and data["license_decision"] == "FETCH_ONLY"
assert isinstance(data["files"], list)
files = data["files"]
excluded = {".venv", "__pycache__", "attempts"}
source_paths = sorted(
    {path.relative_to(source).as_posix() for path in source.rglob("*") if path.is_file()}
)
manifest_paths = sorted({entry["source_path"] for entry in files})
assert len(files) == len(manifest_paths) and source_paths == manifest_paths
for entry in files:
    path = source / entry["source_path"]
    generated = (
        set(path.relative_to(source).parts) & excluded
        or path.suffix == ".pyc"
        or path.name in {"RESULT.md", "STATUS.md"}
    )
    vendor = entry["classification"] == "vendor"
    decision = "exclude" if generated or vendor else "include"
    destination = (
        None
        if generated or vendor
        else (
            "docs/legacy/explore-README.md"
            if entry["source_path"] == "README.md"
            else entry["source_path"]
        )
    )
    assert entry["decision"] in {"include", "exclude"}
    assert entry["decision"] == decision and entry["destination_path"] == destination
    if entry["source_path"] in {
        "assessment/vendor-readme.md",
        "assessment/file_storage/level1.md",
        "assessment/file_storage/level2.md",
        "assessment/file_storage/level3.md",
        "assessment/file_storage/level4.md",
        "assessment/file_storage/simulation.py",
        "assessment/file_storage/test_simulation.py",
    }:
        assert vendor and entry["cache_path"] and entry["sha256"]
    else:
        assert entry.get("cache_path") is None
    assert path.is_file() and path.stat().st_size == entry["bytes"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
print("preflight source manifest: PASS")
PY
```

The final source check runs against `SOURCE` and the preflight manifest,
independently proves complete inventory coverage, classifications, mappings,
and hashes, requires no project or future verifier, and reports
source-manifest success. Command output is tee'd to task evidence, never to
`migration-preflight.md`; that separate immutable provenance record contains
the deterministic totals, license finding, and exactly one standalone
`preflight manifest: PASS` or `preflight manifest: BLOCKED` line.

**Definition of done:** The manifest lists every source file with a decision,
the provenance decision is explicit, fixture hashes are recorded, the
reproducible verifier is reviewed, and no remote, project directory, campaign
submodule, or source content has yet been changed.

#### Task 003.01.02 — Create the private Python project after preflight

**Depends on:** 003.01.01 passing.<br>
**Sources:** D001, D002, and `SOURCE/.gitignore`.
**Destinations:** private `lancekrogers/codesignal-practice-simulator` remote;
`PROJECT/.git`, `.gitignore`, `pyproject.toml`,
`src/codesignal_practice_simulator/{__init__.py,__main__.py,cli.py}`,
`README.md`, and `docs/assessment-provenance.md`.

1. Create the approved private remote and clone or initialize it at exactly
   `PROJECT`. Confirm the remote is private with `gh repo view lancekrogers/codesignal-practice-simulator --json visibility` before pushing imported material.
2. Set Python `>=3.10`, a `src` package layout, console entry point
   `codesignal-sim`, and `python -m codesignal_practice_simulator` dispatch.
   Keep the initial CLI limited to help/version until runtime tasks exist.
3. Create `.gitignore` entries for `attempts/`, `.cache/codesignal-fixtures/`,
   virtual environments, Python caches, test artifacts, and temporary
   atomic-write files. Do not create or track upstream `requirements.txt`.
4. Author root `README.md` with installation prerequisites and the no-license
   FETCH_ONLY boundary: tracked code never contains upstream/vendor bytes, and
   `scripts/fetch_fixture.py` performs validated local setup.
5. Commit the scaffold before importing any source content. Rename the branch
   to `main`, push it with `--set-upstream origin main`, and verify the remote
   default branch by cloning the GitHub remote into a new temporary directory
   and checking out its `HEAD`. Do not begin campaign integration until this
   clone succeeds and `origin/HEAD` resolves to `origin/main`.

**Error path:** If GitHub creation/authentication/privacy verification fails,
stop before copying. If the target path exists but is not the approved clean
repository, stop rather than reusing or deleting it. Do not alter unrelated
campaign submodules.

**Verify:**

```sh
cd "$PROJECT"
python3 -m pip install -e .
codesignal-sim --help
python3 -m codesignal_practice_simulator --help
git check-ignore attempts/example/session.json
gh repo view lancekrogers/codesignal-practice-simulator --json visibility --jq .visibility | grep -qx PRIVATE
git add -- .gitignore pyproject.toml README.md src
git commit -m "chore: bootstrap simulator scaffold"
git branch -M main
git push --set-upstream origin main
RUN_DIR="$(mktemp -d)"
trap 'rm -rf -- "$RUN_DIR"' EXIT HUP INT TERM
git clone git@github.com:lancekrogers/codesignal-practice-simulator.git "$RUN_DIR/remote-default"
test main = "$(git -C "$RUN_DIR/remote-default" branch --show-current)"
test origin/main = "$(git -C "$RUN_DIR/remote-default" symbolic-ref --short refs/remotes/origin/HEAD)"
git remote get-url origin
```

Both help commands must succeed with the same command surface; runtime data
must be ignored; `gh repo view` must emit `PRIVATE`, and origin must be the approved destination.

**Definition of done:** The private, empty-product scaffold installs under
Python 3.10+, exposes both command entry points, ignores disposable runtime
paths, has a focused scaffold-only commit pushed to upstream-tracked `main`,
has a cloneable remote default branch. No campaign submodule exists yet; the
next task installs its manifest-driven Git boundary before any transfer commit.

#### Task 003.01.03 — Implement fetch-only fixture setup and verification

**Depends on:** 003.01.01–003.01.02.<br>
**Sources:** the exact seven manifest fetch-only records: upstream `README.md`
and `practice_assessments/file_storage/{level1.md,level2.md,level3.md,level4.md,simulation.py,test_simulation.py}`.
**Destinations:** `PROJECT/docs/{migration-manifest.json,assessment-provenance.md}`,
`PROJECT/scripts/{fetch_fixture.py,verify_manifest.py}`, `PROJECT/tests/test_migration.py`,
and only the ignored local fixture cache at runtime.

1. Copy only the manifest/provenance metadata into the project; never copy
   vendor contents.
2. Record the URL, commit, `licenseInfo: null`, `/license` 404, `FETCH_ONLY`
   decision, expected paths/hashes, cache location, and no-tracking rule.
3. Implement executable `scripts/fetch_fixture.py`: fetch all seven exact
   pinned public paths into a temporary cache, validate SHA-256 and normalized
   paths, then atomically publish the ignored cache. Map upstream `README.md`
   to cache `vendor-readme.md` and each upstream
   `practice_assessments/file_storage/` input to cache
   `assessment/file_storage/`. It accepts `--source PATH` only when that
   source materializes the complete upstream-path set for deterministic/offline
   tests and fails closed on network/hash/path/incomplete-set errors.
   Implement `verify_manifest.py` with separate `tracked` and `fixture-cache`
   scopes plus a `git-boundary` scope; neither script mutates tracked vendor
   paths. The latter hashes every staged and `HEAD` blob and rejects known
   vendor hashes and forbidden vendor paths.
4. Add tests for complete temporary local-source success (including
   `vendor-readme.md`), absent cache, incomplete local source, downloader
   failure, hash mismatch, and deterministic staged/HEAD Git-boundary
   failures and safe controls.
5. Stage the manifest, scanner, hooks, and tests, configure
   `core.hooksPath=.githooks`, prove both hooks run, and commit those
   non-vendor artifacts before the content-transfer task.

**Error path:** Any network, source-path, or hash error leaves no valid cache
and reports setup-required guidance. Never restore, hand-edit, or track vendor
files.

**Verify:**

```sh
RUN_DIR="$(mktemp -d)"
trap 'rm -rf -- "$RUN_DIR"' EXIT HUP INT TERM
FIXTURE_SOURCE="$RUN_DIR/upstream-fixture"
mkdir -p "$FIXTURE_SOURCE/practice_assessments/file_storage"
cp "$SOURCE/assessment/vendor-readme.md" "$FIXTURE_SOURCE/README.md"
cp -R "$SOURCE/assessment/file_storage/." "$FIXTURE_SOURCE/practice_assessments/file_storage/"
cd "$PROJECT"
python3 scripts/fetch_fixture.py --manifest docs/migration-manifest.json --source "$FIXTURE_SOURCE"
python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope tracked
python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope fixture-cache
python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary
python -m unittest discover -s tests -p 'test_migration.py' -v
git add -- docs/migration-manifest.json docs/assessment-provenance.md scripts .githooks tests
git config core.hooksPath .githooks
test "$(git config --get core.hooksPath)" = .githooks
.githooks/pre-commit
git check-ignore .cache/codesignal-fixtures/6aab304/simulation.py
```

**Definition of done:** No vendor file is tracked; provenance identifies the
upstream snapshot and FETCH_ONLY decision; setup atomically populates and
verifies every declared cache record; and the verifier separately checks
tracked mappings, cache hashes, and staged/HEAD Git boundaries.

### Sequence 003.02 — content_transfer_and_campaign

**Depends on:** 003.01.<br>
**Produces:** the complete meaningful migrated source and campaign integration
only after local evidence passes.

#### Task 003.02.01 — Transfer teaching, reference, and compatibility assets

**Sources:** `SOURCE/{README.md,requirements.txt,justfile}`,
`SOURCE/{scripts/scorecard.py,scripts/new_attempt.py}`,
`SOURCE/solution/**`, `SOURCE/study/**`, `SOURCE/notes/**`, and
`SOURCE/justfiles/{practice.just,verify.just}`.<br>
**Destinations:** each manifest-declared `destination_path` under `PROJECT`;
`SOURCE/README.md` maps to `PROJECT/docs/legacy/explore-README.md`, while
legacy behavior is refactored only in later phases into
`PROJECT/src/codesignal_practice_simulator/**`; also
`PROJECT/docs/migration-manifest.json`.

1. Copy only approved, non-verbatim user-authored source files to their
   manifest destinations, including the current explore README at
   `docs/legacy/explore-README.md`. Do not copy any record classified
   upstream/vendor, including the upstream README cached as
   `vendor-readme.md`, requirements, fixtures, or the explicitly excluded
   verbatim `solution/test_simulation.py`.
2. Author/update the root `README.md` to distinguish tracked simulator and
   teaching material from the fetch-only assessment cache, and document setup.
   Do not put reference material inside candidate workspaces.
3. Adapt user-authored scripts and optional Just recipes as compatibility
   surfaces; later CLI tasks replace their authority without importing upstream
   code.
4. After every included mapping exists, verify the `tracked` and Git-boundary
   scopes. Verify every fetched hash separately with a temporary local source
   or mocked downloader that contains the whole seven-record fetch set,
   including upstream `README.md` for `vendor-readme.md`, then run only lawful
   user-authored checks and retain their output.
5. Commit all transferred user-authored project content to local `main`, push
   it to `origin/main`, and verify `HEAD` equals the remote
   `refs/remotes/origin/main` SHA. Emit exactly one machine-readable evidence
   record for `transfer_commit_sha`, `transfer_remote_main_sha`, and
   `transfer_remote_equality: PASS`. This is a hard prerequisite for
   003.02.02; do not create a campaign gitlink to a scaffold-only or unpushed
   commit.

**Error path:** An exact upstream file, a missing user-authored mapping, or a
hash failure blocks transfer. Record any compatibility discrepancy without
altering the cache or attempting to track its contents.

**Verify:**

```sh
RUN_DIR="$(mktemp -d)"
trap 'rm -rf -- "$RUN_DIR"' EXIT HUP INT TERM
FIXTURE_SOURCE="$RUN_DIR/upstream-fixture"
mkdir -p "$FIXTURE_SOURCE/practice_assessments/file_storage"
cp "$SOURCE/assessment/vendor-readme.md" "$FIXTURE_SOURCE/README.md"
cp -R "$SOURCE/assessment/file_storage/." "$FIXTURE_SOURCE/practice_assessments/file_storage/"
cd "$PROJECT"
python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope tracked
python3 scripts/fetch_fixture.py --manifest docs/migration-manifest.json --source "$FIXTURE_SOURCE"
python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope fixture-cache
python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary
python solution/test_spec.py
python solution/test_stages.py
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
```

**Definition of done:** Every approved user-authored asset is present at its
mapped destination and tracked-scope verified; no vendor bytes are tracked;
every fetch record's hash and lawful checks have recorded outcomes; all
transferred user-authored project content is committed and pushed to `main`
with local and remote SHA equality; and teaching material remains outside the
cache and future attempt tree.

#### Task 003.02.02 — Integrate the proven project into the campaign

**Depends on:** 003.02.01 passing, its committed-and-pushed `main` SHA
verification, and a clean-clone rehearsal.
**Sources:** `CAMPAIGN/.gitmodules`, `SOURCE/.workitem`, and the verified
`PROJECT` remote.<br>
**Destinations:** `CAMPAIGN/.gitmodules`,
`CAMPAIGN/projects/codesignal-practice-simulator` (gitlink), and the
discoverability record for `explore-codesignal-industry-coding-framework-2026-09-08`
(`WI-117ed7`).

1. Before any campaign mutation, mechanically parse the prior transfer
   evidence. Require exactly one valid 40-character `transfer_commit_sha`, one
   matching `transfer_remote_main_sha`, and `transfer_remote_equality: PASS`;
   then require that SHA to equal both `git -C "$PROJECT" rev-parse HEAD` and
   `git -C "$PROJECT" rev-parse refs/remotes/origin/main`. Clone `PROJECT`
   into a separate temporary directory and run the documented
   install and legacy checks before modifying `CAMPAIGN`.
2. Snapshot `git -C "$CAMPAIGN" status --porcelain=v1` before integration.
   Preserve unrelated pre-existing unstaged paths as baseline evidence; require
   no pre-existing staged paths rather than resetting or cleaning the campaign.
   Add the approved SSH remote as the submodule at exactly
   `projects/codesignal-practice-simulator`; inspect the staged `.gitmodules`
   and gitlink only.
3. In a separate clean clone of `CAMPAIGN`, initialize recursively and rerun
   the project smoke tests. Do not edit or copy `SOURCE/.workitem`: 003.02.02
   records its exact ID/ref, source path, durable project path, and decided
   `retained` campaign disposition in integration evidence. Only the JobSearch
   campaign maintainer, through separately authorized campaign maintenance, may
   edit or remove the source-local metadata.
4. Retain `SOURCE` until the clean campaign clone check passes. Its removal is
   never part of migration recovery or this task.

**Error path:** If the remote is public, the clean clone cannot initialize, the
gitlink is wrong, or campaign status shows unintended changes, revert only the
new staged submodule files and stop. Never delete `SOURCE` as recovery.

**Verify:**

```sh
RUN_DIR="$(mktemp -d)"
trap 'rm -rf -- "$RUN_DIR"' EXIT HUP INT TERM
PROJECT_CLONE="$RUN_DIR/project"
CAMPAIGN_CLONE="$RUN_DIR/campaign"
FIXTURE_SOURCE="$RUN_DIR/fixture-source"
TRANSFER_EVIDENCE="$FESTIVAL/003_BOOTSTRAP_MIGRATE/02_content_transfer_and_campaign/results/01_transfer_teaching_reference_and_compatibility_assets.md"
mkdir -p "$FIXTURE_SOURCE/practice_assessments/file_storage"
cp "$SOURCE/assessment/vendor-readme.md" "$FIXTURE_SOURCE/README.md"
cp -R "$SOURCE/assessment/file_storage/." "$FIXTURE_SOURCE/practice_assessments/file_storage/"
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
(
  cd "$PROJECT_CLONE"
  python3 scripts/fetch_fixture.py --manifest docs/migration-manifest.json --source "$FIXTURE_SOURCE"
  python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope fixture-cache
  python3 -m codesignal_practice_simulator --help
)
git -C "$CAMPAIGN" submodule status -- projects/codesignal-practice-simulator
git clone --no-local "$CAMPAIGN" "$CAMPAIGN_CLONE"
git -C "$CAMPAIGN_CLONE" submodule update --init --recursive
python3 -m pip install -e "$CAMPAIGN_CLONE/projects/codesignal-practice-simulator"
(
  cd "$CAMPAIGN_CLONE/projects/codesignal-practice-simulator"
  python3 scripts/fetch_fixture.py --manifest docs/migration-manifest.json --source "$FIXTURE_SOURCE"
  python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope fixture-cache
  python3 -m codesignal_practice_simulator --help
)
```

**Definition of done:** A clean project clone works, a clean campaign clone
initializes the correct submodule, `.gitmodules` and the gitlink use the
approved private remote and published transfer SHA, the work item remains
discoverable, and no unrelated campaign work was modified.

## Phase 004 — SESSION_RUNTIME

**Entry dependency:** 003 complete.<br>
**Exit dependency:** isolated workspaces have recoverable authoritative state,
correct lifecycle enforcement, independent scoring, and safe derived views.

### Sequence 004.01 — session_state_and_workspaces

#### Task 004.01.01 — Define validated models, clock, and error taxonomy

**Sources:** `PROJECT/scripts/new_attempt.py` (legacy metadata is created at
`PROJECT/attempts/<timestamp>[_<name>]/attempt.json`, never project root), D002,
and D003.<br>
**Destinations:** `PROJECT/src/codesignal_practice_simulator/{models.py,clock.py,errors.py}`,
`PROJECT/docs/cli-contract.md`, and `PROJECT/tests/test_models.py`.

1. Define immutable typed models for assessment metadata, mode/profile, score
   summary, session state, event records, and active pointer. Validate
   schema/version, UUID/attempt identifier, revision, UTC timestamps, deadline
   ordering, four-level result shape, and lifecycle-specific submission fields.
2. Define a `Clock` protocol and production UTC implementation; inject it into
   services so tests use a fake clock. Use timezone-aware ISO-8601 timestamps.
3. Centralize user-safe errors and their documented exit mapping from the
   command contract. Never leak stack traces in JSON responses.

**Error path:** Reject unsupported schema versions, naïve/non-UTC timestamps,
negative duration, unknown mode/profile, malformed IDs, malformed score
objects, and illegal state combinations before a filesystem write.

**Verify:**

```sh
cd "$PROJECT"
python -m unittest tests.test_models -v
python -m unittest discover -s tests -p 'test_models.py' -v
```

**Definition of done:** All durable data has one validated schema owner,
services accept injected time, invalid input has stable errors, and no CLI
handler contains duplicate validation logic.

#### Task 004.01.02 — Build atomic persistence, locks, and workspace creation

**Depends on:** 004.01.01.<br>
**Sources:** `PROJECT/scripts/fetch_fixture.py`, validated
`PROJECT/.cache/codesignal-fixtures/6aab304/**`, and D003.
**Destinations:** `PROJECT/src/codesignal_practice_simulator/{persistence.py,workspace.py}`,
`PROJECT/tests/{test_persistence.py,test_workspace.py}`, and
`PROJECT/.gitignore`.

1. Require the complete seven-record validated local fixture cache, then
   transactionally copy exactly its `assessment/file_storage/simulation.py`,
   four `levelN.md` prompts, and `test_simulation.py` into
   `attempts/<attempt-id>/`; add `COACHING.md`, attempt `AGENTS.md`,
   `session.json`, `events.jsonl`, and generated `STATUS.md` as required by
   later tasks. Do not copy `vendor-readme.md` into an attempt.
2. Atomically write state and active pointer through flushed temporary siblings
   plus `os.replace`; implement per-attempt and workspace-root advisory locks.
3. Load events with strict JSON validation: reject malformed non-final lines,
   ignore exactly one incomplete trailing line, and reconcile a state revision
   lacking a matching event by appending a recovery event while locked.
4. Maintain only one versioned `attempts/active.json` pointer. Validate it
   rather than selecting the newest directory. Create the attempt in a unique
   sibling staging directory with a transaction-owned `.creation-owner.json`
   marker containing its attempt ID and creation token; publish it only after
   every input/write/flush succeeds, then atomically update the pointer.
   Under the workspace-root lock, startup reconciliation removes an attempt
   only when its valid ownership marker identifies that newly published attempt
   and the active pointer does not select it. It removes a marker from a
   pointer-selected attempt without deleting that attempt. Thus interruption
   after publish and before pointer replacement deterministically removes only
   the unpublished new attempt and preserves the prior pointer and every prior
   attempt. Inject filesystem operations and on any
   mkdir/copy/write/flush/replace failure roll back only the new
   staged/published attempt and leave the pointer, cache, and other attempts
   unchanged.

**Error path:** On an absent/invalid cache, return a clear setup-required error
without creating an attempt. On existing attempt ID, inaccessible root, cache
copy failure, lock contention, corrupt pointer, malformed state, or interrupted
write, leave other attempts and the cache unchanged.

**Verify:**

```sh
cd "$PROJECT"
python -m unittest tests.test_persistence tests.test_workspace -v
python -m unittest discover -s tests -p 'test_*workspace.py' -v
python -m unittest discover -s tests -p 'test_*persistence.py' -v
```

**Definition of done:** New attempts are self-contained and ignored by Git,
cache hashes stay unchanged, atomic/recovery/locking tests and injected
filesystem-failure rollback tests pass, and state selection is deterministic.

#### Task 004.01.03 — Implement lifecycle application services

**Depends on:** 004.01.02.<br>
**Sources:** D002–D003 and `PROJECT/scripts/{new_attempt.py,scorecard.py}`.<br>
**Destinations:** `PROJECT/src/codesignal_practice_simulator/lifecycle.py` and
`PROJECT/tests/test_lifecycle.py`.

1. Implement start, select, resume, expiry observation, and submit services
   outside CLI parsing. Start creates an active session and pointer; explicit
   resume may update the pointer for a selected active attempt.
2. At every locked selected-session operation, use the injected clock. The
   first observer of an expired active session atomically persists `expired`
   and an event. `status` and `time` then succeed with the expired view;
   `resume` and `test` return exit 4 without a new score, event, or revision.
3. Submit may finalize active or expired work. If it first observes expiry,
   persist the expired transition/event, then store one final score, submission
   metadata, and submission event. Repeating submit on submitted state returns
   the stored final result without running scoring or changing revision/event.

**Error path:** Rejected active-to-active, submitted-to-anything, and
expired-to-test/resume transitions leave session and events byte-for-byte
unchanged. Concurrent writers return exit 4; a corrupt selected attempt returns
exit 3 without touching a valid neighboring attempt.

**Verify:**

```sh
cd "$PROJECT"
python -m unittest tests.test_lifecycle -v
python -m unittest discover -s tests -p 'test_lifecycle.py' -v
```

**Definition of done:** Legal transitions, expiration, idempotent finalization,
revision checks, recovery, and concurrent-write rejection are deterministic
under fake clocks.

### Sequence 004.02 — assessment_scoring_and_agent_surfaces

**Depends on:** 004.01.<br>
**Produces:** a registry seam, partial-credit scoring, and non-authoritative
candidate/agent context.

#### Task 004.02.01 — Generalize assessment lookup and score isolated attempts

**Sources:** `PROJECT/scripts/scorecard.py:{resolve_target,run_level,timing,render_time}`,
validated local cache `test_simulation.py`, and
`PROJECT/solution/test_spec.py`.<br>
**Destinations:** `PROJECT/src/codesignal_practice_simulator/{assessment.py,scoring.py}`,
`PROJECT/tests/test_scoring.py`, and `PROJECT/docs/assessment-provenance.md`.

1. Create a registry interface and register only `file_storage`; it identifies
   validated-cache source paths, copied candidate inputs, four level groups, and
   available profiles. Do not add another assessment.
2. Execute `test_group_1` through `test_group_4` independently as
   `<absolute-interpreter> -I -S <attempt>/.scoring/run_group.py <group>` with
   the selected attempt as `cwd`. The copied, attempt-local bootstrap validates
   its own path and replaces application import paths with only the attempt
   candidate/test directory plus interpreter standard-library paths; it adds no
   project, editable-install, user-site, cache, solution, study, reference, or
   environment-derived path. The minimal child environment omits
   `PYTHONPATH` and Python site/configuration variables. Capture exit status
   and safe output, continue after failures/crashes, and calculate total passed
   plus highest contiguous level.
3. Persist the resulting score through lifecycle services, not the scorer's
   direct filesystem writes. Explicitly exclude coaching/status/agent documents
   from subprocess inputs and score calculation.
4. Keep fixture-compatible rollback behavior in candidate scoring; label
   `solution/test_spec.py` as the prose-correct educational profile.

**Error path:** Missing copied test/prompt, unknown assessment, subprocess
launch failure, timeout, and malformed test group are recorded as per-level
results without skipping independent later levels. Never run cached tests in
place or import `solution/` into an active attempt. Any project/reference
module import or hostile inherited `PYTHONPATH` is an isolation failure.

**Verify:**

```sh
RUN_DIR="$(mktemp -d)"
trap 'rm -rf -- "$RUN_DIR"' EXIT HUP INT TERM
FIXTURE_SOURCE="$RUN_DIR/upstream-fixture"
mkdir -p "$FIXTURE_SOURCE/practice_assessments/file_storage"
cp "$SOURCE/assessment/vendor-readme.md" "$FIXTURE_SOURCE/README.md"
cp -R "$SOURCE/assessment/file_storage/." "$FIXTURE_SOURCE/practice_assessments/file_storage/"
cd "$PROJECT"
python -m unittest tests.test_scoring -v
python3 scripts/fetch_fixture.py --manifest docs/migration-manifest.json --source "$FIXTURE_SOURCE"
python solution/test_spec.py
```

**Definition of done:** Four independent outcomes, total pass count, and
contiguous reach are persisted and rendered; changing `COACHING.md` or
`STATUS.md` cannot affect scores or cached-file hashes; tests prove injected
project/reference modules and `PYTHONPATH` values cannot influence scoring.

#### Task 004.02.02 — Render status, context, coaching, and agent boundaries

**Depends on:** 004.02.01.<br>
**Sources:** `PROJECT/notes/{walkthrough.md,level4-rollback-discrepancy.md}`,
D004, and validated session/event data.<br>
**Destinations:** `PROJECT/src/codesignal_practice_simulator/rendering.py`,
`PROJECT/{AGENTS.md,docs/agent-safety.md}`, attempt `COACHING.md`, attempt
`AGENTS.md`, generated attempt `STATUS.md`, and
`PROJECT/tests/test_rendering.py`.

1. Render Markdown and JSON context exclusively from selected state/events:
   safe attempt paths, assessment/mode/profile, lifecycle, clock/deadline,
   score summary, and next legal commands. Do not include candidate code,
   reference content, or test output that exposes solutions.
2. Generate/update `STATUS.md` only through the renderer. Create
   `COACHING.md` as a plain-text, non-executable candidate surface.
3. Author root and attempt `AGENTS.md`: read context/status first; edit only
   coaching by default; candidate-code edits require explicit request; never
   manually edit structured/derived state; never consult reference, stages,
   walkthrough, or study answers during active timed work. State that this is
   an operational, not cryptographic, boundary.
4. Document post-attempt access to education material and the level-4
   discrepancy without making it an active-session hint source.

**Error path:** If state cannot validate, refuse to generate a misleading
status and return session-unavailable. Rendering errors must not mutate
candidate code, fixture files, or authoritative state.

**Verify:**

```sh
cd "$PROJECT"
python -m unittest tests.test_rendering -v
python -m unittest discover -s tests -p 'test_rendering.py' -v
```

**Definition of done:** Status/context are derived, safe, and non-authoritative;
coaching safety rules are visible at root and attempt scopes; mutation
invariance tests pass.

## Phase 005 — CLI_WORKFLOWS

**Entry dependency:** 004 complete.<br>
**Exit dependency:** all documented commands expose the runtime without
duplicating domain logic and have consistent human/JSON/error behavior.

### Sequence 005.01 — command_interface_and_live_session

#### Task 005.01.01 — Build parser, output adapters, and selection plumbing

**Sources:** D002, `PROJECT/justfiles/practice.just`, and the 004 services.<br>
**Destinations:** `PROJECT/src/codesignal_practice_simulator/{cli.py,__main__.py}`,
`PROJECT/docs/cli-contract.md`, and `PROJECT/tests/test_cli.py`.

1. Define `argparse` subparsers once, common `--json`, `--workspace-root`,
   and `--attempt` options, and stable help examples. Map errors centrally to
   the five exit classes.
2. Make every handler construct/select services and serialize their typed
   results; no handler reads/writes JSON state, tests, locks, or fixtures.
3. Test installed console-command parity with module invocation.

**Error path:** Missing subcommand, unsupported option combination, invalid
path, and malformed attempt selector yield exit 2 with machine-readable error,
not traceback or partial state mutation.

**Verify:**

```sh
cd "$PROJECT"
python -m unittest tests.test_cli -v
codesignal-sim --help
python -m codesignal_practice_simulator --help
```

**Definition of done:** Parsing/output/exit-code behavior is documented and
covered; both invocation methods are behaviorally equivalent.

#### Task 005.01.02 — Expose start, resume, status, time, and task

**Depends on:** 005.01.01.<br>
**Sources:** 004 lifecycle, workspace, rendering, and scoring services.<br>
**Destinations:** `PROJECT/src/codesignal_practice_simulator/cli.py`,
`PROJECT/docs/cli-contract.md`, and `PROJECT/tests/test_cli.py`.

1. Wire `start` to full and drill profiles; require a named drill profile and
   persist duration/mode/start/deadline.
2. Wire `resume`, `status`, and `time` to explicit selection and lifecycle
   checks. `status`/`time` observe and persist expiration only through the
   lifecycle service.
3. Wire `task` to the copied prompt for the requested level, never
   `solution/`, `study/`, or root fixture content.
4. Cover no pointer, bad pointer, invalid explicit selector, submitted/expired
   session, and `--json` paths.

**Error path:** No valid selected attempt is exit 3; resume/test-eligible
checks on final sessions are exit 4; a request for an unavailable level is
exit 2. All errors identify a repair action without exposing reference text.

**Verify:**

```sh
cd "$PROJECT"
RUN_DIR="$(mktemp -d)"
trap 'rm -rf -- "$RUN_DIR"' EXIT HUP INT TERM
WORKSPACE="$RUN_DIR/workspace"
codesignal-sim start --workspace-root "$WORKSPACE" --mode full --json
codesignal-sim status --workspace-root "$WORKSPACE" --json
codesignal-sim time --workspace-root "$WORKSPACE"
codesignal-sim task --workspace-root "$WORKSPACE" --level 1
python -m unittest tests.test_cli -v
```

**Definition of done:** Candidate session creation and observation are usable
from both interfaces, selected attempts are deterministic, and no command
changes candidate source or cached fixture after start.

### Sequence 005.02 — evaluation_submission_and_operator_docs

**Depends on:** 005.01.<br>
**Produces:** evaluation/finality commands and documentation that makes the
CLI—not Just—the stable public contract.

#### Task 005.02.01 — Expose test, submit, and context safely

**Sources:** 004 scoring/lifecycle/rendering services and
`PROJECT/scripts/scorecard.py`.<br>
**Destinations:** `PROJECT/src/codesignal_practice_simulator/cli.py`,
`PROJECT/docs/cli-contract.md`, and `PROJECT/tests/test_cli.py`.

1. Wire `test` to score active sessions, persist the outcome/event, render
   partial credit, and return exit 5 when any group fails.
2. Wire `submit` to final score persistence and idempotent retrieval. Refuse
   tests/resumes after finalization while allowing safe read-only
   status/context.
3. Wire `context --format markdown|json` to the renderer; do not make it
   inspect candidate code or education sources.

**Error path:** Failed levels are a normal scored outcome, not a command crash.
Subprocess failure is per-level evidence. Submit on expired session persists finality as specified in 004.01.03; repeated
submit never reruns scoring or adds an event/revision.

**Verify:**

```sh
cd "$PROJECT"
RUN_DIR="$(mktemp -d)"
trap 'rm -rf -- "$RUN_DIR"' EXIT HUP INT TERM
WORKSPACE="$RUN_DIR/workspace"
codesignal-sim start --workspace-root "$WORKSPACE" --mode drill --json
python -m unittest tests.test_cli -v
codesignal-sim context --json --workspace-root "$WORKSPACE"
if codesignal-sim test --workspace-root "$WORKSPACE"; then
  printf '%s\n' 'expected candidate test failure' >&2
  exit 1
else
  test "$?" -eq 5
fi
codesignal-sim submit --workspace-root "$WORKSPACE" --json
codesignal-sim submit --workspace-root "$WORKSPACE" --json
```

**Definition of done:** Evaluation and finality have stable errors and JSON,
level failures preserve useful results, and status/context remain safe after
finalization.

#### Task 005.02.02 — Publish operator and compatibility documentation

**Sources:** `PROJECT/{README.md,justfile,justfiles/practice.just,justfiles/verify.just}`,
`PROJECT/notes/**`, and the completed CLI contract.<br>
**Destinations:** `PROJECT/{README.md,AGENTS.md,justfile}`,
`PROJECT/justfiles/{practice.just,verify.just}`,
`PROJECT/docs/{cli-contract.md,drill-profiles.md,agent-safety.md}`.

1. Document installation, console/module equivalence, full/drill use, selector
   precedence, runtime-data location, JSON schemas, errors/exits, and
   FETCH_ONLY setup and cache requirements.
2. Adapt Just recipes to invoke the CLI as optional developer shortcuts.
   Preserve meaningful legacy verification recipes and label deprecated
   behavior explicitly.
3. Explain agent safety, candidate approval, post-attempt learning paths, and
   the Level-4 compatibility/spec distinction without leaking walkthrough
   guidance into live commands.

**Error path:** Documentation must not claim a security sandbox, install an
unneeded runtime dependency, or provide an example that writes the fixture,
state, or candidate source unexpectedly.

**Verify:**

```sh
cd "$PROJECT"
codesignal-sim --help
just --list
just verify
python -m unittest tests.test_cli -v
```

**Definition of done:** A new user can run all commands without Just; Just
remains compatible; policies, dependencies, and error recovery are accurate.

## Phase 006 — VERIFICATION

**Entry dependency:** 004–005 complete.<br>
**Exit dependency:** deterministic local and clean-clone evidence proves
runtime contracts, migration fidelity, CLI workflows, and campaign integration.

### Sequence 006.01 — runtime_and_contract_tests

#### Task 006.01.01 — Complete deterministic unit and contract coverage

**Sources:** all 004–005 modules and requirements R04–R14.<br>
**Destinations:** `PROJECT/tests/{test_models.py,test_persistence.py,test_workspace.py,test_lifecycle.py,test_scoring.py,test_rendering.py,test_cli.py}`,
`PROJECT/docs/cli-contract.md`.

1. Add table-driven valid/invalid schema and transition cases, fake-clock
   full/drill/expiry cases, lock contention, revision recovery, pointer
   validation, and JSONL trailing-line recovery.
2. Assert score group independence, contiguous reach, crash representation,
   all-seven-record fetched-cache hashes, setup-required behavior,
   coaching/status non-interference, workspace rollback for every injected
   filesystem failure point (including publish-before-pointer interruption),
   and staged/HEAD Git vendor-boundary rejection. Inject an installed editable
   project sentinel, hostile `PYTHONPATH` sentinel, and loose reference
   sentinel; prove `-I -S` scoring children cannot import or observe them.
3. Assert every command's human/JSON envelope and documented exits.

**Error path:** Flaky timing, platform-specific lock failures, uncovered
recovery behavior, or nondeterministic subprocess results are defects: inject
the clock/process seams and remove timing assumptions rather than relaxing
assertions.

**Verify:**

```sh
cd "$PROJECT"
python -m unittest discover -s tests -v
python -m unittest tests.test_models tests.test_persistence tests.test_lifecycle tests.test_scoring tests.test_rendering tests.test_cli -v
```

**Definition of done:** Tests directly prove each state, event, isolation,
scoring, safety, command, and failure contract with no network or wall-clock
dependency.

### Sequence 006.02 — cli_end_to_end_and_migration_release_checks

**Depends on:** 006.01.<br>
**Produces:** real-process lifecycle, migration, and clean-clone evidence.

#### Task 006.02.01 — Exercise full and drill CLI lifecycles in temporary roots

**Sources:** installed `PROJECT` package and a validated local fixture cache.
**Destinations:** `PROJECT/tests/test_end_to_end.py` and
`PROJECT/justfiles/verify.just`.

1. Use `tempfile.TemporaryDirectory` and subprocess invocation of both CLI
   entry points. Execute start → status/time/task → test → submit → repeated
   submit for full and drill sessions.
2. Test no active attempt, explicit-selector precedence, expired session,
   candidate test failures, invalid JSONL tail, and lock contention in real
   processes.
3. Populate the cache from a temporary local source or mocked downloader, then
   assert attempt data never appears in project root or cache and all runtime
   paths remain ignored.

**Error path:** A test may not use a developer's existing `attempts/`, global
environment state, or local timestamp ordering. Any leak to the cache/root is
a blocking isolation failure.

**Verify:**

```sh
cd "$PROJECT"
python -m unittest tests.test_end_to_end -v
git status --ignored --short attempts
```

**Definition of done:** Complete lifecycle evidence runs in isolated temporary
directories for both entry points and both modes.

#### Task 006.02.02 — Prove migrated fidelity and clean-clone reproducibility

**Sources:** `PROJECT/docs/{migration-manifest.json,assessment-provenance.md}`,
legacy source/test files, `CAMPAIGN/.gitmodules`, and the project remote.<br>
**Destinations:** `PROJECT/scripts/run_legacy_checks.py`,
`PROJECT/tests/test_migration.py`, `PROJECT/justfiles/verify.just`, and
`PROJECT/.github/workflows/verify.yml` (if CI is enabled for the private
repository).

1. Compose one standard documented direct-Python command that verifies
   tracked manifest mappings and fetched-cache hashes separately, then runs
   unit/CLI/end-to-end and lawful user-authored compatibility checks.
2. Rehearse fresh project and campaign clones using only documented
   installation steps. Each clone must use a temporary local source fixture or
   mocked downloader that materializes every one of the seven manifest fetch
   records, including upstream `README.md` → `vendor-readme.md`; neither may
   contain unlicensed tracked upstream bytes or require network access.
3. If repository CI is enabled, make it call the same local verification
   command on Python 3.10; do not create network-dependent hidden test logic.
   Just may be run only as an optional compatibility check when installed.

**Error path:** A missing cache, downloader error, or hash difference must
produce setup guidance, not a misleading simulator-core failure. A
clean-clone/submodule failure or tracked vendor byte blocks release.

**Verify:**

```sh
RUN_DIR="$(mktemp -d)"
trap 'rm -rf -- "$RUN_DIR"' EXIT HUP INT TERM
PROJECT_CLONE="$RUN_DIR/project"
CAMPAIGN_CLONE="$RUN_DIR/campaign"
FIXTURE_SOURCE="$RUN_DIR/fixture-source"
mkdir -p "$FIXTURE_SOURCE/practice_assessments/file_storage"
cp "$SOURCE/assessment/vendor-readme.md" "$FIXTURE_SOURCE/README.md"
cp -R "$SOURCE/assessment/file_storage/." "$FIXTURE_SOURCE/practice_assessments/file_storage/"
git clone --no-local "$PROJECT" "$PROJECT_CLONE"
(
  cd "$PROJECT_CLONE"
  python3 -m pip install -e .
  python3 scripts/fetch_fixture.py --manifest docs/migration-manifest.json --source "$FIXTURE_SOURCE"
  python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope tracked
  python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope fixture-cache
  python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary
  python scripts/run_legacy_checks.py
  python -m unittest discover -s tests -v
)
git clone --no-local "$CAMPAIGN" "$CAMPAIGN_CLONE"
git -C "$CAMPAIGN_CLONE" submodule update --init --recursive
(
  cd "$CAMPAIGN_CLONE/projects/codesignal-practice-simulator"
  python3 -m pip install -e .
  python3 scripts/fetch_fixture.py --manifest docs/migration-manifest.json --source "$FIXTURE_SOURCE"
  python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope tracked
  python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope fixture-cache
  python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary
  python scripts/run_legacy_checks.py
  python -m unittest discover -s tests -v
)
```

**Definition of done:** A clean clone produces all required evidence with
documented dependencies; the campaign clone resolves the private submodule; no
CI-only or developer-machine-only requirement remains.

## Phase 007 — REVIEW_RELEASE

This is a review phase, not an implementation sequence. It has no code-creation
tasks. The reviewer records evidence in
`FESTIVAL/007_REVIEW_RELEASE/PHASE_GOAL.md` and its review result directory.

### Review checklist and release decision

| Review area | Evidence required | Blocking result |
| --- | --- | --- |
| Requirements traceability | This plan plus passing tests/evidence for R01–R15; R16–R17 remain deferred | Any P0/P1 requirement lacks an owner or result |
| Privacy/provenance | Private remote confirmation, manifest, FETCH_ONLY decision, and cache hashes | Public remote, tracked vendor bytes, unclear boundary, or cache mismatch |
| Isolation/lifecycle | Workspace, fake-clock, lock, recovery, idempotent-submit tests | Cross-attempt/cache write, invalid state recovery, non-final submit |
| Assessment fidelity | Four group outcomes, legacy tests, explicit Level-4 dual-profile evidence | Aggregate-only scoring or silent fixture/spec alteration |
| CLI/candidate experience | Console/module parity, documented exits/JSON, E2E full/drill traces | Ambiguous selection, undocumented error, or broken entry point |
| Agent safety | Root/attempt guidance and coaching/status non-interference tests | Reference leakage in active flow or claims of a security sandbox |
| Campaign integration | Clean superproject clone with initialized approved submodule | Wrong gitlink, failed submodule init, or unrelated campaign changes |

**Release definition of done:** All blocking rows have dated command output,
the private repository and clean campaign clone are reproducible, deferred work
is explicitly R16–R17 only, review finds no unresolved high-severity defect,
and handoff identifies the canonical verification command.

## Requirement Traceability

| Requirement | Implementing tasks | Acceptance evidence |
| --- | --- | --- |
| R01 | 003.01.02, 003.02.02, 006.02.02 | private remote and clean submodule clone |
| R02 | 003.01.01, 003.02.01 | approved manifest and hashes |
| R03 | 003.01.03, 004.01.02, 006.02.02 | FETCH_ONLY provenance, fetch, and cache hash checks |
| R03a | 003.01.02–003.01.03, 006.01.01 | hooks and staged/HEAD vendor-boundary tests |
| R04 | 004.02.01, 006.01.01 | independent groups and contiguous reach |
| R05 | 005.01.01–005.02.01, 006.01.01 | CLI contract, exits, console/module tests |
| R06 | 004.01.01, 004.01.03, 005.01.02 | fake-clock full/drill persisted duration |
| R07 | 004.01.02, 006.02.01 | workspace isolation tests |
| R07a | 004.02.01, 006.01.01–006.02.01 | sanitized scoring subprocess isolation |
| R08 | 004.01.01–004.01.02, 006.01.01 | atomic state/event recovery tests |
| R09 | 004.01.03, 005.02.01, 006.01.01 | lifecycle, lock, and idempotency tests |
| R10 | 004.02.02, 005.02.01 | generated status/context tests |
| R11 | 004.02.02, 006.01.01 | coaching exclusion/invariance tests |
| R12 | 004.02.02, 005.02.02 | root and attempt agent guidance |
| R13 | 003.02.01, 004.02.01, 005.02.02 | educational separation and dual-profile docs |
| R14 | 006.01.01–006.02.02 | unit, integration, E2E, clean-clone evidence |
| R15 | 003.02.01, 004.02.01, 006.02.02 | legacy and discrepancy verification |
| R16 | 004.02.01 | registry seam; no second assessment |
| R17 | 004.02.01, 007 review | explicitly deferred; no weighted/hidden/remote scope |

## Sequence Gates

After each implementation sequence, create its required `results/` evidence
and run the configured testing, code-review, review/iterate, and focused-commit
gates. The authoritative concrete commands are:

```sh
cd "$PROJECT"
python -m unittest discover -s tests -v
python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope tracked
python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope fixture-cache
python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary
python scripts/run_legacy_checks.py
git diff --check
git status --short
```

Before 003.01.03, only commands whose inputs already exist apply. Before
`run_legacy_checks.py` is implemented, execute its listed component legacy
commands from 003.02.01. When installed, `just verify` is an optional
compatibility check after these authoritative commands. A gate fails on any
authoritative command failure, generated runtime file tracked by Git,
tracked vendor byte, unreviewed changed cache hash, undocumented expected Level-4 profile
difference, or unrelated campaign modification.
