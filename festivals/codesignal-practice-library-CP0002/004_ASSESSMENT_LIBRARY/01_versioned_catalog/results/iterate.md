# Iteration on review findings — 004/01_versioned_catalog

All accepted findings from results/review.md are done.

## F1 — symlink rejection is now proven, not inspected

New test `test_symlinked_packaged_content_is_rejected_at_every_level`: a
symlinked prompt, starter and manifest, a symlinked exercise directory, and a
symlinked intermediate `assessments/` directory each fail before `attempts/`
exists; a restored package then starts normally.

## F2 — every directory segment is checked

`PackagedOriginalProvider._directory` walks each segment of the input directory
below the resources root and rejects a symlink or non-directory at any level.

## F3 — docs wording

The "Input providers" section now states that the shared `attempts/` root and
its lock file may already exist when validation refuses a start; no attempt,
staging, journal or marker is written.

## F4 nit — archive directory shape

`run_packaged_browser.py` validates the bundled assessment directory name with
the same segment regex the registry uses, so `..` and dot-prefixed names are
rejected by shape; the allowlist test now includes both.

## Verification after iteration

    python3 -m unittest tests.test_input_providers tests.test_catalog_distribution tests.test_packaging_support   26 tests, OK
    just check unit                                                                                             445 tests, OK (1 skipped)
    python3 -m unittest tests.test_documentation                                                                OK
    git diff --check                                                                                            clean

Browser and frontend suites were not rerun: no browser asset, route body or
frontend file changed in this iteration (a provider path check, a script regex,
docs and tests).
