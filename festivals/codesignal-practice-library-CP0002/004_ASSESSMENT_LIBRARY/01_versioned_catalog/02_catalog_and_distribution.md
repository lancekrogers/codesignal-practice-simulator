---
fest_type: task
fest_id: 02_catalog_and_distribution.md
fest_name: catalog_and_distribution
fest_parent: 01_versioned_catalog
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-11T14:32:19.009153-06:00
fest_updated: 2026-09-12T20:08:27.578228-06:00
fest_tracking: true
---


# Task: catalog_and_distribution

## Objective

Replace the hardcoded catalog at `application.py:174`, expose metadata/readiness via fixed routes and CLI discovery, and extend packaging so originals ship in wheel/sdist while history review stays independent of installed definitions.

## Requirements

- [ ] Read and apply **D003_assessment_catalog.md** (catalog enumeration, version removal honesty, offline originals) and **D004_history_api_and_ux.md** (catalog GET route).
- [ ] Replace `src/codesignal_practice_simulator/application.py:174` hardcoded catalog with registry-driven enumeration including availability/setup reasons.
- [ ] Add catalog GET route and CLI listing with readiness flags (offline available vs fetch required).
- [ ] Extend `pyproject.toml` package resources and existing packaging allowlists/checkers for bundled original content.
- [ ] Keep history review readable when catalog version removed; do not rewrite old attempt metadata to current version.
- [ ] Test outside-checkout wheel discovery, removed versions, duplicate identity, and wrong profiles.

## Implementation

1. **Registry enumeration** — Read installed definitions with id, version, digest, description, four-level metadata, profiles, provider kind, readiness.
2. **HTTP/CLI catalog** — GET `/api/catalog` (or existing fixed route pattern) and CLI `list`/`catalog` command returning same shape.
3. **Packaging** — Add package-data entries and allowlist checks ensuring prompts/starters/tests/manifests included; exclude development solutions.
4. **Removal behavior** — Old attempts retain pinned identity; review shows stored metadata with explicit unavailable setup when definition missing.
5. **Tests** — Add packaging/discovery tests: build wheel, install in temp venv outside checkout, discover originals with network blocked; duplicate ID/version rejected at build or load time.

### Affected files

- `src/codesignal_practice_simulator/application.py`
- `src/codesignal_practice_simulator/web/routes.py`
- `pyproject.toml`
- packaging checker scripts (existing allowlists)
- `tests/test_catalog_distribution.py`

### Negative cases to prove

- Duplicate assessment id/version → build or registry load failure.
- Wrong profile on definition → rejected before catalog exposure.
- Removed version → old review still shows stored results with honest unavailable fields.
- Wheel installed outside checkout discovers bundled originals without legacy cache.

### Commands and evidence

```bash
python3 -m unittest tests.test_catalog_distribution -v
just check wheel
```

## Done When

- [ ] All requirements met
- [ ] Catalog is registry-driven with CLI/HTTP parity and packaged originals discoverable offline
- [ ] Packaging and discovery tests pass with command output recorded
