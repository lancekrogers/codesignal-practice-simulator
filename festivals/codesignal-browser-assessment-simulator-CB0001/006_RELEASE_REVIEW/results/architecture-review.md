# Independent architecture review

Cursor CLI, Terra High, read-only, no subdelegation. Reviewed clean commit
`62d950c8cdcf5d79764f2bf5a27ffd571e0910e3`; no tests or edits by reviewer.

## Decision: NO-GO pending B15 remediation

Confirmed material history-restoration defect: saves C0 → C1 → C2 → C1
collapse records by `new_hash` in candidate document history reconstruction.
The predecessor walk detects a repeated hash and stops, omitting older distinct
revisions from required history/restoration. No-op autosaves can also mask history.
Anchors: candidate_documents.py snapshot writes 173–190, history walk 276–296;
source_controller_runtime.ts autosave 136–160. Existing lifecycle and browser
history tests cover only distinct successive revisions.

Required: reproduce with synthetic data; preserve durable operation ordering
without conflating repeated content, deliberately handle uncommitted/orphan
records, and verify oldest retained revision restoration in unit and browser
regressions. Reviewer called this Medium severity and a material P1 requirement
failure. No release approval is claimed.

Otherwise, composition/service ownership, thin CLI/HTTP transports, durable
lifecycle, CAS/atomic candidate writes, and server-authoritative browser state
are coherent. Static coverage supports B01–B14 and B16–B20; browser fidelity and
security require their independent reviews. Phase005 execution evidence was
read, not rerun. Final remote clone verification remains a release action.

Optional non-blocking observations: web/resources.py combines several concerns
in 620 lines; the application RLock spans scoring and can delay status requests.
No speculative refactor is included in the required remediation.
