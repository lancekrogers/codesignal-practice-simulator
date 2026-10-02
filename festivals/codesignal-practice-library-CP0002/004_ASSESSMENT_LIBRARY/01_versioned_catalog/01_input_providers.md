---
fest_type: task
fest_id: 01_input_providers.md
fest_name: input_providers
fest_parent: 01_versioned_catalog
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-11T14:32:19.009153-06:00
fest_updated: 2026-09-12T19:59:38.861767-06:00
fest_tracking: true
---


# Task: input_providers

## Objective

Extend assessments, workspace, and application with a narrow validated input-provider boundary retaining unchanged File Storage cache validation while adding packaged-original inputs pinned at attempt creation.

## Requirements

- [ ] Build on 003/01/02_creation_identity, which already delivered the File
  Storage identity (manifest hashes + runner contract, staged-byte verification),
  the v1 legacy identity adapter and v2 creation. Move that derivation behind the
  provider interface without changing the File Storage digest value; assert
  equality with a pre-refactor fixture. Never synthesize a digest to satisfy a field.
- [ ] Keep read-only metadata/review independent of the current registry (already
  required of 003/01/04 and 003/03); missing definitions block continued scoring,
  not stored-result visibility. Re-test both paths with packaged originals.

- [ ] Read and apply **D003_assessment_catalog.md** (pinned-fetched vs packaged-original providers, validation before staging).
- [ ] Extend `src/codesignal_practice_simulator/assessments.py` near `:56` and `:88` with provider kind, content version, digest, and runner contract metadata.
- [ ] Extend `src/codesignal_practice_simulator/workspace.py` near `:116` and `:329` to resolve selected provider before staging; pin version/digest on new attempts.
- [ ] Extend `src/codesignal_practice_simulator/application.py` near `:343` attempt creation to require validated inputs before mutation or abandonment commit intent.
- [ ] Detect missing/tampered resources before any new attempt; originals must work without File Storage fetch.
- [ ] Test missing/tampered packaged resources, original startup without legacy fetch, and legacy File Storage path unchanged.

## Implementation

1. **Provider interface** — Define `InputProvider` with `validate()`, `stage_to_attempt()`, and declared allowlisted candidate-facing files only.
2. **pinned-fetched** — Wrap existing cache/provenance validation and the 003/01/02 identity function unchanged for File Storage assessments.
3. **packaged-original** — Read bundled resources from installed package paths with declared hash verification; compute identity with the same canonical `assessment-content/v1` digest input and verify staged bytes before publish.
4. **Attempt pinning** — Creation already persists assessment id, content version, digest and profile (003/01/02); route both provider kinds through that path.
5. **Failure before mutation** — Missing files, wrong digest, unsupported profile → error before workspace staging or restart commit intent.
6. **Tests** — Add `tests/test_input_providers.py` for tampered package manifest, offline original staging, legacy fetch requirement still enforced for fetched assessments.

### Affected files

- `src/codesignal_practice_simulator/assessments.py`
- `src/codesignal_practice_simulator/workspace.py`
- `src/codesignal_practice_simulator/application.py`
- `tests/test_input_providers.py`

### Negative cases to prove

- Tampered bundled hash rejected before attempt directory mutation.
- Original exercise does not require network or legacy cache directory.
- Wrong profile or missing prompt file → deterministic validation error.
- Legacy File Storage validation behavior unchanged for existing assessments.

### Commands and evidence

```bash
python3 -m unittest tests.test_input_providers -v
```

## Done When

- [ ] All requirements met
- [ ] Both provider kinds validate before staging and pin identity on new attempts
- [ ] Offline original and legacy fetch tests pass with evidence recorded
