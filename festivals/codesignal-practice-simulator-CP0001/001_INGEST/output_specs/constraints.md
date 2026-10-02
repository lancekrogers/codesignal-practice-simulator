# Constraints: CodeSignal Practice Simulator

## Scope and Change Boundaries

1. This festival plans the work only. It must not create the external GitHub
   repository, create a GitHub remote, copy/move the exploration source, alter
   product code, or modify unrelated campaign changes during planning.
2. The repository name, owner, privacy setting, destination, migration scope,
   and five implementation/review phases are approved. The festival workflow's
   normal plan-approval checkpoint is therefore recorded as satisfied for this
   run; no additional product-design approval is needed before task
   scaffolding.
3. Preserve unrelated work already present in the JobSearch superproject.
   Implementation work must use focused commits and must not reset, clean, or
   rewrite existing modified/submodule state.

## Technical Constraints

1. Target Python 3.10 or later because the upstream assessment identifies
   CodeSignal Python 3.10.6. Use the standard library for simulator runtime,
   persistence, process management, and test orchestration where practical.
2. The upstream repository has no usable license: GitHub reports
   `licenseInfo: null` and its `/license` endpoint returns 404 at commit
   `6aab304`. Its exact files must never be added to the private repository,
   even as an attributed fixture. Preserve only provenance and per-file
   expected hashes/paths in Git; use a Git-ignored local cache populated by a
   pinned fetch script or its `--source` test seam.
3. The simulator core and fixture-fetcher use the standard library. A setup
   failure (network, unsafe path, missing source file, or hash mismatch) fails
   closed and reports setup guidance. Candidate workspaces receive copies only
   from a validated cache; tests and simulator status files must not alter the
   cache or tracked project files.
4. JSON is the durable machine interface. Write `session.json` atomically
   (temporary sibling then replace) and append individual JSON records to
   `events.jsonl`. UTC ISO-8601 timestamps, schema versions, and explicit
   validation are mandatory.
5. A same-machine local CLI cannot cryptographically prevent an unrestricted
   terminal agent from editing candidate files. The safety guarantee is
   therefore a clear operational boundary: documented permitted paths,
   commands that never write candidate code, and tests that prove coaching is
   excluded from evaluation.

## Assessment-Fidelity Constraints

1. A full session is precisely 90 minutes; drill duration is explicitly named
   and persisted rather than silently masquerading as an authentic assessment.
2. Preserve independent execution of `test_group_1` through `test_group_4`
   and report both passed groups and contiguous reach. Do not replace this
   with aggregate-only scoring.
3. Preserve exact output-string behavior and the known Level-4 contradiction:
   fixture compatibility uses announce-only rollback, while educational/spec
   checks retain real restoration semantics. Do not silently change either.
4. Keep reference answers, stages, and walkthrough material outside active
   candidate workspaces and make the access boundary clear in documentation.

## Delivery and Review Constraints

1. GitHub repository creation and campaign submodule registration occur in the
   implementation migration phase only, after a source inventory, FETCH_ONLY
   provenance decision, and clean local validation plan exist.
2. `SOURCE/.workitem` is source-local campaign metadata, not an asset to
   migrate. 003.02.02 owns recording its decided `retained` disposition after
   a successful clean campaign clone; the JobSearch campaign maintainer owns
   any future source-local metadata mutation through a separately authorized
   campaign-maintenance action.
3. All implementation sequences need executable numbered task files and the
   configured testing, review, iteration, and commit quality gates. Gate
   commands must be concrete for the selected project tooling.
4. Planning deliverables must contain substantive, project-specific content in
   every required section. A final `fest validate` and marker audit are
   required.
