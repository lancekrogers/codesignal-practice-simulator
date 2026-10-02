# Purpose

## End goal

Turn the existing private, tested CodeSignal practice simulator into a local
browser assessment application whose interaction model is close enough to the
current CodeSignal candidate experience to rehearse the real test under time
pressure.

The browser experience must sit on top of the existing simulator engine. It
must not replace the engine with client-side state or shell out through the CLI
for each action.

## Why this matters

The user has a real assessment soon and has not handwritten Python recently.
The current terminal simulator proves scoring and lifecycle correctness, but it
does not rehearse the cognitive and navigational experience of working inside
CodeSignal: starting a one-sitting timer, reading progressive requirements,
editing in a browser IDE, running tests, interpreting results, switching views,
and making a final submission.

## Success criteria

- A single documented command launches a private loopback browser application.
- The user can complete a full or drill assessment entirely in the browser.
- The browser reproduces the important CodeSignal flow: pre-start instructions,
  no-pause countdown, question/level navigation, description/history/rules/info
  views, configurable code editor, output panel, run, skip/navigation, reset,
  and explicit final submission.
- Refreshing or reopening the browser recovers the same durable attempt without
  resetting time or losing saved code.
- Browser state cannot bypass validated workspace, lifecycle, scoring, or
  submission services.
- Reference/study/vendor material is never exposed by a live-attempt endpoint.
- Terminal agents can observe safe context and write coaching without silently
  editing candidate code.
- Real-browser tests and clean-clone evidence prove the experience works
  offline on Python 3.10+.

## Product boundary

This is a local practice product inspired by CodeSignal's documented candidate
workflow. It is not CodeSignal, does not copy proprietary branding or assets,
does not implement proctoring/accounts/cloud execution, and does not claim that
its tests are CodeSignal hidden tests.
