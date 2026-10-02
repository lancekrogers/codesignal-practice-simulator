# Iteration on review findings — 004/02_original_content

All accepted findings from results/review.md are done.

## F1 (blocking) — closure rules are now asserted and discriminated

`account_ledger/test_simulation.py` `test_group_4` gained a scenario with
three accounts: a schedule targeting an account that is closed before its
`execute_at` (status `PENDING` until due, then `FAILED`, no funds moved), a
schedule owned by the heir that survives the closure (`PENDING`, later
`EXECUTED`), the closed account's own schedule `CANCELLED`, and a ranking that
omits the closed account. The reviewer's two mutants (heir's schedules
cancelled on closure; missing target treated as executed) were added to
`tests/test_original_content.py` and fail at group 4 while groups 1–3 pass.

## F2 — time order across distinct due times

`test_group_3` gained a scenario where a later-created schedule is due earlier
and must execute first; a mutant ordering by schedule number fails at group 3.
The specification edge-case list names the rule.

## F3 — vendor identifier scan

`scripts/check_content.py` scans every candidate-facing file for
`codesignal` and `cp0002` (case-insensitive) and reports the file and marker.

## F4 — archive defense in depth

`scripts/run_packaged_browser.py` rejects any archive member under an
`oracles` segment or ending in `_reference.py`, `_solution.py` or
`_oracle.py`; `tests/test_catalog_distribution.py` covers three such members.

## F5 — specification wording

The inheritance sentence in `docs/content/account_ledger.md` is rewritten.

The ledger manifest was regenerated for the changed test module; the packaged
tests were run directly against the oracle (4 OK) and `just check content`
passes.

## Verification after iteration

    just check content                                                         OK
    python3 -m unittest tests.test_original_content tests.test_catalog_distribution tests.test_packaging_support   22 tests, OK
    just check unit                                                            453 tests, OK (1 skipped)
    python3 -m unittest tests.test_documentation                               OK
    git diff --check                                                           clean

Browser and frontend suites were not rerun: no route, bootstrap or frontend
file changed in this iteration.
