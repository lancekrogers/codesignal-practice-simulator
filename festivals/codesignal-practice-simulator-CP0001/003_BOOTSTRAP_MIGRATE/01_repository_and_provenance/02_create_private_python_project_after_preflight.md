---
fest_type: task
fest_id: 02_create_private_python_project_after_preflight.md
fest_name: create_private_python_project_after_preflight
fest_parent: 01_repository_and_provenance
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-08T16:23:47.527944-06:00
fest_updated: 2026-09-08T18:52:12.768172-06:00
fest_tracking: true
fest_dependencies:
  - 01_inventory_source_and_approve_migration_boundary
---


# Task: 003.01.02 — Create the Private Python Project After Preflight

## Objective

After an exact canonical FETCH_ONLY passing preflight, create, publish, and
clean-clone the private minimal Python scaffold before user-authored material
is transferred.

## File anchors

Prerequisite: the canonical preflight is PASS with `license decision:
FETCH_ONLY`. Create only the Python scaffold, `.gitignore`, root README, and
package entry points; do not create upstream `requirements.txt` or a tracked
fixture path. The manifest-driven scanner and hook wrappers are installed in
003.01.03 after its manifest is staged. Evidence is this task’s
`results/02_create_private_python_project_after_preflight.md`.

## Ordered implementation steps

1. Immediately before remote creation, mechanically require that the canonical
   preflight has exactly one decision line, it is the final nonblank line,
   `license decision: FETCH_ONLY` is present, and it is exactly
   `preflight manifest: PASS`; any BLOCKED line or other license decision is a
   rejection. Verify that PROJECT does not already exist; never reuse or
   delete an existing path. Create the empty private remote without `--source`,
   prove its visibility, then clone it into the verified-absent destination:
   ```sh
   PREFLIGHT="/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/003_BOOTSTRAP_MIGRATE/01_repository_and_provenance/results/migration-preflight.md"
   PROJECT="/workspace/campaign/projects/codesignal-practice-simulator"
   python3 - "$PREFLIGHT" <<'PY'
   import sys
   from pathlib import Path
   lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
   decisions = [line for line in lines if line.startswith("preflight manifest:")]
   assert decisions == ["preflight manifest: PASS"]
   assert next(line for line in reversed(lines) if line.strip()) == "preflight manifest: PASS"
   PY
   test ! -e "$PROJECT"
   gh repo create lancekrogers/codesignal-practice-simulator --private
   gh repo view lancekrogers/codesignal-practice-simulator --json visibility --jq .visibility | grep -qx PRIVATE
   git clone git@github.com:lancekrogers/codesignal-practice-simulator.git "$PROJECT"
   ```
2. Initialize the Python 3.10+ src-layout package in the cloned destination. Define `codesignal-sim` and `python -m codesignal_practice_simulator`; implement help/version only until runtime work exists.
3. Ignore `attempts/`, `.cache/codesignal-fixtures/`, environments, test
   artifacts, and atomic temporary siblings.
4. Author root `README.md` with installation and FETCH_ONLY guidance. It must
   say that upstream/vendor files are never tracked and setup later retrieves
   validated files into the ignored cache.
5. Commit only the scaffold, rename the branch to `main`, and push it with
   upstream tracking. In a fresh temporary clone of the GitHub remote, verify
   that the remote default branch resolves to `main` and its checked-out HEAD
   is the pushed scaffold commit. The clone from step 1 establishes the
   approved `origin`; do not add a campaign submodule until this proof and the
   approved campaign integration workflow in 003.02.02 pass.

## Error paths

Missing/non-FETCH_ONLY-PASS preflight, authentication failure, a non-PRIVATE
visibility value, an existing destination, or install/entry-point failure
blocks the task. A remote URL listing is not visibility proof and must not be
substituted.

## Do-not-mutate boundaries

Do not copy SOURCE, push upstream/vendor material, add a submodule, change
the campaign-root `.gitmodules`, edit `SOURCE/.workitem`, or alter unrelated
campaign state.

## Verification and evidence

Run from the directory named in the commands. Save complete output and exit codes to `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/003_BOOTSTRAP_MIGRATE/01_repository_and_provenance/results/02_create_private_python_project_after_preflight.md`; a nonzero exit is blocking unless stated below.

```sh
PROJECT="/workspace/campaign/projects/codesignal-practice-simulator"
PREFLIGHT="/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/003_BOOTSTRAP_MIGRATE/01_repository_and_provenance/results/migration-preflight.md"
EVIDENCE="/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/003_BOOTSTRAP_MIGRATE/01_repository_and_provenance/results/02_create_private_python_project_after_preflight.md"
mkdir -p "$(dirname "$EVIDENCE")"
RUN_DIR="$(mktemp -d)"
trap 'rm -rf -- "$RUN_DIR"' EXIT HUP INT TERM
set -e
set -o pipefail
{
python3 - "$PREFLIGHT" <<'PY'
import sys
from pathlib import Path
lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
decisions = [line for line in lines if line.startswith("preflight manifest:")]
assert decisions == ["preflight manifest: PASS"]
assert "license decision: FETCH_ONLY" in lines
assert next(line for line in reversed(lines) if line.strip()) == "preflight manifest: PASS"
PY
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
SCAFFOLD_COMMIT="$(git rev-parse HEAD)"
git clone git@github.com:lancekrogers/codesignal-practice-simulator.git "$RUN_DIR/remote-default"
test "$SCAFFOLD_COMMIT" = "$(git -C "$RUN_DIR/remote-default" rev-parse HEAD)"
test main = "$(git -C "$RUN_DIR/remote-default" branch --show-current)"
test origin/main = "$(git -C "$RUN_DIR/remote-default" symbolic-ref --short refs/remotes/origin/HEAD)"
git diff --check
git status --short
} 2>&1 | tee "$EVIDENCE"
```

Expected result: the commands produce the stated success output and `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/003_BOOTSTRAP_MIGRATE/01_repository_and_provenance/results/02_create_private_python_project_after_preflight.md` records it.

## Definition of done

- [ ] Exactly one canonical final decision is mechanically asserted as
  `preflight manifest: PASS` and `license decision: FETCH_ONLY` before remote
  creation; BLOCKED, ambiguous, or copy-permitting content is rejected.
- [ ] `gh repo view` reports only `PRIVATE`.
- [ ] Both entry points work and attempt data is ignored.
- [ ] The scaffold-only commit is pushed on upstream-tracked `main`, and a
  fresh clone proves that `main` is the remote default branch before campaign
  integration or source import.
