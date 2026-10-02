# Browser Assessment Simulator — Intake Presentation

## Captured outcome

Extend the proven local simulator into a complete browser assessment experience
that rehearses the consequential parts of current CodeSignal use: explicit
assessment start, one-sitting timer, prompt/navigation views, browser Python
editor, run and submit flows, results, refresh recovery, and finality.

## Scope captured

- A local loopback web application launched by the installed Python package.
- A CodeSignal-like assessment shell with Description, History, Rules, and Info
  views; four-level navigation; editor settings; output panel; reset; run;
  navigation/skip; and final submission.
- A locally packaged, license-compatible Python editor with no runtime CDN.
- Durable conflict-safe autosave and candidate history built behind a dedicated
  locked candidate-document service.
- Existing lifecycle, scoring, persistence, prompt, and context services remain
  authoritative.
- Safe terminal-agent coaching continues through context/status/coaching files,
  outside the candidate IDE.
- Real-browser, API, security-boundary, installed-package, and clean-clone
  verification.

## Interpretations made

- “As close as possible” means behavioral and spatial fidelity, not copying
  CodeSignal branding, assets, proprietary page source, or wording.
- The browser should feel like a real assessment, so it will not place coaching
  inside the candidate screen. Coaching remains available from a second
  terminal under the established agent policy.
- The local four-group scorer remains honestly labeled. The application will
  not represent its cases as actual CodeSignal hidden tests.
- Proctoring, accounts, cloud workspaces, arbitrary browser terminal execution,
  multiple languages, realtime collaboration, and keystroke replay are outside
  this personal Python practice release.
- Only active, unexpired attempts accept code changes; expiry and submission
  make the editor read-only.

## Approval basis

These specifications reflect the user-approved shape and the explicit request
for maximum practical CodeSignal fidelity. The open implementation choices—
specific editor package, HTTP adapter module layout, and exact styling tokens—
will be resolved in planning against offline packaging, Python 3.10 support,
accessibility, and clean-clone reproducibility.
