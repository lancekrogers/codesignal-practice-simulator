"""Registered assessment definitions and their immutable input contracts."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass

from .errors import InvalidInputError
from .models import DRILL_PROFILE, FULL_PROFILE, AssessmentMetadata, PinnedAssessment


CONTENT_IDENTITY_SCHEMA_VERSION = "assessment-content/v1"
# The isolated runner loads test_simulation.TestSimulateCodingFramework.test_group_N
# for N in 1..4 (scoring.py bootstrap). Content pinned to another contract is not
# scorable by this release.
RUNNER_CONTRACT = "unittest-groups-v1"
# Input provider kinds (D003). The provider that owns a kind validates the
# source before staging and computes the identity new attempts pin.
PINNED_FETCHED = "pinned-fetched"
PACKAGED_ORIGINAL = "packaged-original"
PROVIDER_KINDS = frozenset((PINNED_FETCHED, PACKAGED_ORIGINAL))
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_DIRECTORY_SEGMENT = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")


@dataclass(frozen=True, slots=True)
class AssessmentDefinition:
    """The copied inputs and supported runtime contract for one assessment.

    ``cache_directory`` is the definition's input directory relative to its
    provider's root: the fetched fixture cache for ``pinned-fetched`` content,
    the installed resources package for ``packaged-original`` content.
    """

    metadata: AssessmentMetadata
    cache_directory: str
    prompt_filenames: tuple[str, ...]
    candidate_filename: str
    test_filename: str
    level_groups: tuple[int, ...]
    profile_ids: frozenset[str]
    runner_contract: str = RUNNER_CONTRACT
    provider_kind: str = PINNED_FETCHED
    description: str = ""

    def __post_init__(self) -> None:
        if (
            not isinstance(self.cache_directory, str)
            or not self.cache_directory
            or any(
                not _DIRECTORY_SEGMENT.fullmatch(segment)
                for segment in self.cache_directory.split("/")
            )
        ):
            raise InvalidInputError("assessment cache directory is invalid")
        if self.provider_kind not in PROVIDER_KINDS:
            raise InvalidInputError("assessment provider kind is unsupported")
        if not isinstance(self.description, str):
            raise InvalidInputError("assessment description is invalid")
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
        if self.runner_contract != RUNNER_CONTRACT:
            raise InvalidInputError("assessment runner contract is unsupported")

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


def content_identity(
    definition: AssessmentDefinition,
    *,
    content_version: str,
    file_hashes: Mapping[str, str],
) -> PinnedAssessment:
    """Pin one definition to declared hashes of its copied candidate-facing files.

    The digest covers the assessment ID, content version, runner contract, and
    each copied file's declared SHA-256. Callers supply hashes that were (or will
    be) verified against actual bytes; this function never reads files itself.
    """
    if not isinstance(file_hashes, Mapping) or set(file_hashes) != set(
        definition.copied_filenames
    ):
        raise InvalidInputError("content identity requires every copied file hash")
    if any(
        not isinstance(digest, str) or not _SHA256.fullmatch(digest)
        for digest in file_hashes.values()
    ):
        raise InvalidInputError("content identity file hashes are invalid")
    document = {
        "schema_version": CONTENT_IDENTITY_SCHEMA_VERSION,
        "assessment_id": definition.metadata.assessment_id,
        "content_version": content_version,
        "runner_contract": definition.runner_contract,
        "files": [
            {"path": name, "sha256": file_hashes[name]} for name in sorted(file_hashes)
        ],
    }
    encoded = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return PinnedAssessment(
        assessment_id=definition.metadata.assessment_id,
        display_name=definition.metadata.display_name,
        content_version=content_version,
        content_digest=hashlib.sha256(encoded).hexdigest(),
        level_count=definition.metadata.level_count,
    )


FILE_STORAGE = AssessmentDefinition(
    metadata=AssessmentMetadata("file_storage", "File Storage"),
    cache_directory="assessment/file_storage",
    prompt_filenames=("level1.md", "level2.md", "level3.md", "level4.md"),
    candidate_filename="simulation.py",
    test_filename="test_simulation.py",
    level_groups=(1, 2, 3, 4),
    profile_ids=frozenset((FULL_PROFILE, DRILL_PROFILE)),
    runner_contract=RUNNER_CONTRACT,
    provider_kind=PINNED_FETCHED,
    description=(
        "Fetched File Storage practice assessment; requires the pinned fixture cache."
    ),
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
        directories = {definition.cache_directory for definition in definitions}
        if len(directories) != len(definitions):
            raise InvalidInputError("assessment registry contains duplicate input directories")

    def definitions(self) -> tuple[AssessmentDefinition, ...]:
        """Return every installed definition in stable ID order."""
        return tuple(self._definitions[key] for key in sorted(self._definitions))

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
    "CONTENT_IDENTITY_SCHEMA_VERSION",
    "DEFAULT_ASSESSMENT_REGISTRY",
    "FILE_STORAGE",
    "PACKAGED_ORIGINAL",
    "PINNED_FETCHED",
    "PROVIDER_KINDS",
    "RUNNER_CONTRACT",
    "content_identity",
]
