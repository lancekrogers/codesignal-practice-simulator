# Independent keyboard-navigation diagnosis

Read-only Cursor Terra High session `8dc17605-caec-45e8-a23b-070c2703c611`,
model `gpt-5.6-terra-high`, inspected `shell_layout.spec.mjs`, `a11y.ts`,
`navigation_view.ts`, and `prompt_controller.ts`. No edits or tests were run.
This is a bounded diagnosis, not the final sequence or release review.

No confirmed runtime race or assertion-before-readiness defect was found.
`keyboardStart` waits for editor readiness; initial prompt loading may overlap
navigation, but prompt generations, selected level/tab guards, and request aborts
prevent stale Level 1 content overwriting Level 4. The Level 4 and History content
checks already use auto-waiting expectations. Roving focus/tabIndex and selection
are synchronous. The spec's serial configuration explains the three downstream
skips after one failure.

Suggested safe diagnostic separation: input/selection (`aria-current` or
`aria-selected`), then request/render completion for Level 4 or History. A content
timeout alone does not prove a focus defect. Do not add arbitrary waits/retries or
attribute this failure to intercepted-response scanning without evidence.

Primary Sol owns the focused real-browser investigation and final rerun. Its
failure disposition and retained changes belong in `streaming-iteration.md`.
