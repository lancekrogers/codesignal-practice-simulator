# Festival Overview: CodeSignal Practice Library

## Problem and scope

CB0001 explicitly excluded additional assessments. The registry still contains
only File Storage; browser start rejects a live selected attempt. Submission
scores/timestamps already persist, but there is no past-attempt catalog.

This festival covers multiple Python assessments, unlimited fresh attempts,
confirmed abandon/restart preserving prior work, metadata history, read-only
submission review, compatibility, and complete browser/CLI verification.

## Proposed execution shape

After INGEST and PLAN, create implementation sequences in dependency order:

1. Attempt lifecycle/history: schema compatibility, abandon/restart transaction,
   bounded listing, and immutable submission-review contract.
2. Assessment library: versioned catalog, packaged original problems/scoring,
   and compatibility with fetched File Storage.
3. Practice UI: selector, restart confirmation, history, review, keyboard
   navigation, and recovery/error states.
4. Verification/release: migration fixtures, concurrency/crash tests, real
   browser journeys, offline wheels, documentation, and review remediation.

These are full-scope planning groups, not yet scaffolded executable tasks.
Create tasks just in time with verified source anchors and quality gates.

## Boundaries and decisions

Remain local, single-user, Python-first. No cloud accounts, proctoring,
proprietary question reproduction, arbitrary new languages, or attempt deletion.

Proposed initial catalog: retain File Storage and add two original four-level
Python exercises, in-memory records and account ledger. Count/tracks require
acceptance. PLAN must resolve version pinning, restart crash recovery, exact
result/source binding, safe legacy reads, and history pagination. Do not invent
historical per-test details that older submissions did not persist.

Related work: completed CB0001 and follow-up navigation/shutdown/README PRs.
Recheck integration baseline before implementation; preserve user checkout edits.

<!-- fest:replay:start -->
## Execution replay

![Festival execution replay](festival-replay.gif)
<!-- fest:replay:end -->
