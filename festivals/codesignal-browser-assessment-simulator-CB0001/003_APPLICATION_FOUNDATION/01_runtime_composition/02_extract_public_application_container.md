---
fest_type: task
fest_id: 02_extract_public_application_container.md
fest_name: extract public application container
fest_parent: 01_runtime_composition
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:27.495709-06:00
fest_updated: 2026-09-09T03:36:58.401518-06:00
fest_tracking: true
---


# Task: extract public application container

## Objective

Move the private runtime object graph into a public application module that the CLI and web server can share while preserving the current service authorities.

## Requirements

- [ ] Create `src/codesignal_practice_simulator/application.py` with public `RuntimeApplication` and `create_application(workspace_root, *, clock=None, registry=..., filesystem=None, persistence=None)` seams.
- [ ] Keep `_score_selected_attempt` registry-derived and attempt-local, and expose typed methods for fetch/start/resume/status/time/task/test/submit/context plus candidate-document collaborators planned by later tasks.
- [ ] Update `src/codesignal_practice_simulator/cli.py` so `_default_application` uses the factory and existing `CommandApplication`, parser, dispatch, serializer, envelopes, and exits remain compatible.

## Implementation

Follow these steps in order:

1. Copy the behavior of `cli.py::_RuntimeApplication` into `src/codesignal_practice_simulator/application.py` without changing service call order; import `ValidatedFixtureCache`, `WorkspaceManager`, `LifecycleService`, `EvaluationService`, `PromptService`, `AttemptContextService`, `DerivedStatusService`, and `IsolatedAttemptScorer` there.
2. Add constructor seams for a fake `Clock`, registry, filesystem/persistence, and optional scorer factory while keeping production defaults equivalent to the current `_RuntimeApplication`.
3. Replace the CLI class definition with imports/type references and make `_default_application` call `create_application`; do not make `src/codesignal_practice_simulator/application.py` depend on argparse or `sys.stdout`.
4. Add `tests/test_application.py` for construction and collaborator wiring, then run `python3 -m unittest tests.test_application tests.test_cli -v`.

### Safety and content isolation

The container must not expose arbitrary paths or commands. Preserve `WorkspaceManager` selection and `Persistence` lock order; keep derived status best-effort and never let status rendering become lifecycle authority.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] `src/codesignal_practice_simulator/application.py` contains the public container/factory and imports cleanly on Python 3.10+.
- [ ] `cli.py` has no second production composition graph and all existing CLI tests pass.
- [ ] Injected clock/registry/filesystem seams are testable, while the default scorer still uses persisted assessment metadata and `IsolatedAttemptScorer`.
