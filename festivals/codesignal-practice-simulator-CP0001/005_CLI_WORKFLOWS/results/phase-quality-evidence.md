# Phase 005 quality evidence

Verified on 2026-09-08 from
`/workspace/campaign/projects/codesignal-practice-simulator`.

## Functional deliverables

- `codesignal-sim` and `python -m codesignal_practice_simulator` expose the
  same fetch/start/resume/status/time/task/test/submit/context parser.
- A managed temporary workspace completed start, safe context, test with the
  expected exit 5 and four persisted results, first submit, byte-identical
  repeat submit, and final safe context.
- Installed-wheel coverage performs an offline fetch and starts an attempt
  outside the source checkout.
- README, CLI contract, drill profiles, agent safety policy, and optional Just
  recipes describe the implemented behavior.

## Verification results

| Check | Result |
| --- | --- |
| `.venv/bin/python -m unittest discover -s tests` | PASS — 136 tests |
| `python3 -m unittest discover -s tests` | PASS — 136 tests |
| `.venv/bin/python -m unittest tests.test_documentation tests.test_cli` | PASS — 29 tests |
| `just verify` | PASS — 136 tests plus `git diff --check HEAD` |
| Console/module help diff | PASS — byte-identical |
| `verify_manifest.py --scope tracked` | PASS |
| `verify_manifest.py --scope fixture-cache` | PASS |
| `verify_manifest.py --scope git-boundary` | PASS |
| `.githooks/pre-commit` and `.githooks/pre-push` | PASS |
| `solution/test_spec.py` | PASS — 26 tests |
| `solution/test_stages.py` | PASS — 12 tests |
| `study/check.py 4 solution/simulation.py` | PASS — levels 1–4 |
| `git diff --check` and `git diff --cached --check` | PASS |

## Review results

- Sequence 01 final Cursor judge: APPROVE, no critical findings.
- Evaluation/submission final Cursor judge: APPROVE, no critical findings.
- Operator documentation final Cursor judge: APPROVE, no critical or
  nonblocking findings.
- All earlier judge findings have regression tests and are recorded in the
  two sequence iterate gates.

The phase-006 `scripts/run_legacy_checks.py` aggregate is not a phase-005
deliverable. Its available component checks were run directly and passed.
