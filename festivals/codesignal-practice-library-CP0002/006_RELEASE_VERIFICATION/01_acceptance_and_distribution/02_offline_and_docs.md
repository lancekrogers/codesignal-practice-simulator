---
fest_type: task
fest_id: 02_offline_and_docs.md
fest_name: offline_and_docs
fest_parent: 01_acceptance_and_distribution
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-11T14:32:19.009153-06:00
fest_updated: 2026-09-13T00:00:30.399881-06:00
fest_tracking: true
---


# Task: offline_and_docs

## Objective

Build/rebuild assets, install wheels outside checkout, prove original exercises run offline without legacy cache, validate File Storage with explicit setup, run canonical/provenance checks, and update README/CLI/API/safety docs with actual commands and negative-path evidence.

## Requirements

- [ ] Document that new releases read v1/v2, old binaries need not read v2, and
  mixed-version writers in the same workspace are unsupported. Do not claim
  old-binary downgrade safety. Retain D005 approval before testing/shipping content.

- [ ] Satisfy **R11 distribution** and documentation deliverables from IMPLEMENTATION_PLAN 006/01/02.
- [ ] Build bundled frontend assets and Python wheel/sdist using project Just recipes (`just build assets`, `just build assets-check`, `just check wheel`—inspect current names before execution).
- [ ] Install wheel in clean temp venv **outside** project checkout with network disabled; complete each accepted original exercise offline without legacy cache.
- [ ] Verify File Storage assessments remain explicitly unavailable until fetch setup; test fetch path separately with documented setup steps.
- [ ] Run `just verify`, provenance/allowlist checkers, and record counts of bundled resources vs development-only exclusions.
- [ ] Update README, CLI/API docs, safety/troubleshooting for every new action (abandon, restart, history, review, retry) with actual command transcripts and unresolved limitations list.

## Implementation

1. **Asset build** — Run frontend build recipes; confirm assets packaged into wheel per 004/01 packaging rules.
2. **Offline install test** — Extend the existing packaged-browser harness to create a unique temporary venv outside checkout, install the exact built wheel using that venv's interpreter, block network, and run catalog/start/submit/review per accepted original. Never install into a global interpreter or reuse a fixed temporary directory.
3. **File Storage path** — Document and execute explicit fetch/setup; confirm originals still work when fetch cache absent.
4. **Provenance** — Run existing allowlist/manifest diff twice; compare resource manifests for determinism.
5. **Docs pass** — Update README quickstart, `docs/cli-contract.md`, safety section (symlink/path rejection, no candidate data in logs), troubleshooting for recovery-pending and legacy-unbound review.
6. **Evidence file** — Write `results/offline_and_docs.md` with commands run, exit codes, wheel filename, exercise count completed offline, and known gaps.

### Affected files

- `README.md`
- `docs/cli-contract.md` and related API/safety docs
- `006_RELEASE_VERIFICATION/01_acceptance_and_distribution/results/offline_and_docs.md`
- build/packaging scripts as exercised (read-only unless fixes required)

### Negative cases to prove

- Offline install without network cannot complete fetch-dependent assessment until setup documented.
- Second rebuild produces identical resource manifest hashes.
- Old attempt review readable after installing wheel that omits removed catalog version.
- Docs include at least one negative-path example per new action (conflict, stale, unavailable).

### Commands and evidence

```bash
just build assets
just build assets-check
just check wheel
just verify
just check frontend
# Offline install script documented in results/offline_and_docs.md
```

## Done When

- [ ] All requirements met
- [ ] Wheel installs and runs accepted originals offline with recorded command transcript
- [ ] Documentation updated with real commands, counts, negative-path examples, and unresolved limitations
