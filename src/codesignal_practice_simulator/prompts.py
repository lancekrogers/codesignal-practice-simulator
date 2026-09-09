"""Safe prompt retrieval for an already-created practice attempt."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import InvalidInputError, SessionUnavailableError
from .workspace import WorkspaceManager


MAX_PROMPT_BYTES = 512 * 1024


@dataclass(frozen=True, slots=True)
class PromptResult:
    """The selected copied prompt, identified by its authoritative attempt."""

    attempt_id: str
    level: int
    prompt: str

    def to_dict(self) -> dict[str, object]:
        """Convert the service result to the stable CLI result shape."""
        return {
            "attempt_id": self.attempt_id,
            "level": self.level,
            "prompt": self.prompt,
        }


class PromptService:
    """Read one validated copied prompt without consulting fixture material."""

    def __init__(self, workspace: WorkspaceManager) -> None:
        self.workspace = workspace
        self.persistence = workspace.persistence

    def read_prompt(
        self, *, attempt_id: str | None = None, level: int
    ) -> PromptResult:
        """Select, validate, and read a prompt while its attempt is locked."""
        if isinstance(level, bool) or not isinstance(level, int):
            raise InvalidInputError("level must be an integer")

        with self.workspace.selected_attempt(attempt_id) as attempt:
            state = self.persistence.read_session(attempt)
            definition = self.workspace.definition_for_persisted_session(state)
            if (
                level not in definition.level_groups
                or level > state.assessment.level_count
            ):
                raise InvalidInputError(
                    f"level is unavailable for this assessment: {level}"
                )

            filename = f"level{level}.md"
            if filename not in definition.prompt_filenames:
                raise SessionUnavailableError(
                    f"selected level is unavailable: {level}"
                )
            prompt = attempt / filename
            if prompt.parent != attempt or not prompt.is_file() or prompt.is_symlink():
                raise SessionUnavailableError(
                    f"selected level is unavailable: {level}"
                )
            try:
                with prompt.open("rb") as stream:
                    raw = stream.read(MAX_PROMPT_BYTES + 1)
                if len(raw) > MAX_PROMPT_BYTES:
                    raise ValueError("prompt is too large")
                text = raw.decode("utf-8")
            except (OSError, UnicodeDecodeError) as error:
                raise SessionUnavailableError(
                    f"cannot read selected level: {level}"
                ) from error
            except ValueError as error:
                raise SessionUnavailableError(
                    f"cannot read selected level: {level}"
                ) from error
            return PromptResult(state.attempt_id, level, text)


__all__ = ["MAX_PROMPT_BYTES", "PromptResult", "PromptService"]
