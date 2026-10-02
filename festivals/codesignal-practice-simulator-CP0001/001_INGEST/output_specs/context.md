# Context and Source Anchors

## Existing Project

The source to migrate is
`/workspace/campaign/workflow/explore/codesignal-industry-coding-framework`.
It is a single `file_storage` Industry Coding Framework practice project with
an untouched vendor fixture, a reference solution, staged teaching solutions,
a hand-coding study track, a timed-attempt harness, and explanatory notes.

The source README identifies the upstream repository as
`PaulLockett/CodeSignal_Practice_Industry_Coding_Framework` at commit
`6aab304`. GitHub reports `licenseInfo: null` and `GET /license` returns 404.
Implementation must use `FETCH_ONLY`: record provenance and expected
paths/hashes, but do not copy exact upstream/vendor bytes into the private
repository. The exact fetch set is upstream `README.md` → cache
`vendor-readme.md`, plus upstream
`practice_assessments/file_storage/{level1.md,level2.md,level3.md,level4.md,simulation.py,test_simulation.py}`
→ cache `assessment/file_storage/` counterparts, all below
`.cache/codesignal-fixtures/6aab304/`.

## Reuse Anchors

| Area | Source anchor | Planning significance |
| --- | --- | --- |
| Attempt creation | `scripts/new_attempt.py` — `COPIED_FILES`, `main()` | Copies six fixture files to `attempts/<timestamp>`, records UTC start/deadline, and is the basis for isolated workspaces. |
| Scoring | `scripts/scorecard.py` — `resolve_target()`, `run_level()`, `timing()`, `render_time()`, `main()` | Uses a separate subprocess per `test_group_N`, calculates passed-count and contiguous reach, and emits `scorecard/v1` JSON. |
| Command UX | `justfiles/practice.just` | Maps the current `practice`, `score`, `level`, `time`, `task`, `submit`, `where`, and `attempts` recipes to the desired stable command surface. |
| Regression recipes | `justfiles/verify.just` | Defines bundled, spec, staged, reference scorecard, compare, and cleanup checks that the migration must preserve or replace explicitly. |
| Vendor fixture | `assessment/vendor-readme.md`; `assessment/file_storage/{level1..4}.md`, `simulation.py`, `test_simulation.py` | Upstream README and candidate contract are excluded from Git; setup atomically fetches and hash-validates all seven declared records to the ignored cache, but attempts copy only the six assessment inputs. |
| Reference implementation | `solution/simulation.py` — `FileStorage`, `StoredFile`, `Operation`, parsers, handlers | Provides a standard-library reference and exposes the documented rollback compatibility modes. |
| Specification tests | `solution/test_spec.py` | Tests numeric size parsing, errors, TTL boundaries, expiry/copy behavior, and real rollback beyond fixture happy paths. |
| Stage tests | `solution/test_stages.py`, `solution/stages/` | Demonstrates cumulative levels independently and must remain an educational track, not candidate-session material. |
| Study drill | `study/check.py`, `study/starter.py`, `study/level{1..4}.py`, `study/README.md` | Supplies active-recall cases and teaching context; evaluate how it maps to an accelerated drill without exposing answers during an active session. |
| Coaching content | `notes/walkthrough.md`, `notes/level4-rollback-discrepancy.md` | Supplies level strategy, time budgets, and the visible-test/prose mismatch that the new agent/coaching documents must make explicit. |

## Current Behavior and Gaps

Today, `new_attempt.py --minutes 90` provides an authentic-duration attempt
and `scorecard.py` produces a terminal score or an optional final `RESULT.md`.
It has no named drill profile, active-attempt pointer, resume lifecycle,
persisted evolving state, append-only events, generated live status,
candidate-safe coaching document, agent instructions, or harness end-to-end
tests.

The existing `attempts/<timestamp>[_<name>]/attempt.json` is useful but static: it records
`schema_version`, assessment, start, deadline, and duration once. The planned
`session.json` evolves through the lifecycle and is complemented—not
replaced—by append-only event records. Markdown status is a derived
convenience view, never the authority.

## Campaign Integration

The JobSearch campaign uses Git submodules under `projects/`; `.gitmodules`
currently records SSH URLs in the `lancekrogers` GitHub organization/account.
The target integration follows that convention at
`projects/codesignal-practice-simulator` after the repository exists. The
current exploration work item is
`explore-codesignal-industry-coding-framework-2026-09-08` (`WI-117ed7`), so
the project migration must exclude `SOURCE/.workitem` as source-local campaign
metadata. After a successful campaign clean clone, 003.02.02 owns recording
its decided `retained` disposition with that ID/ref and the durable project
path. It does not edit or copy the source-local metadata; the JobSearch
campaign maintainer owns any future schema-valid retirement/update through a
separately authorized campaign-maintenance action.
