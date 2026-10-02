# Independent bounded diagnosis

Cursor Luna High, read-only chat `e80466ec-5e34-45ab-b7b8-68a24646e1ab`.
No edits or browser runs. This is diagnosis assistance, not final sequence review.

The strongest causal candidate is the CDP streaming startup race: sending
`Network.streamResourceContent` on requestWillBeSent does not ensure it has
resolved before the independently fulfilled Playwright synthetic response finishes.
Late rejection yields a strict `streaming-unavailable` violation; a still-pending
command explains absent completed diagnostics. The settled-before-response theory
is weaker for normal CDP request ordering and is not established by this evidence.

An additional structural concern needs a deterministic check: `assertPolicyState`
awaits only one snapshot of `state.scanPromises`, then waits for relevant requests.
If another scan is queued while that snapshot is pending, assertion could finish
before the new scan's violation is appended. Suggested controlled scenario:
start scan A, call assert, queue deferred scan B, resolve A, then demonstrate that
assert must still await B and reject its eventual violation. Check this in the
existing guard rather than assuming it caused the original flaky case.

Do not change request-ID generation/retirement semantics based only on the weaker
hypothesis. Do not introduce broad retries, sleeps, weaker bounds or reporter
overrides. Primary implementation and real-browser confirmation remain assigned
to the Sol investigation; final independent review must inspect the resulting diff.

Coordinator inspection of the initial route barrier: its `if (!request) return`
branch also needs causal verification. Playwright route and CDP notifications
arrive on independent paths; a route callback preceding CDP request tracking must
not silently release the response before arming. Exercise missing/delayed tracking,
rejected setup, and retirement explicitly, not only the matching-request happy path.
