# Browser verification evidence

## Approval state

All three implementation sequences have passed their testing, independent review,
iteration and commit work. The final distribution project commit is
`62d950c8cdcf5d79764f2bf5a27ffd571e0910e3`, created with `fest commit`; its worktree
is clean. This presentation submits phase005 evidence to the configured local
approval judge. Phase006 independent release review, publishing, and final remote
reproduction remain outstanding; no completed release is claimed here.

All four phase005 checkpoints subsequently received an **approved** verdict from
the configured `ob judge --quiet --model qwen3:8b` judge: phase goal, sequence
outcomes, quality and completeness. No manual approval, skip or override was used.

## Verified user outcomes

The complete synthetic browser suite verifies explicit entry/start, full/drill
timing, server-authoritative expiry, responsive pane layout, keyboard navigation,
Monaco editing/settings, durable autosave and stale-write recovery, bounded source
history/reset/restore, practice test results, confirmation and exactly-once submit,
refresh/process restart, and safe CLI/coaching continuity.

The per-requirement B01–B25 assertions and their test modules are indexed in
`../02_candidate_journeys/results/evidence-index.md`. That historical sequence
index intentionally left distribution evidence pending; the records below close
the launch/install/offline/clone portions of B01 and B14. Task04 closes B20 through
the updated README, CLI contract, agent safety, root policy and six documentation
regressions, with executable install/build proof in `task04-install-proof.md`.

Security checks exercise capability/Origin/header/path/method/body/UUID/ETag
rejections, symlinks, invalid UTF-8, safe result envelopes, no arbitrary content
routes, and forbidden-content scans. Browser network guards and installed Python
fixture socket checks are test-scoped evidence, not an OS or same-user sandbox.

## Harness and candidate sequences

- Harness checkpoint `be5389b`: deterministic synthetic workspaces, controllable
  clocks, role-first helpers, network denial, privacy-safe failure diagnostics,
  startup rejection of unsafe output paths, and successful-run artifact checks.
- Candidate checkpoint `83b76f7`: 160 complete browser cases, 276 Python tests,
  four explicit E2E tests, legacy/provenance, asset, and metadata checks passed.
- Sequence testing/review/iteration records under `../01_browser_harness/results/`
  and `../02_candidate_journeys/results/` preserve actual failures, fixes, reruns
  and independent Cursor reviews. No material finding was silently deferred.
- Timeout finalization is deliberately distinguished: active browser submission
  is tested; the expired browser is read-only and its Submit action is disabled.
  API/CLI finalization after expiry scores once; repeats and restarts preserve the
  stored result. The operating documentation must explain that fallback.

## Distribution and clean-clone proof

See `../03_distribution_and_docs/results/`:

- `testing.md`, `review.md`, `iteration.md`, `review-remediation.md`, and
  `packaging-review-remediation.md`: final **283 Python tests plus four explicit
  E2E**, **170 checkout browser tests**, and **170 serialized installed-wheel
  browser tests** passed without skips. All legacy/provenance, syntax, compilation,
  metadata/licensing, real archives, launch and cleanup checks passed. A fresh
  frontend build produced the identical 13 asset hashes. Independent Cursor Terra
  High re-review approved the complete sequence diff with no confirmed blocker.
  Earlier accepted scan-cap, FIFO-correlation, prerequisite and package-resource
  findings were corrected and have causal/negative regressions; no P0/P1 was deferred.
- `task01-matrix.md`: Python 3.10.20, 3.11.16, 3.12.13 and 3.14.6 each passed
  276 tests without skips, four explicit E2E cases, canonical legacy/provenance
  checks, and sdist/wheel builds. Python 3.13 was unavailable and is not claimed
  tested. Verification was performed on macOS, not every supported operating system.
- `task02-wheel.md` and `task02-review.md`: wheel runtime isolation and independent
  review. Installed imports/cwd exclude the checkout; runtime PATH excludes Node,
  npm and npx; both public entry points serve all 13 bundled assets. Full installed
  synthetic suite: 161 passed. Default artifact reporters remain enabled.
- `fixture-exception.md`: explicit operator approval for seven pinned hash-checked
  records in ignored temporary clone caches, solely for canonical verification.
  Existing caches and real attempts are not copied; browser tests stay synthetic.
- `task03-project-approved.md`: exact `b61d136` clean clone, editable console/module
  and web launch, seven pinned hashes, canonical 276 + 4 tests, checkout browser
  161/161 and installed-wheel browser 161/161. No tracked changes or real attempts.
- `task03-campaign-approved.md`: fresh campaign clone, only the simulator submodule
  initialized at reviewed `b61d136` through a temporary staged gitlink; canonical
  276 + 4, strict provenance and all asset hashes passed. No unrelated submodule
  was changed. Both owned clones were moved to Trash and original paths absent.

The campaign rehearsal is a local staged-pointer proof, not a claim that release
integration or remote verification already happened. Phase006 owns those actions.
The wheel's public console/module launch probes use an unmodified wheel and empty
workspace. Full lifecycle journeys use a separate injected synthetic fixture driver;
the two scopes are not conflated, and the pinned runtime manifest is not rewritten.

Manifest SHA256 for all 13 assets:
`19d284d6377c9f74db84fd4051116fc8834d2df090cb7dc8ef5c502fb14e48bd`.
Final archives contain 49 wheel members, 94 sdist members and exactly 14 static package
members including the Python package marker. Assets, license/provenance files and
worker bytes match the manifest; forbidden path and Git-boundary checks pass.
The additional sdist member since checkpoint `b61d136` is a first-party packaging
regression test, not runtime or fetched content. Undeclared non-static runtime
resources are rejected; future arbitrary Python content still requires source
and provenance review.

## Evidence precision

`npm --prefix webui run check` checks metadata, lockfile, notice snapshots and its
own Node syntax. It is not a TypeScript type checker. Historical shorthand about
“types” must not be read as a separate type-check result. esbuild build success and
executed browser behavior are the available frontend verification.

Earlier failed parallel Python runs shared build outputs and were rerun serially.
The first wheel rehearsal's streaming test failure passed three focused repeats
and subsequent complete suites, but later recurred at the distribution gate.
The resulting iteration replaces timing-dependent scans of harness-owned mocked
responses with bounded pre-fulfillment scans, checks effective JSON/header
semantics, and drains late-queued scans. Runtime streaming behavior and packaged
assets are unchanged. Final distribution testing and independent re-review passed.
A later keyboard-roving failure produced three downstream serial skips; its
20 focused repeats and 10-test serial file passed without a runtime change.
That failure is recorded as non-reproduced, not explained or causally fixed.
The original clone diagnostic lacked esbuild and
the pinned cache; locked npm setup fixed the former, and the approved narrow fetch
exception resolved the latter. One zsh wrapper used a reserved variable name; its
corrected full check passed. These failed rehearsals remain recorded rather than
being represented as successful runs.
