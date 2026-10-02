# Distribution review remediation

## Scope and dispositions

This bounded iteration changed only:

- `webui/tests/network_guard.mjs`
- `webui/tests/harness.spec.mjs`
- this result file

No runtime, fixture/cache, candidate/protected source, other pending
documentation, festival state, commit, or remote state was changed.

### Accepted finding 1: scan-cap exhaustion

Remediated. The response scan cap remains exactly 100. Each harness-intercepted
response beyond that cap now records a fail-closed
`scan-budget-exhausted` response-scan violation. The exhausted path does not
run eligibility or body consumption, allocate a scan accumulator, retain a
prefix, or emit a body diagnostic.

The negative browser regression fills all 100 scan slots, sends response 101
with a forbidden sentinel, and proves:

- exactly 100 diagnostics exist;
- response 101 produces the expected budget violation;
- no forbidden match is produced from the unexamined body; and
- neither diagnostics nor violations retain the sentinel.

### Accepted finding 2: FIFO request correlation

Remediated. URL/method FIFO matching and its pending counters were removed.
Each normalized intercepted fulfillment now receives a fresh UUID in a
harness-only response header. Coverage is consumed once, only from the exact
CDP response carrying that marker, and only after validating:

- the marker was issued and is still pending;
- the response is synthetic (`connectionId === 0`);
- request method and resource type match;
- request and response URLs match the expected URL; and
- response status matches.

Unknown, reused, ordinary, and independently mocked response markers do not
consume coverage and therefore proceed through the ordinary response policy.
Causal browser coverage includes an earlier settled ordinary same-URL request,
an earlier in-flight ordinary same-URL request, an independently mocked
same-URL response with an unissued marker, and repeated intercepted URLs.

### Other review dispositions

- Falsy JSON behavior was not changed. The existing Playwright-1.63-compatible
  truthiness check for default JSON MIME remains intact.
- The 64 KiB retained-prefix bound, default privacy reporters, offline denial,
  streaming behavior for ordinary responses, and fixed-point scan draining
  remain unchanged.
- This remains a harness policy and correlation mechanism, not an OS sandbox.
- No new dependency or transport rewrite was introduced; UUID generation uses
  `node:crypto`.

## Causal regression evidence

New regressions were run before implementation:

```text
npm --prefix webui run test:browser -- harness.spec.mjs --grep "fails closed past|settled ordinary|inflight ordinary"
3 failed
```

The cap failure was causal: the old guard returned silently and did not produce
the expected budget violation. The first drafts of the two mixed tests also
failed for fixture-specific setup reasons (cross-origin favicon denial, then
expected synthetic API 400s), so those failures are not claimed as FIFO
evidence. The tests were corrected to use same-origin synthetic API traffic and
declare the expected ordinary 400 responses.

With the corrected mixed tests, a bounded A/B substitution of the reviewed FIFO
method/URL behavior produced the causal failure:

```text
npm --prefix webui run test:browser -- harness.spec.mjs --grep "settled ordinary|inflight ordinary"
2 failed
```

The exact-marker implementation was immediately restored; no temporary FIFO
code remains. The same command then passed:

```text
npm --prefix webui run test:browser -- harness.spec.mjs --grep "settled ordinary|inflight ordinary"
2 passed
```

Combined cap and mixed regressions after restoration:

```text
npm --prefix webui run test:browser -- harness.spec.mjs --grep "fails closed past|settled ordinary|inflight ordinary"
3 passed
```

All four newly added remediation regressions, including the independently
mocked response:

```text
npm --prefix webui run test:browser -- harness.spec.mjs --grep "fails closed past|settled ordinary|inflight ordinary|independently mocked"
4 passed
```

## Final verification

Focused bounded, intercepted, repeated-URL, cap, mixed-correlation, independent
mock, JSON, unsupported-option, drain, length, streaming-failure, no-body, and
retained-prefix checks:

```text
npm --prefix webui run test:browser -- harness.spec.mjs --grep "scans only bounded|scans bounded intercepted|scans each repeated|fails closed past|settled ordinary|inflight ordinary|independently mocked|scans effective JSON|rejects unsupported intercepted|waits for response scans|does not retrieve bodies|fails closed when response stream|skips responses whose method|bounds retained prefix"
14 passed
```

Static metadata/lockfile/license check:

```text
npm --prefix webui run check
webui metadata, lockfile, and license checks passed
```

Owned-file syntax and whitespace check:

```text
git diff --check && node --check webui/tests/network_guard.mjs && node --check webui/tests/harness.spec.mjs
passed
```

The one authorized final checkout browser run, after code cleanup:

```text
npm --prefix webui run test:browser
170 passed
```

No further full suite was launched. Installed-wheel and canonical serial checks
remain for the coordinator after this worker exits.
