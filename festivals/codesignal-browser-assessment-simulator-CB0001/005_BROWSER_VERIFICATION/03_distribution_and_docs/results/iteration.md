# Distribution review iteration — complete

## Findings and dispositions

- Recurring fast mocked-response scan race and snapshot-only draining: replaced
  by bounded synchronous scanning and fixed-point drain; original failures,
  discarded deadlocking approaches and pre-review passes are preserved in
  `streaming-iteration.md` and `testing.md`.
- Same-URL ordinary/intercepted correlation: accepted major finding. Fresh Cursor
  Sol High `d5145c00-def0-42ea-9cfe-b67704b76442` replaces FIFO association with
  one-use exact synthetic-response coverage markers and metadata checks. Mixed
  settled/in-flight cases and independent mocks have focused browser coverage.
- Synthetic scan-budget exhaustion: accepted major finding. The 100-response
  bound remains; exhaustion records a violation without scanning the extra body.
  Final causal evidence belongs in `review-remediation.md`.
- Falsy JSON MIME allegation: withdrawn by the independent reviewer after
  checking pinned Playwright. No incompatible normalization change was made.
- Missing wheel preflight and unexpected package resources: Cursor Terra High
  `3b6ae5a4-fcfa-4e94-939d-6c8a106e0013` fixed prerequisite discovery/guidance and
  narrowed the new resource policy to declared runtime metadata. A draft wider
  archive metadata catalog was removed, not retained as new architecture.
- Prerequisite-test quality: Cursor Luna High
  `03caed8e-5000-4f94-b266-ab29115dc550` replaced a command-shape assertion with a
  real isolated import-presence test. Six tests pass under Python 3.10/3.11/3.12
  and 3.14; details in `packaging-review-remediation.md`.
- Wheel filesystem isolation and arbitrary future Python content: documented
  limits, not current product defects. Import/CWD/PATH checks are not an OS
  sandbox; package resource/static checks complement, not replace, source and
  provenance review. No actual fetched content in artifacts was found.
- Keyboard roving failed once before this review. Focused, serial and full reruns
  passed without changing runtime/test behavior. Its exact cause remains unknown;
  see `keyboard-second-opinion.md` and `streaming-iteration.md`. No retry or sleep
  was added to mask it.

No P0/P1 feature was deferred, no runtime transport/lifecycle behavior changed,
and no privacy reporter, content bound or fixture permission was relaxed.

## Final verification

All implementation agents exited before coordinator verification. Guard evidence
in `review-remediation.md` records 14 focused passes, causal old-FIFO failures
followed by marker passes, and one complete checkout browser run: **170 passed**.

- `ASSET_BUILDER=/private/tmp/cb0001-release.HTxOTs/builder/bin/python just verify`:
  exit 0, **283 Python tests**, **four explicit E2E tests**, 26 first-party spec
  tests, 12 staged tests, all four study levels and all tracked/cache/Git boundary
  checks passed. No skips. Python 3.14.6.
- `ASSET_BUILDER=/private/tmp/cb0001-release.HTxOTs/builder/bin/python python3 scripts/run_packaged_browser.py`:
  exit 0, **170 installed-wheel browser tests**, no skips, default reporters.
  Wheel imports/CWD/runtime PATH isolation, both console/module loopback launch
  probes, 13 asset hashes, seven synthetic fixture records and final temporary
  cleanup passed. No overlapping browser suite or editing agent was running.
  Archives: **94 sdist members**, **49 wheel members**, **14 static members**.
  The one additional sdist member is the new first-party packaging regression
  test; there is no new runtime resource or wheel member.
- `python3 -m compileall -q src tests scripts`, both changed JavaScript syntax
  checks, `npm --prefix webui run check`, and `git diff --check`: passed.
- All six packaging tests passed under Python 3.10/3.11/3.12/3.14. These are
  additional focused results, not a relabeling of the historical full matrix.
- Coordinator Node 26.7.0/npm 11.19.0; Playwright 1.63.0, locked Chromium
  153.0.8010.12 revision1243, macOS ARM64. No TypeScript-check claim is made.
- Fresh `npm --prefix webui run build` and `python3 scripts/check_assets.py`:
  passed. All 13 assets and manifest hash remained byte-identical to the prior
  reviewed build. The final wheel temporary root was removed. Only the intended
  ten documentation/test/verification files were staged; staged whitespace and
  Git-boundary provenance checks passed.

Before/after hashes matched for all five changed guard/packaging verification
files; there were no edits during the final run:

```text
network_guard.mjs 8bef84ab4821ff45b596954f898cbb47efbfb776480e44dc2e90dc79ffbadbdb
harness.spec.mjs 44a497622d4273eadf44e4c3ff141605068ffef88bb4f26b8794a6f60c873e72
packaging_support.py ff83d816ef9352f35eee50b548290636bbd8464619b02b30bc3125b7a6af6971
run_packaged_browser.py 68e98e8af2165a6139039e4919a937f278e268df829a317fa705ed8620d76551
test_packaging_support.py 2a459f5eccefcdb175aab85e95c70725d6aa005992bb93fef6e653e12b00b784
```

Independent Cursor Terra High re-review approved the entire staged sequence diff
with no remaining confirmed blocker; see `review.md`. All accepted findings are
resolved, the incorrect JSON finding was withdrawn, and scoped evidence limits
remain explicit. Final staged whitespace/provenance passed. This iteration is
ready for the required Festival commit.
