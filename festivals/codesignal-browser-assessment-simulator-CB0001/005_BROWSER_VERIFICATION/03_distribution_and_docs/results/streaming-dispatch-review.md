# Intermediate streaming design feedback — not final gate review

Read-only Cursor Luna High session `8211fbd0-8084-4d9d-9387-e80cf22ead0e`
reviewed the temporary dispatch-barrier design; no files or tests were changed.
Its cache-command acknowledgment concern is superseded by Sol's actual deadlock
experiment and removal of that design. Awaiting the stream promise, suggested by
Luna, had also deadlocked in the preceding experiment and is not an accepted fix.

Coordinator feedback for the replacement intercepted-byte scanning design:

- Scan every intercepted response regardless of whether a matching CDP request
  has arrived. A missing match must not silently skip the synchronous scan.
- Matching must exclude already claimed/scanned requests. Repeated or concurrent
  identical method/URL requests must each receive their own scan; choosing the
  oldest previously scanned record and returning skips later bytes. Add a causal
  regression with repeated same-URL responses and a forbidden later body.
- Do not set `streamEstablished` true for synchronous scans: use an honest scan
  mechanism marker. Preserve the original body bounds and fail-closed behavior.
- Keep negative length, over-budget, forbidden-body and missing-data checks.
  Unsupported fulfill shapes must not silently become an empty successful scan.

The reviewer also flags existing non-synthetic streaming failures being reported
as skips, and a possible scan queued after the final empty drain. Assess against
the existing approved bounded-scanning contract and actual CDP lifecycle. Its
claim that `request.settled` is Playwright-side state is inaccurate: inspect
`finishNetworkResponse`, which is driven by CDP terminal events. Do not accept an
unproven ordering hypothesis or broaden the redesign based only on that claim.

Coordinator checked the pinned Chromium 153.0.8010.12 implementation: the stream
method rejects resources that already have content and otherwise registers the
request for streaming. This supports the observed late-command error, but does
not itself prove cross-session route ordering. Primary source:
[InspectorNetworkAgent streamResourceContent](https://chromium.googlesource.com/chromium/src/+/refs/tags/153.0.8010.12/third_party/blink/renderer/core/inspector/inspector_network_agent.cc).

Final focused/full browser and installed-wheel reruns, independent sequence
review, and disposition of all relevant findings remain required.
