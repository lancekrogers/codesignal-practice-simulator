# Independent security/provenance review

Cursor CLI, Sol High, read-only, no subdelegation. HEAD remained
`62d950c8cdcf5d79764f2bf5a27ffd571e0910e3`; no execution or edits. The separate
UI reviewer temporarily added an untracked probe; tracked files stayed unchanged.

## Decision: NO-GO pending scorer availability remediation

`scoring.py:_collect_bounded_output` drains a nonblocking pipe in an unbounded
inner loop before checking its deadline. A sustained stdout/stderr writer can
keep the pipe readable and starve timeout/process termination. Test/submit hold
action/attempt locks, so lifecycle observation and finalization can also wait.
Memory is bounded but execution time is not structurally bounded.

Reviewer classified this Medium security severity, blocking a P0 requirement:
B08 fails, B07/B09 availability indirectly affected, B19 lacks a sustained-output
regression. Require bounded drain/deadline checks plus synthetic sustained-output
tests covering elapsed time, child cleanup, later groups, and safe browser errors.
Coordinator must validate reproduction and remediation; no final approval yet.

Otherwise source review passed loopback/token/Origin, fixed methods/routes,
request/response bounds, CSP/security headers, absent CORS permission, fixed
candidate path/CAS/atomicity/finality/symlink checks, history ownership, scorer
envelopes, static integrity, frontend lock integrity and notices. No reachable
protected-content or arbitrary-path endpoint found. B06 and B10–B14 pass within
documented same-user non-sandbox threat model; B21–B25 exclusions respected.

Low non-blocking reproducibility observation: Python build requirements use
ranges. Record/constrain the provisioned final builder rather than claiming
arbitrary future resolver versions produce identical archives. Final remote
reproduction remains required. Supplied Phase005 evidence was not rerun here.
