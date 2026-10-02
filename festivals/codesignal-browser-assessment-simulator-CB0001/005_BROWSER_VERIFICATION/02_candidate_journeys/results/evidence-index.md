# Candidate-journey evidence index

Baseline project commit: `be5389b`; this sequence adds focused synthetic
journeys, HTTP/source rejection checks, and the Monaco bracket-matching
contribution with rebuilt local assets. This index proves the candidate
sequence, not completion of the distribution or release phases.

## Reproduction commands

Run from the linked project root; browser commands retain all default
privacy-safe reporters and the locked Chromium configuration.

```sh
npm --prefix webui run test:browser
npm --prefix webui run test:browser -- tests/candidate_journey.spec.mjs --repeat-each=3
npm --prefix webui run test:browser -- tests/actions.spec.mjs tests/accepted_journeys.spec.mjs tests/fresh_findings.spec.mjs tests/source_terminal.spec.mjs tests/browser_continuity.spec.mjs
npm --prefix webui run test:browser -- tests/accessibility_security_offline.spec.mjs tests/shell_layout.spec.mjs
python3 -m unittest tests.test_lifecycle tests.test_rendering -v
python3 -m unittest tests.test_web_server_static tests.test_web_server_source tests.test_web_server_safety tests.test_web_server_lifecycle -v
python3 scripts/check_assets.py
```

Focused results: candidate repeat 15 passed; lifecycle browser group 33 passed;
accessibility/security group 11 passed; lifecycle/rendering Python 32 passed;
web-server Python 21 passed. The full browser result is recorded below when
complete. `regression-checkpoint.md` records the passing canonical Python,
legacy, and interpreter checks and the failed concurrency experiment.

To isolate a row below, use `npm --prefix webui run test:browser --
tests/<spec>.spec.mjs` with the named spec. Python rows identify the corresponding
`python3 -m unittest tests.<module> -v` target. No private attempt is required:
all browser workspaces use synthetic seven-record fixtures, generated capability
tokens, and an injected clock starting at a fixed test instant. Only the public
API/CLI and explicit synthetic test controls mutate these workspaces.

## Required behavior

| ID | Executed assertion and source | Result / remaining evidence |
|---|---|---|
| B01 | `harness`, `browser_harness_setup`, and `shell_contract`: loopback launch, opener/no-open, read-only bootstrap, cleanup; `test_web_server_static`: token/opener/bind failures | Checkout launch proven; installed-wheel and clean-clone launch remain distribution task 02/03. |
| B02 | `candidate_journey`: visible full/drill durations, every first-party rule, no-pause confirmation; `shell_contract`: explicit start and no pre-start lifecycle | Focused passes; full-suite regression below. |
| B03 | `shell_layout`: desktop/narrow pane geometry, sticky actions and keyboard order; `shell_contract`: title/timer/save state | Existing real-browser assertions reused, not inferred from a build. |
| B04 | `navigation`: four distinct prompts, Description/History/Rules/Info, keyboard roving, source preservation | Public selected-prompt and candidate-history views checked. |
| B05 | `candidate_journey`: computed Python token colors, automatic brackets, persisted indentation; `editor`/`editor_settings`: find/undo/settings, local workers and preference reload | Added test passed three consecutive runs after token-render readiness correction. No claim of zero-delay input behavior before tokenization. |
| B06 | `source_save`: debounced save/reload, stale ETag reload/copy, exact content; `test_candidate_document_core`/`models`: CAS, atomic replacement and limits; `test_web_server_safety`: invalid UTF-8 and source symlink | Focused browser and HTTP boundaries pass; document-service baseline canonical checks passed. |
| B07 | `accepted_journeys`: real injected expiry disables mutations; `source_terminal`: delayed save cancellation; `fresh_findings`: authoritative time and foreign-attempt snapshot rejection | Deadline/lifecycle authority verified through server envelopes, not browser-local time alone. |
| B08 | `actions`: passing/failing four-group results, candidate failure versus HTTP failure, fixed bounded evidence and exact source-before-test ordering; `test_web_server_evaluation` | Score data remains separate from transport/internal failure. |
| B09 | `actions`: active-browser confirmation/cancel, exact source flush and one evaluation; `accepted_journeys`: API timeout submission, repeat session/score/source equality and one scorer call | API/CLI timeout finalization is proven, not an expired-browser Submit action. The expired browser intentionally remains read-only. Existing active-browser repeat/restart coverage passes. |
| B10 | `candidate_journey`: exact attempt identity, saved source and deadline after refresh and process restart; `shell_contract`/`fresh_findings`: bad/stale selection handling | Durable recovery asserted independently of transient save-label text. |
| B11 | `accessibility_security_offline`: capability/Origin/method/body/UUID/ETag, headers/CSP/no CORS, forbidden routes; `test_web_server_static`/`source`: duplicate headers/keys, size and query boundaries | Direct loopback HTTP rejections and existing API regressions pass. |
| B12 | Shared `network_guard`, `editor`, `navigation`, `source_save`, `browser_continuity`, and static/provenance checks: forbidden sentinels, no arbitrary content routes, safe response envelopes | Synthetic boundary evidence only; no real FETCH_ONLY content read or retained. |
| B13 | `browser_continuity`: public CLI context schema, STATUS, lifecycle/score/events, non-executable coaching excluded from source/read/scoring surfaces; `test_web_continuity` | Browser and CLI derived state stay synchronized; same-user policy is not represented as a sandbox. |
| B14 | Shared offline guard plus `editor`: local bootstrap/Monaco/workers; Python 3.10/3.11/3.12/3.14 regression runs; `check_assets`: 13 integrity-checked assets | Checkout offline/runtime and interpreter evidence pass. Wheel-only/no-Node and clean-clone evidence remain distribution work. |
| B15 | `candidate_journey`: independent SHA-256 links, exact current buffer/ETag, injected timestamps; `source_save`: candidate-only preview/restore; document lifecycle tests: bounded history | Content-derived hashes, not hash-shaped strings, are compared. |
| B16 | `source_save`: explicit reset/restore and operation locks; `source_terminal`/`accepted_journeys`: terminal locks; document lifecycle tests: own baseline and finality | Existing focused save tests and lifecycle coverage pass. |
| B17 | `navigation`/`shell_layout`: four groups, distinct prompts, reached/completed presentation and stable source | Local practice results remain explicitly non-official. |
| B18 | `shell_layout`: keyboard focus outline, reduced-motion computation, tab order, narrow layout, modal containment/opener restoration; `navigation`/`actions`: roving and live/result semantics | Added computed checks and existing real keyboard journeys pass. |
| B19 | Complete default Playwright command above plus direct HTTP probes, candidate-failure, expiry, repeat-submit, and CLI continuity specs | Full result below; failure diagnostics remain privacy-safe. |
| B20 | Existing `test_documentation`, README, CLI contract and agent safety checks in canonical suite | Existing documentation baseline passes. Final operating instructions and command consistency remain distribution task 04; not claimed complete here. |

## Explicit exclusions

| ID | Enforcement / evidence |
|---|---|
| B21 | Local first-party simulator shell and declared Monaco assets/licenses; no copied CodeSignal branding/page assets. Static manifest/provenance checks and source review enforce the package boundary. No pixel-identical claim. |
| B22 | Fixed local bootstrap/API routes, no accounts/invitations/cloud/video/proctoring service. Permissions policy denies camera and browser networking is same-origin only. |
| B23 | Python-only editor, registered candidate source service, no arbitrary shell/file/upload/proxy routes. Direct rejection matrix and source-CAS tests enforce this boundary. |
| B24 | Four-group local practice evidence is labeled as such. No claimed official hidden cases, score prediction or remote CodeSignal integration; safe-result tests reject raw scorer diagnostics. |
| B25 | Attempt-local bounded revision history only. No keystroke replay or collaboration endpoint; websocket/network guard and fixed route table remain unchanged. |

## Failure dispositions and evidence hygiene

- Task 01 harness defects: fresh-entry helper used for reconnect, stale save-label
  observation, hash-shape-only assertions, and unready token reads. Corrected
  with reconnect state checks, public-source polling, independent content hashes,
  and computed token readiness. Small reproducer and three whole journey repeats
  passed. See `task01.md` and `task01-review.md`.
- Task 03 harness correction: the new focus test initially assumed an extra Tab
  stop. Corrected to the actual radio-group/start order; focused suite passed.
- Full-suite task-02 harness correction: the timeout-submit test checked final
  reconnect visibility immediately after reload, before asynchronous bootstrap
  had resolved. The first full run finished 157 passed, 1 failed, 2 skipped
  (serial descendants). It now waits for either the reconnect action or the
  submitted presentation before choosing the action. Small repeated reproducer
  and full rerun are recorded below.
- Coordinator verification misuse: concurrent full interpreter suites shared
  setuptools output. Failed runs remain recorded; serial 3.10/3.11 reruns passed.
  Do not treat those failed runs as passing matrix evidence.
- Packaging/clone/docs gaps above are pending planned work, not silently passed
  or deferred P0/P1 behavior. The synthetic-only clone instruction conflicts
  with strict canonical fixture-cache hashes; an operator decision is pending.
- Resolved failure traces are not release evidence. Successful outputs are
  removed, with only aggregate Markdown records retained. Default reporters
  sanitize diagnostics during execution; no post-hoc sanitizer is used to make
  an artifact or test assertion pass.

## Full browser regression

Final `npm --prefix webui run test:browser`: 160 passed, no skips, exit 0.
Before that full rerun, the corrected timeout-submit case passed three
consecutive runs using `--grep 'expired attempt accepts' --repeat-each=3`.
The final canonical check also passed 276 Python tests without skips, four
explicit end-to-end tests, legacy/provenance checks, metadata/type checks,
compilation, all 13 static assets, and whitespace checks.

Retained Markdown was scanned for full capability fragments, private-key/token
patterns, and synthetic source excerpts; no matches remained. Final staged
`git-boundary` and `tracked` manifest verification passed. The verifier has no
`staged` scope: its `git-boundary` scope explicitly checks the staged index.
