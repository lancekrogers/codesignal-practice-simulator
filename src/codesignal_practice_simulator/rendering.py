"""Safe, derived views of one validated timed-attempt session.

Renderers intentionally receive only validated session state and event records.
They never inspect candidate inputs, Markdown, the fixture cache, or educational
material.  The generated views are operational context, not session authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import uuid4

from .errors import SessionUnavailableError
from .filesystem import Filesystem, LocalFilesystem
from .models import ACTIVE, EXPIRED, SUBMITTED, EventRecord, SessionState
from .workspace import WorkspaceManager


STATUS_FILENAME = "STATUS.md"
CONTEXT_SCHEMA_VERSION = "attempt-context/v1"
SESSION_UNAVAILABLE_MESSAGE = "session unavailable"


@dataclass(frozen=True, slots=True)
class AttemptContext:
    """The narrow, non-authoritative data allowed in a live-session view."""

    state: SessionState
    events: tuple[EventRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.state, SessionState):
            _unavailable()
        if not isinstance(self.events, tuple) or not self.events:
            _unavailable()

        revisions: set[int] = set()
        for event in self.events:
            if not isinstance(event, EventRecord):
                _unavailable()
            if event.attempt_id != self.state.attempt_id:
                _unavailable()
            if event.revision > self.state.revision:
                _unavailable()
            revisions.add(event.revision)
        if self.state.revision not in revisions:
            _unavailable()


@dataclass(frozen=True, slots=True)
class ContextResult:
    """A CLI-safe representation of context in the requested output format."""

    context: AttemptContext
    output_format: Literal["markdown", "json"]

    def __post_init__(self) -> None:
        if self.output_format not in ("markdown", "json"):
            _unavailable()

    def to_dict(self) -> dict[str, object]:
        if self.output_format == "markdown":
            return {
                "format": self.output_format,
                "context": render_markdown(self.context),
            }
        return {"format": self.output_format, "context": _context_document(self.context)}


class AttemptContextService:
    """Read a validated safe view without inspecting candidate-owned inputs."""

    def __init__(self, workspace: WorkspaceManager) -> None:
        self.workspace = workspace

    def read(
        self,
        *,
        attempt_id: str | None,
        output_format: Literal["markdown", "json"],
    ) -> ContextResult:
        with self.workspace.selected_attempt(attempt_id) as attempt:
            context = load_attempt_context(attempt, self.workspace.persistence)
            self.workspace.definition_for_persisted_session(context.state)
        return ContextResult(context=context, output_format=output_format)


class DerivedStatusService:
    """Best-effort writer for the generated status of one known attempt."""

    def __init__(self, workspace: WorkspaceManager) -> None:
        self.workspace = workspace

    def refresh(self, attempt_id: str) -> AttemptContext | None:
        """Refresh derived status without changing lifecycle command outcomes.

        ``selected_attempt`` holds the workspace lock before the attempt lock.
        That keeps the read-render-replace sequence ordered with lifecycle
        writes, so a stale context cannot replace a newer generated status.
        """
        try:
            with self.workspace.selected_attempt(attempt_id) as attempt:
                return refresh_status(
                    attempt,
                    self.workspace.persistence,
                    filesystem=self.workspace.filesystem,
                )
        except Exception:
            return None


def load_attempt_context(attempt: Path, persistence) -> AttemptContext:
    """Load the selected attempt's validated durable inputs, or fail safely."""
    try:
        state = persistence.read_session(attempt)
        events = tuple(persistence.read_events(attempt))
        return AttemptContext(state=state, events=events)
    except SessionUnavailableError as error:
        raise SessionUnavailableError(SESSION_UNAVAILABLE_MESSAGE) from error


def render_json(context: AttemptContext) -> str:
    """Return deterministic JSON containing only safe derived session context."""
    return json.dumps(
        _context_document(context),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def render_markdown(context: AttemptContext) -> str:
    """Return deterministic Markdown containing only safe derived session context."""
    document = _context_document(context)
    assessment = document["assessment"]
    lifecycle = document["lifecycle"]
    score = document["score"]
    events = document["events"]
    commands = document["next_legal_commands"]

    lines = [
        "# Attempt status",
        "",
        "This is derived, non-authoritative session context.",
        "",
        "## Assessment",
        f"- Assessment: {assessment['display_name']} (`{assessment['id']}`)",
        f"- Mode: `{assessment['mode']}`",
        f"- Profile: `{assessment['profile']}`",
        "",
        "## Lifecycle",
        f"- Status: `{lifecycle['status']}`",
        f"- Started: {lifecycle['started_at']}",
        f"- Deadline: {lifecycle['deadline_at']}",
    ]
    if lifecycle["submitted_at"] is not None:
        lines.append(f"- Submitted: {lifecycle['submitted_at']}")
    lines.extend(
        [
            "",
            "## Score summary",
            (
                f"- Passed levels: {score['passed_levels']} of "
                f"{len(score['levels'])}"
            ),
            f"- Highest contiguous level: {score['highest_contiguous_level']}",
            "",
            "## Event history",
        ]
    )
    lines.extend(
        (
            f"- Revision {event['revision']}: `{event['name']}` "
            f"({event['outcome']}) at {event['occurred_at']}"
        )
        for event in events
    )
    lines.extend(
        [
            "",
            "## Next legal commands",
        ]
    )
    lines.extend(f"- `{command}`" for command in commands)
    return "\n".join(lines) + "\n"


def write_status(
    attempt: Path,
    context: AttemptContext,
    *,
    filesystem: Filesystem | None = None,
) -> None:
    """Atomically replace only the generated ``STATUS.md`` surface."""
    filesystem = filesystem or LocalFilesystem()
    status = attempt / STATUS_FILENAME
    temporary = attempt / f".{STATUS_FILENAME}.{uuid4().hex}.tmp"
    try:
        filesystem.write_bytes(temporary, render_markdown(context).encode("utf-8"))
        filesystem.flush_file(temporary)
        filesystem.replace(temporary, status)
    except OSError:
        try:
            if temporary.exists() or temporary.is_symlink():
                filesystem.unlink(temporary)
        except OSError:
            pass
        raise


def refresh_status(
    attempt: Path,
    persistence,
    *,
    filesystem: Filesystem | None = None,
) -> AttemptContext:
    """Validate selected durable inputs before replacing generated status."""
    context = load_attempt_context(attempt, persistence)
    write_status(attempt, context, filesystem=filesystem)
    return context


def _context_document(context: AttemptContext) -> dict[str, object]:
    state = context.state
    score = _score_document(state)
    return {
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "attempt_id": state.attempt_id,
        "assessment": {
            "id": state.assessment.assessment_id,
            "display_name": state.assessment.display_name,
            "mode": state.profile.mode,
            "profile": state.profile.profile_id,
        },
        "lifecycle": {
            "status": state.status,
            "started_at": state.started_at.isoformat(),
            "deadline_at": state.deadline_at.isoformat(),
            "submitted_at": (
                None if state.submitted_at is None else state.submitted_at.isoformat()
            ),
        },
        "score": score,
        "events": [
            {
                "revision": event.revision,
                "occurred_at": event.occurred_at.isoformat(),
                "name": event.name,
                "outcome": event.outcome,
            }
            for event in context.events
        ],
        "next_legal_commands": _next_legal_commands(state),
    }


def _score_document(state: SessionState) -> dict[str, object]:
    if state.score is None:
        return {
            "levels": [],
            "passed_levels": 0,
            "highest_contiguous_level": 0,
        }
    return state.score.to_dict()


def _next_legal_commands(state: SessionState) -> list[str]:
    prefix = "codesignal-sim"
    selected = f"--attempt {state.attempt_id}"
    commands = [
        f"{prefix} status {selected}",
        f"{prefix} context {selected}",
    ]
    if state.status == ACTIVE:
        commands.extend(
            (
                f"{prefix} resume {selected}",
                f"{prefix} time {selected}",
                f"{prefix} test {selected}",
                f"{prefix} submit {selected}",
            )
        )
    elif state.status == EXPIRED:
        commands.append(f"{prefix} submit {selected}")
    elif state.status != SUBMITTED:
        _unavailable()
    return commands


def _unavailable() -> None:
    raise SessionUnavailableError(SESSION_UNAVAILABLE_MESSAGE)


__all__ = [
    "AttemptContext",
    "AttemptContextService",
    "CONTEXT_SCHEMA_VERSION",
    "ContextResult",
    "DerivedStatusService",
    "SESSION_UNAVAILABLE_MESSAGE",
    "STATUS_FILENAME",
    "load_attempt_context",
    "refresh_status",
    "render_json",
    "render_markdown",
    "write_status",
]
