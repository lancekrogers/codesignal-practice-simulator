# Constraints

## Technical

- Reuse `LifecycleService`, `EvaluationService`, `PromptService`,
  `AttemptContextService`, `WorkspaceManager`, `Persistence`, and
  `IsolatedAttemptScorer`; the browser adapter must not duplicate their rules.
- Promote or extract the current private CLI composition root before sharing it
  with HTTP code. HTTP handlers remain transport adapters.
- Add a dedicated candidate-document service. HTTP handlers never construct an
  arbitrary filesystem path.
- Candidate source revisions are independent from lifecycle revisions. Use a
  SHA-256 content revision with optimistic concurrency and atomic writes.
- Only active, unexpired attempts accept candidate writes, reset, or history
  restore. Testing and submission use a coherent saved snapshot.
- The server binds to loopback and uses a launch capability. Same-user local
  processes remain outside the threat model; documentation must not call this a
  cryptographic sandbox.
- Browser assets must be package resources and work in editable and wheel
  installs. No runtime CDN is allowed.
- Any third-party editor dependency must have a compatible license, a locked
  version, documented provenance, and reproducible build output. CodeSignal
  assets or copied page source are prohibited.
- Keep FETCH_ONLY assessment bytes in ignored cache/attempt locations. Never
  add them to static assets, tests, snapshots, or Git history.
- Preserve Python 3.10+ and the existing standard-library runtime unless the
  plan demonstrates that a small dependency materially improves reliability.

## Product and fidelity

- Match consequential workflow and spatial conventions, not logos, wording,
  icons, or proprietary visual identity.
- The assessment timer starts only after explicit confirmation and cannot
  pause. Client clock display is derived from server timestamps.
- “Run Tests” and final submission must be clearly distinct. Results must not
  imply access to actual CodeSignal hidden cases.
- The candidate must never need Just; Just may provide optional shortcuts.
- The first useful browser flow should remain simple enough for immediate
  interview practice, while planning still covers the full requested scope.

## Process

- Use Cursor CLI agents for implementation and independent review to conserve
  primary-model inference.
- Use one project worktree for this festival and commit through `fest commit`.
- Preserve unrelated dirty campaign submodules and the completed simulator
  release history.
- Use `apply_patch` for direct edits and record task/gate evidence.
- Real-browser tests must use isolated temporary workspaces, fake/injected
  clocks where applicable, synthetic seven-record fixtures, and no network.
- Every implementation sequence ends with testing, review, iterate, and commit
  gates. Final release requires clean project and campaign-clone evidence.
