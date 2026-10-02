# Gap Analysis and Resolution Record

## No Approval-Blocking Product Gaps

The user has explicitly approved the private repository identity, campaign
destination, fetch-only provenance boundary, complete user-authored-content
migration, and the five delivery/review phases.
The simulator must provide the named lifecycle commands, authentic 90-minute
and accelerated drill modes, isolated workspaces, level-by-level scoring,
durable state/events, agent-readable context, coaching safety, live-agent
guidance, and end-to-end tests. Those requirements are sufficient to create
implementation tasks.

## Decisions Resolved During Planning

| Topic | Resolution | Why it is sufficient |
| --- | --- | --- |
| Command name | Use `codesignal-sim` with equivalent `python -m` invocation; retain Just recipes as compatibility shortcuts. | The current project is Python and has human-friendly Just wrappers, but the new required interface needs a stable primary CLI. |
| Session modes | Full is exactly 90 minutes; drill defaults to 30 minutes and persists both named mode and effective duration. | A named accelerated mode meets the requirement without falsely presenting a shortened run as an authentic assessment. |
| State authority | Per-attempt `session.json` is authoritative; `events.jsonl` is immutable history; `STATUS.md` and context are generated views. | This separates reliable automation data from human-readable status. |
| Candidate/agent boundary | Candidate code remains in an isolated attempt; coaching is non-executable and excluded from grading; instructions constrain agents to coaching unless help is explicitly requested. | Same-user local access cannot technically prevent edits, so an operational boundary is honest and testable. |
| Scoring | Run each fixture `test_group_N` independently and report total passes plus contiguous reach. | This preserves the existing partial-credit behavior and makes gaps visible. |
| Assessment scope | Start with frozen `file_storage`; design an assessment registry seam but do not invent a second fixture. | It creates reusable architecture without expanding approved content. |
| Upstream/vendor material | `FETCH_ONLY` is resolved: retain one manifest-declared, hash-pinned fetch set in an ignored cache and prohibit vendor bytes from Git history. `solution/test_simulation.py` is explicitly excluded as a verbatim upstream file. | The upstream has no license record, so copying or publishing its bytes is not an available migration option. |
| Legacy and product READMEs | The current explore `README.md` is user-authored and included at `docs/legacy/explore-README.md`; `PROJECT/README.md` is new product documentation. | The manifest, not a categorical filename rule, records ownership and destination. |

## Implementation Investigations, Not Planning Blockers

1. Run the migrated fixture on the pinned Python baseline and explicitly
   document the optional `numpy`/`sortedcontainers` setup required by its
   starter. The simulator core and its tests should remain standard-library
   compatible.
2. Verify macOS/Linux lock behavior, interrupted-write recovery, and atomic
   workspace rollback under injected filesystem failures in tests; define a
   supported Windows policy only if cross-platform support is adopted.
3. Prove candidate scoring starts with a sanitized environment, empty
   `PYTHONPATH`, and selected-attempt working directory, so project and
   reference modules cannot leak into evaluation.
4. Verify the staged-and-HEAD vendor-boundary scanner is installed for both
   pre-commit and pre-push and covers every manifest-known vendor hash and
   forbidden vendor path.
5. Confirm whether the old exploration directory can be retired after
   checksum-verified transfer. The migration task must retain a redirect or
   archival record until campaign work-item links are updated.

These investigations have concrete owners and acceptance criteria in the
migration and verification tasks; none changes the approved product shape.
