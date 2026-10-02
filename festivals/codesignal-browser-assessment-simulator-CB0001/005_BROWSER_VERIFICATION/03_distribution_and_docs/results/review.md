# Independent distribution sequence review — approved after remediation

Fresh Cursor Terra High session `4d71d24d-5a30-4f7f-960d-2a4bfc8fe383`, model
`gpt-5.6-terra-high`, reviewed the actual 12-file working-tree diff from
`83b76f7` (including committed `b61d136`) after passing final testing. It read
the sequence goal, project rules, testing evidence, diff and surrounding code.
It did not edit or run tests/build/browser commands. Review command used
`cursor-agent -p --trust --mode ask --model gpt-5.6-terra-high` with explicit
base, scope and boundary instructions. Its subordinate additional findings are
being retrieved; no inaccessible chat artifact is treated as evidence.

## Findings and current dispositions

1. **Major — scan-cap handling.** `network_guard.mjs` returns after 100 scans;
   an additional synthetic intercepted response can be marked covered without
   a scan or violation. Preserve the bound, but record a fail-closed synthetic
   budget-exhausted violation without examining/retaining the extra body. Add a
   causal cap regression. Accepted for narrow remediation.
2. **Major — request correlation (coordinator independently reproduced).**
   `matchingNetworkRequest` chooses the earliest non-retired same method/URL,
   including an earlier ordinary request. A read-only Node diagnostic invoked
   the actual function extracted from the current file: with ordinary request
   sequence1 and intercepted request sequence2, it selected sequence1 both when
   sequence1 was settled and when it was still in flight. Marking that ordinary
   request as intercepted then suppresses its response scan; the intercepted
   response may instead receive a duplicate scan. Filtering settled requests
   alone does not fix the in-flight case. Accepted; require a meaningful mixed
   ordinary/intercepted same-URL regression and accurate correlation.
3. **Minor alleged falsy-JSON mismatch — withdrawn by reviewer.** The
   reviewer suggested default JSON MIME should use presence rather than
   truthiness. The installed pinned Playwright `_innerFulfill` at
   `webui/node_modules/playwright-core/lib/coreBundle.js:59800` itself uses
   truthiness after serializing based on presence. The current normalizer matches
   that behavior. The same reviewer checked the installed code and explicitly
   retracted this finding on follow-up. No compatibility change is warranted.
4. **Minor — missing wheel preflight.** `scripts/packaging_support.py` probes
   setuptools/pip/venv and optionally build, but not wheel. With an older supported
   backend this can accept an interpreter that fails the documented no-isolation
   wheel build. Accepted: align capability discovery/error guidance and add
   meaningful rejection/fallback checks.

## Non-defect evidence limits raised by review

- Wheel proof excludes checkout imports/CWD and Node runtime PATH, not arbitrary
  same-user filesystem reads. The injected source-root string supports assertions;
  it is not an OS access-control boundary. No product use or reachable leak was
  found. Preserve this limitation explicitly rather than claiming a sandbox.
- Archive checks combine forbidden-path rules and exact static asset hashes;
  they do not constitute an exhaustive content allowlist for arbitrary future
  Python modules. Current source/provenance review remains necessary alongside
  package checks. No actual FETCH_ONLY package content was identified. A narrow
  reachable gap is accepted for remediation: `resources/*.json` package data can
  include an unexpected innocuous-named resource that passes the blacklist.
  Restrict non-static runtime resources to declared metadata and test both wheel
  and sdist rejection with synthetic archives; this does not assert arbitrary
  future Python source content is automatically proven safe.

The follow-up review also independently confirmed the stale completed-request
correlation defect. Coordinator's in-flight case extends the same finding and
requires more than a settled-request filter. Primary guard remediation is a fresh
Cursor Sol High session; packaging preflight/resource checks are assigned to a
separate Cursor Terra High session with disjoint ownership and no build/browser
commands. Final coordinator verification waits for both agents to exit.

No critical finding was reported. Documentation lifecycle/commands, installed
imports/CWD/PATH isolation and fixed-point scan draining were assessed positively.

## Final independent re-review

The same independent Cursor Terra High reviewer was resumed after all workers
exited and final canonical (283 + 4), installed-wheel (170), checkout browser
(170), asset/build and staged provenance checks passed. It reviewed all 14
sequence files from `83b76f7`, including the staged new packaging test. No edits,
tests, builds, browser runs or additional delegation were performed by this
reviewer. Command: `cursor-agent -p --resume
4d71d24d-5a30-4f7f-960d-2a4bfc8fe383 --trust --mode ask --model
gpt-5.6-terra-high`, with explicit final scope and finding-disposition instructions.

**Disposition: approve the distribution-sequence iteration; no remaining
confirmed blocker.**

- Cap: resolved at guard1238–1244, with causal 100/101 response regression at
  harness402–450. No extra-body scan/retention; bounds preserved.
- Correlation: resolved at guard1263–1307 with issued one-use UUID markers and
  synthetic/method/type/URL/status checks. Settled, in-flight and independent
  response cases are asserted at harness454–611.
- Wheel preflight: resolved at packaging_support12–55 and runner350–354. Real
  isolated prerequisite import rejection/acceptance is tested at packaging test77–134.
- Resource policy: resolved at runner90–113 and151–170. Synthetic wheel/sdist
  direct and nested resource rejection/acceptance is tested at packaging test140–207.
- Falsy JSON: remains withdrawn; pinned semantics preserved.

Reviewer found no privacy, FETCH_ONLY, wheel-isolation, scan-bound, drain or
documentation regression. Non-OS-sandbox and future arbitrary-Python-content
limits remain explicit boundaries, not current defects. No P0/P1 feature or
material finding was deferred.
