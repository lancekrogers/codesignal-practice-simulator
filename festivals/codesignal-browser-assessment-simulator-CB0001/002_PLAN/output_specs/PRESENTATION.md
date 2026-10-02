# Implementation Plan Presentation

## Proposed result

One command opens a private local browser assessment with an intentional start,
server-authoritative countdown, four-question navigation, CodeSignal-familiar
split IDE, locally bundled Monaco Python editor, autosave/history/reset, separate
practice-test and final-submit paths, expiry/final screens, refresh/restart
recovery, and synchronized safe terminal-agent coaching.

## Execution shape

1. **Application foundation:** extract the shared production application graph,
   add a locked candidate-document/CAS/history service, and expose only a fixed
   capability-scoped loopback API.
2. **Assessment IDE:** bundle licensed Monaco assets offline, build the entry and
   responsive assessment shell, connect editing/tabs/navigation/test/submit,
   and preserve terminal coaching boundaries.
3. **Browser verification:** use Playwright for the complete visible journey,
   races, expiry, security, accessibility, restart, offline, and wheel behavior;
   then rehearse clean clones and document the proven workflow.
4. **Release review:** independent Cursor reviews plus delegated local judges,
   remediation, traced commits, private push/merge, and campaign pointer sync.

## Key decisions

- Existing lifecycle/scoring services remain the only authority.
- Standard-library `ThreadingHTTPServer`; no runtime web framework or Node.
- `monaco-editor@0.56.0` (MIT) is locked, built locally, and shipped in the wheel.
- Source writes use attempt locking, SHA-256 ETags, atomic replacement, and a
  bounded recoverable history owned by one service.
- Every API request requires the per-launch capability; mutations also require
  exact loopback Origin. There is no arbitrary file, command, upload, or proxy
  route.
- The UI uses a small explicit state machine; browser storage never owns time or
  assessment lifecycle.

## Plan-readiness assessment

Every required behavior B01-B20 and every explicit exclusion B21-B25 is mapped
to implementation and verification. No unresolved product question requires
user input. The user has already approved the browser-app shape, requested
Cursor Agent implementation, delegated routine decisions to the judge, and
asked that work continue without interruption.
