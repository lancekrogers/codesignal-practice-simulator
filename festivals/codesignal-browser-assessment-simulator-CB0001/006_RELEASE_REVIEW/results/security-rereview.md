# Security/provenance re-review of corrected commit

Independent Cursor Sol High, chat `1b009d63-ddaa-43d4-967e-12b1ae4ed9ea`,
read-only, no subdelegation/execution/edits. Initial/final clean exact commit:
`600c6cff0bd9428c6cf605e24085ea8729a475d2`.

## Implementation/security/provenance: GO

No unresolved material implementation finding. Both prior defects resolved:
ordered history preserves repeated-content predecessors and omits no-ops;
scorer reads once per loop, rechecks monotonic deadline, caps selector waits,
and retains bounded timeout cleanup ordering. Causal regression evidence valid.

History anchors: candidate_documents.py274–294; repeated/no-op, frozen-time,
order-gap,50-change retention, failed-publication orphan/retry and browser
oldest-restore tests. CAS/atomicity/ownership/symlink/finality/locks unaffected.
Scorer anchors: scoring.py322–378; deterministic always-readable failure,
real writer bounded return/reaping/later groups, safe HTTP envelope and responsive
subsequent time, and exited-parent inherited-pipe regression.

Important limit: exited-parent test proves bounded collector return/pipe close;
test cleanup, not collector, kills a surviving descendant. Acceptable within
the audited-Python child-creation rejection boundary, not an OS sandbox or
native/same-user containment promise. Four default10-second group deadlines
plus bounded cleanup overhead bound ordinary supported scoring execution.

B06–B14 boundaries rechecked and satisfied: fixed candidate document/CAS,
server lifecycle/expiry, isolated groups, exactly-once write-ahead submit,
restart/capability rotation,127.0.0.1/token/Origin/routes/headers/body bounds,
static/API allowlists without arbitrary content paths, derived safe coaching,
standard-library runtime/local assets. B19 focused evidence adequate; B21–B25
exclusions unchanged. Frontend locks/assets/notices/package provenance unchanged.

## Overall release: evidence gates pending

Reviewer withheld overall release approval pending exact600c wheel/browser,
fresh project/campaign clone, remote reproduction and delegated sign-off.
Prior b61 clone proof is not equivalent. No additional code fix requested.
At review time the wheel run was still underway; coordinator subsequently
recorded171passed in remediation-verification.md. Remaining actions must be
executed and supplied for final disposition, not assumed.

Recorded reproduction builder: Python3.14.6, setuptools84.0.0, build1.6.1,
wheel0.48.0. Build requirements use ranges; arbitrary future resolver versions
are not claimed byte-identical.
