# Runtime Composition Iteration

All review and testing findings were addressed:

- Removed public registry injection from the production container rather than
  weakening `IsolatedAttemptScorer` canonical-definition validation.
- Enforced filesystem/persistence identity and added mismatch coverage.
- Changed dependency defaults to explicit `None` handling in the touched
  composition path and its directly reused collaborators.
- Narrowed public mode/context types to domain literals.
- Added direct scorer-factory forwarding coverage for `create_application`.
- Stabilized the synthetic ps observation window while preserving exact four-
  group argv and isolation assertions.

Rerun evidence: focused tests passed; 163 tests passed three full runs after the
fix; four E2E tests passed; canonical legacy/provenance checks passed; compileall
and diff checks passed. No P0/P1 behavior was deferred and no exclusion was
relaxed. The sequence is ready for traceable commit.
