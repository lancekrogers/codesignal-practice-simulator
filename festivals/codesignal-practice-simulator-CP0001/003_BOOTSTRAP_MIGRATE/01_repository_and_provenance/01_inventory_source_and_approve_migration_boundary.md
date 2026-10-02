---
fest_type: task
fest_id: 01_inventory_source_and_approve_migration_boundary.md
fest_name: inventory_source_and_approve_migration_boundary
fest_parent: 01_repository_and_provenance
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-08T16:23:47.52721-06:00
fest_updated: 2026-09-08T18:46:30.055715-06:00
fest_tracking: true
---


# Task: 003.01.01 — Inventory Source and Approve the Migration Boundary

## Objective

Create reproducible preflight evidence that permits transfer only of
non-verbatim user-authored assets. Do not create a project, remote, cache, or
staging copy.

## File anchors

Inventory every regular file under `SOURCE`. The manifest and immutable
preflight/provenance records are created only in this task's `results/`
directory. `PROJECT` must remain absent.

## Ordered implementation steps

1. Compare each source file with the exact upstream repository
   `PaulLockett/CodeSignal_Practice_Industry_Coding_Framework` at `6aab304`.
   Record its source path, byte length, SHA-256, classification, and reason.
2. Include only simulator, study, notes, scripts, and solution files proven
   user-authored and non-verbatim. Each included record has one normalized,
   unique, safe project-relative destination. Classify the current explore
   `README.md` individually as user-authored and include it at
   `docs/legacy/explore-README.md`; the root product README is newly authored.
   Never exclude a file merely because it is named README.
3. Classify every exact upstream/vendor file as `exclude` with
   `destination_path: null` and SHA-256. Only the separately enumerated
   seven-record fetch set receives a cache-relative path: upstream `README.md`
   represented locally as `assessment/vendor-readme.md` and the six
   `assessment/file_storage/{level1.md,level2.md,level3.md,level4.md,simulation.py,test_simulation.py}`
   files. Verbatim `solution/test_simulation.py`, upstream
   `requirements.txt`, and every other exact upstream match have
   `cache_path: null`. Generated files and `.workitem` are also excluded with
   null destinations.
4. Record exactly one complete seven-record fetch set in the manifest:
   upstream `README.md` → cache `vendor-readme.md`, and upstream
   `practice_assessments/file_storage/{level1.md,level2.md,level3.md,level4.md,simulation.py,test_simulation.py}`
   → cache `assessment/file_storage/{level1.md,level2.md,level3.md,level4.md,simulation.py,test_simulation.py}`,
   each below `.cache/codesignal-fixtures/6aab304/`, with source path, cache
   path, and SHA-256. Record upstream URL/commit, `licenseInfo: null`, the
   `/license` 404, expected fetch paths/hashes, and exact
   `license decision: FETCH_ONLY` in `assessment-provenance-draft.md` and
   `migration-preflight.md`.
5. Atomically create the three canonical evidence files only when absent.
   `PASS` requires the exact FETCH_ONLY decision, null destinations for every
   vendor record, safe mappings for every included record, and complete hash
   coverage. Otherwise record `BLOCKED`.

## Error paths

An unknown classification, unsafe/duplicate included mapping, vendor
destination, absent hash, changed source, or any decision other than
`FETCH_ONLY` is blocking. Do not compensate by copying an upstream file.

## Do-not-mutate boundaries

Do not create or modify PROJECT, any GitHub resource, source content,
campaign files, or a fixture cache. In particular, do not copy
`assessment/vendor-readme.md`, `assessment/file_storage/**`,
`solution/test_simulation.py`, or `requirements.txt`.

## Verification and evidence

```sh
SOURCE="/workspace/campaign/workflow/explore/codesignal-industry-coding-framework"
FESTIVAL="/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001"
EVIDENCE="$FESTIVAL/003_BOOTSTRAP_MIGRATE/01_repository_and_provenance/results"
MANIFEST="$EVIDENCE/migration-manifest.json"
PREFLIGHT="$EVIDENCE/migration-preflight.md"
set -euo pipefail
test -d "$SOURCE"
test ! -e /workspace/campaign/projects/codesignal-practice-simulator
python3 - "$MANIFEST" "$PREFLIGHT" <<'PY'
import json, sys
from pathlib import Path
manifest, preflight = map(Path, sys.argv[1:])
data = json.loads(manifest.read_text())
assert data["schema_version"] == 2
assert data["upstream"]["commit"] == "6aab304"
assert data["license_decision"] == "FETCH_ONLY"
for record in data["files"]:
    if record["classification"] == "vendor":
        assert record["decision"] == "exclude"
        assert record["destination_path"] is None
        assert record["sha256"]
    elif record["decision"] == "include":
        path = Path(record["destination_path"])
        assert not path.is_absolute() and ".." not in path.parts
assert preflight.read_text().rstrip().endswith("preflight manifest: PASS")
fetches = data["fetches"]
expected = {
    ("README.md", "vendor-readme.md"),
    *{
        (f"practice_assessments/file_storage/{name}",
         f"assessment/file_storage/{name}")
        for name in ("level1.md", "level2.md", "level3.md", "level4.md",
                     "simulation.py", "test_simulation.py")
    },
}
assert len(fetches) == 7
assert {(item["upstream_path"], item["cache_path"]) for item in fetches} == expected
assert all(item["sha256"] for item in fetches)
fetch_source_records = {
    "assessment/vendor-readme.md",
    *{
        f"assessment/file_storage/{name}"
        for name in ("level1.md", "level2.md", "level3.md", "level4.md",
                     "simulation.py", "test_simulation.py")
    },
}
for record in data["files"]:
    assert bool(record.get("cache_path")) == (record["source_path"] in fetch_source_records)
PY
```

## Definition of done

- [ ] The manifest separates safe tracked user-authored mappings from excluded
  vendor paths/hashes.
- [ ] The seven-record fetch set and user-authored explore README mapping are
  explicit; verbatim `solution/test_simulation.py` is excluded, never fetched
  implicitly.
- [ ] The no-license finding and `FETCH_ONLY` decision are explicit.
- [ ] PASS is impossible with a vendor destination or a non-FETCH_ONLY decision.
- [ ] No source, project, cache, remote, or campaign content changed.
