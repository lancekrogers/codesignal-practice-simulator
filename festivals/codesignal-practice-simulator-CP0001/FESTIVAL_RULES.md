# Festival Rules: CodeSignal Practice Simulator

## Scope and ownership

- Planning changes only festival documents and configuration. It must not create
  the GitHub repository, copy the source tree, or alter campaign integration.
- Execution creates the private project only after preflight contains exactly
  `license decision: FETCH_ONLY` and `preflight manifest: PASS`.
- GitHub reports `licenseInfo: null` and a 404 `/license` endpoint at
  `6aab304`; no exact upstream/vendor byte may be tracked. The manifest stores
  paths/hashes/provenance only. Its one exact fetch set is upstream `README.md`
  → cache `vendor-readme.md` plus six upstream
  `practice_assessments/file_storage/` → cache `assessment/file_storage/`
  records. Setup atomically fetches every record into an ignored validated
  cache; simulator commands never write that cache.
- Candidate code lives only in an attempt workspace. `session.json`,
  `events.jsonl`, locks, active pointers, and generated `STATUS.md` have the
  ownership specified in the implementation plan.
- `SOURCE/.workitem` is source-local campaign metadata, not a project asset.
  It is excluded from the migration manifest; 003.02.02 records the decided
  `retained` disposition after clean-clone success. The JobSearch campaign
  maintainer owns any later retirement/update under separate authorization.

## Migration and provenance

- Enumerate every source file in the schema-version 2 manifest with a
  classification, byte length, SHA-256, and reason. Only non-verbatim
  user-authored files receive safe unique destinations. The user-authored
  explore README maps to `docs/legacy/explore-README.md`; the root product
  README is newly authored. Vendor files—including the assessment, vendor
  README, explicitly excluded `solution/test_simulation.py`, requirements, and
  any exact upstream match—are excluded with null destinations; only the
  seven declared fetch records receive cache paths.
- `core.hooksPath` must be `.githooks`; pre-commit and pre-push run the
  manifest-driven scanner, which hashes every staged-index and `HEAD` blob and
  rejects a known vendor hash or forbidden vendor path.
- A preflight record is immutable. Never tee command output into it or
  overwrite it. A blocked record may be retried only by the archival and task
  reset procedure in 003.01.01.
- Do not create the remote, destination project, submodule, or source changes
  when the FETCH_ONLY boundary, manifest verification, or preflight is incomplete.
- `.gitmodules` is a JobSearch campaign-root integration anchor. It is never a
  source-project asset or migration input.
- Before any campaign mutation, 003.02.02 must mechanically parse the prior
  transfer evidence for exactly one successful transfer SHA/equality record and
  prove that SHA equals both PROJECT `HEAD` and `origin/main`.

## Runtime and verification

- Use Python 3.10+ and the standard library for the simulator core and fetcher.
  `--source` supports deterministic offline setup tests.
- `codesignal-sim` and `python -m codesignal_practice_simulator` are the
  authoritative interfaces. Just recipes are optional compatibility checks.
- Preserve independent `test_group_1` through `test_group_4` results,
  fixture-compatible rollback behavior, and the separate prose-correct
  educational profile.
- Scoring subprocesses launch exactly as
  `<absolute-interpreter> -I -S <attempt>/.scoring/run_group.py <group>` with
  selected-attempt `cwd`. The attempt-local bootstrap permits only copied
  candidate/test paths plus interpreter standard-library paths, and no
  global/user site, project, editable-install, reference, or environment path.
  Tests must prove editable-project, `PYTHONPATH`, and loose-reference
  sentinels cannot leak.
- Workspace creation is transactional and must roll back all injected
  filesystem faults without leaving a partial attempt or changing its pointer.
  A marker-owned publish-before-pointer interruption reconciles by deleting
  only the new unpublished attempt and preserving the former pointer/attempts.
- Verification must use direct Python commands in clean project and campaign
  clones. It may run `just verify` only when Just is installed and must not
  treat it as a prerequisite for authoritative evidence.

## Completion evidence

- Record task output under the sequence `results/` directory, keep focused
  commits, and preserve unrelated campaign changes.
- Run the task's direct Python checks, `git diff --check`, declared dependency
  installation, and relevant Festival validation before completion.
- Escalate instead of weakening a cache hash, FETCH_ONLY decision, lifecycle
  boundary, clean-clone assertion, or exact PASS requirement.
