# D005: Server-Authoritative Browser State Machine and Layered Verification

**Status:** accepted
**Date:** 2026-09-09

## Context

Timer, autosave, testing, timeout, refresh, and submission create overlapping
asynchronous states. A convincing UI must stay responsive without becoming a
second lifecycle authority.

## Options

### Persist the assessment state in browser storage

- **Pros:** easy refresh behavior.
- **Cons:** allows time/state drift and contradicts durable terminal visibility.

### Server-render every interaction

- **Pros:** one authority.
- **Cons:** poor editor interaction and unnecessary page churn.

### Small client state machine over authoritative API snapshots

- **Pros:** realistic editor UX with explicit race handling and durable server
  truth.
- **Cons:** needs disciplined transitions and browser tests.

## Decision

The client has four top-level screens: `booting`, `entry`, `attempt`, and
`final`. An attempt has server lifecycle state (`active`, `expired`,
`submitted`) plus orthogonal UI state: selected level/tab, source ETag,
`clean|dirty|saving|conflict|failed`, `idle|testing|submitting`, modal, and
connection status.

`/api/bootstrap` determines the screen. The timer renders from the latest
server deadline/remaining observation and periodically resynchronizes; reaching
zero triggers an authoritative refresh and disables mutation optimistically but
never invents an expired state. Navigation never starts/pauses time. Run and
Submit flush autosave first. Only one evaluation action runs at once. Submit
confirmation captures focus and the idempotent server result determines the
final screen.

Use three verification layers:

1. Unit/domain tests for composition and candidate-document invariants.
2. Real HTTP tests for schema, error mapping, security, concurrency, and content
   isolation.
3. Playwright tests for visible candidate journeys, keyboard/accessibility,
   timing, refresh/restart, races, offline assets, and terminal-surface sync.

All tests use temporary workspaces, synthetic fixture builders, fake clocks,
fixed capability injection, and network denial. Selectors prefer accessible
roles/names with stable test IDs only where roles cannot disambiguate.

## Consequences

- Client code stays framework-free and small; no Redux/router/backend state copy.
- Browser preferences (theme/font/tab/pane sizes) may use local storage because
  they do not affect assessment authority.
- Playwright is a locked development dependency; runtime remains Python plus
  packaged static assets.
