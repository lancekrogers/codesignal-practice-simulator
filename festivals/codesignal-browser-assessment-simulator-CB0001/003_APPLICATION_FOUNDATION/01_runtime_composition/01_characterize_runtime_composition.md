---
fest_type: task
fest_id: 01_characterize_runtime_composition.md
fest_name: characterize runtime composition
fest_parent: 01_runtime_composition
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:27.374367-06:00
fest_updated: 2026-09-09T03:36:51.467674-06:00
fest_tracking: true
---


# Task: characterize runtime composition

## Objective

Capture the current CLI application graph and externally observable behavior so extracting the shared container cannot change lifecycle, serialization, status refresh, scorer selection, or exit semantics.

## Requirements

- [ ] Trace `_RuntimeApplication.__init__`, `_score_selected_attempt`, every adapter method, `_default_application`, and `_dispatch` in `src/codesignal_practice_simulator/cli.py`.
- [ ] Record the exact dependencies and lock-sensitive calls used by `WorkspaceManager`, `LifecycleService`, `EvaluationService`, `PromptService`, `AttemptContextService`, `DerivedStatusService`, and `IsolatedAttemptScorer`.
- [ ] Add characterization coverage without modifying production behavior, including injected clock/scorer seams, `--json` envelopes, candidate-failure exit 5, and derived `STATUS.md` refresh.

## Implementation

Follow these steps in order:

1. Read `src/codesignal_practice_simulator/cli.py` and the constructors/methods in `lifecycle.py`, `evaluation.py`, `workspace.py`, `prompts.py`, `rendering.py`, and `scoring.py`; draw the call graph in comments or test names, not in a new runtime dependency.
2. Extend `tests/test_cli.py` with a recording application/factory assertion that `_default_application` creates the same collaborators and with behavior cases for `start`, `resume`, `status`, `time`, `task`, `test`, `submit`, and `context`.
3. Use the existing helpers in `tests/test_cli.py`, `tests/test_lifecycle.py`, and `tests/test_end_to_end.py`; keep all workspaces temporary and use synthetic fixture builders rather than `.cache/codesignal-fixtures/` bytes.
4. Run focused tests, then `python3 -m unittest discover -s tests -v` and the console/module smoke flow from `tests/test_end_to_end.py` before extraction.

### Safety and content isolation

Do not read candidate source, copied tests, solution, study, or vendor material in characterization output. Assert serialized results contain only the existing CLI envelope and safe context fields.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] A test or documented matrix names every current composition collaborator and adapter operation.
- [ ] `tests/test_cli.py` covers injected dependencies, serialization, status refresh, and exit mapping without changing production code.
- [ ] The baseline unittest suite, `python3 scripts/run_legacy_checks.py`, and existing end-to-end entry-point checks pass unchanged.
