"""Registered assessment definitions and their immutable input contracts."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import InvalidInputError
from .models import DRILL_PROFILE, FULL_PROFILE, AssessmentMetadata


@dataclass(frozen=True, slots=True)
class AssessmentDefinition:
    """The copied inputs and supported runtime contract for one assessment."""

    metadata: AssessmentMetadata
    cache_directory: str
    prompt_filenames: tuple[str, ...]
    candidate_filename: str
    test_filename: str
    level_groups: tuple[int, ...]
    profile_ids: frozenset[str]

    def __post_init__(self) -> None:
        if not self.cache_directory or self.cache_directory.startswith("/"):
            raise InvalidInputError("assessment cache directory is invalid")
        if self.level_groups != (1, 2, 3, 4):
            raise InvalidInputError("assessment must define groups 1 through 4")
        if not self.prompt_filenames or any(
            not name.startswith("level") or not name.endswith(".md")
            for name in self.prompt_filenames
        ):
            raise InvalidInputError("assessment prompt filenames are invalid")
        if self.candidate_filename != "simulation.py":
            raise InvalidInputError("assessment candidate filename is invalid")
        if self.test_filename != "test_simulation.py":
            raise InvalidInputError("assessment test filename is invalid")
        if self.profile_ids != frozenset((FULL_PROFILE, DRILL_PROFILE)):
            raise InvalidInputError("assessment profiles are invalid")

    @property
    def copied_filenames(self) -> tuple[str, ...]:
        """Return only candidate-facing files copied from the validated cache."""
        return (*self.prompt_filenames, self.candidate_filename, self.test_filename)

    @property
    def cache_filenames(self) -> tuple[str, ...]:
        """Return validated-cache paths relative to the fixture root."""
        return tuple(
            f"{self.cache_directory}/{filename}" for filename in self.copied_filenames
        )

    def supports_profile(self, profile_id: str) -> bool:
        return profile_id in self.profile_ids


FILE_STORAGE = AssessmentDefinition(
    metadata=AssessmentMetadata("file_storage", "File Storage"),
    cache_directory="assessment/file_storage",
    prompt_filenames=("level1.md", "level2.md", "level3.md", "level4.md"),
    candidate_filename="simulation.py",
    test_filename="test_simulation.py",
    level_groups=(1, 2, 3, 4),
    profile_ids=frozenset((FULL_PROFILE, DRILL_PROFILE)),
)


class AssessmentRegistry:
    """Look up the deliberately small set of supported assessments."""

    def __init__(self, definitions: tuple[AssessmentDefinition, ...]) -> None:
        if not definitions:
            raise InvalidInputError("assessment registry cannot be empty")
        self._definitions = {
            definition.metadata.assessment_id: definition for definition in definitions
        }
        if len(self._definitions) != len(definitions):
            raise InvalidInputError("assessment registry contains duplicate IDs")

    def require(self, assessment_id: str) -> AssessmentDefinition:
        if not isinstance(assessment_id, str):
            raise InvalidInputError("assessment ID is invalid")
        try:
            return self._definitions[assessment_id]
        except KeyError as error:
            raise InvalidInputError(f"unknown assessment: {assessment_id}") from error


DEFAULT_ASSESSMENT_REGISTRY = AssessmentRegistry((FILE_STORAGE,))


__all__ = [
    "AssessmentDefinition",
    "AssessmentRegistry",
    "DEFAULT_ASSESSMENT_REGISTRY",
    "FILE_STORAGE",
]
