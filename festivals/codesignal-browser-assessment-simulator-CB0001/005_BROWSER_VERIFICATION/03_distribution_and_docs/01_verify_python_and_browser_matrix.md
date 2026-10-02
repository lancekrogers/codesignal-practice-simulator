---
fest_type: task
fest_id: 01_verify_python_and_browser_matrix.md
fest_name: verify python and browser matrix
fest_parent: 03_distribution_and_docs
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:31.887518-06:00
fest_updated: 2026-09-10T11:20:34.144102-06:00
fest_tracking: true
---


# Task: verify Python and browser matrix

## Objective

Run the canonical Python, package, browser, provenance, and legacy checks across the interpreters and browser version available for release.

## Requirements

- [ ] Run the full unittest suite, end-to-end suite, legacy checks, static build/check, and complete Playwright suite with network denial.
- [ ] Execute under available Python 3.10+ interpreters and record unavailable versions rather than claiming unsupported evidence.
- [ ] Run provenance/content scans that reject FETCH_ONLY bytes, secrets, traces, caches, node_modules, arbitrary external URLs, and official hidden-test claims in tracked outputs.

## Implementation

Follow these steps in order:

1. Run `python3 -m unittest discover -s tests -v`, `python3 -m unittest tests.test_end_to_end -v`, `python3 scripts/run_legacy_checks.py`, and `just verify` from the project root.
2. For each available interpreter, run the same focused/full commands and `python -m build`; run `npm run check` and `npm run test:browser` from `webui/`.
3. Use the existing migration/provenance scripts as the baseline and add browser/static manifests to the scan without reading or copying fixture bytes.
4. Record command, interpreter/browser version, result, and temporary artifact cleanup in the sequence results directory if one exists.

### Safety and content isolation

Never run verification against a user's live attempt or external network. Do not commit output logs that contain tokens, source, reference content, or machine-specific absolute paths.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] All available interpreter/browser/canonical commands pass or have an explicit blocker and owner.
- [ ] Provenance/content scans pass with no prohibited tracked artifacts.
- [ ] Version matrix evidence is reproducible from a clean temporary workspace.
