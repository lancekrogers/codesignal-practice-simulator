"""Registry-driven, read-only catalog of installed assessments (D003/D004).

The catalog lists every installed definition with its stored metadata, the
identity a new attempt would pin, and an honest readiness verdict from the
definition's input provider. Enumeration reads provider inputs to validate
them but writes nothing, takes no lock, and never touches attempts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .assessments import AssessmentDefinition, PINNED_FETCHED
from .errors import FixtureSetupRequiredError, InvalidInputError
from .models import (
    DRILL_DEFAULT_DURATION_SECONDS,
    DRILL_MODE,
    DRILL_PROFILE,
    FULL_DURATION_SECONDS,
    FULL_MODE,
    FULL_PROFILE,
)
from .workspace import WorkspaceManager


FETCH_REQUIRED = "fetch_required"
PACKAGED_CONTENT_INVALID = "packaged_content_invalid"
PROVIDER_UNAVAILABLE = "provider_unavailable"

_PROFILE_DOCUMENTS = {
    FULL_PROFILE: {
        "mode": FULL_MODE,
        "profile_id": FULL_PROFILE,
        "duration_seconds": FULL_DURATION_SECONDS,
    },
    DRILL_PROFILE: {
        "mode": DRILL_MODE,
        "profile_id": DRILL_PROFILE,
        "duration_seconds": DRILL_DEFAULT_DURATION_SECONDS,
    },
}


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """One installed assessment as the library shows it."""

    assessment_id: str
    display_name: str
    description: str
    level_count: int
    levels: tuple[int, ...]
    profiles: tuple[dict[str, object], ...]
    provider_kind: str
    content_version: str | None
    content_digest: str | None
    available: bool
    setup: Literal["fetch_required", "packaged_content_invalid", "provider_unavailable"] | None
    setup_message: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "assessment_id": self.assessment_id,
            "display_name": self.display_name,
            "description": self.description,
            "level_count": self.level_count,
            "levels": [{"level": level, "label": f"Level {level}"} for level in self.levels],
            "profiles": [dict(profile) for profile in self.profiles],
            "provider_kind": self.provider_kind,
            "content_version": self.content_version,
            "content_digest": self.content_digest,
            "available": self.available,
            "setup": self.setup,
            "setup_message": self.setup_message,
        }


@dataclass(frozen=True, slots=True)
class Catalog:
    entries: tuple[CatalogEntry, ...]

    def to_dict(self) -> dict[str, object]:
        return {"assessments": [entry.to_dict() for entry in self.entries]}


class CatalogService:
    """Enumerate installed definitions with readiness, without side effects."""

    def __init__(self, workspace: WorkspaceManager) -> None:
        self.workspace = workspace

    def list_assessments(self) -> Catalog:
        return Catalog(
            tuple(self._entry(definition) for definition in self.workspace.registry.definitions())
        )

    def _entry(self, definition: AssessmentDefinition) -> CatalogEntry:
        version: str | None = None
        digest: str | None = None
        setup = None
        message = None
        available = True
        try:
            provider = self.workspace.providers.for_definition(definition)
        except FixtureSetupRequiredError as error:
            provider = None
            available, setup, message = False, PROVIDER_UNAVAILABLE, error.message
        if provider is not None:
            try:
                pinned = provider.pinned_assessment(definition)
                version, digest = pinned.content_version, pinned.content_digest
                provider.validate(definition, self.workspace.filesystem)
            except (FixtureSetupRequiredError, InvalidInputError) as error:
                available = False
                setup = (
                    FETCH_REQUIRED
                    if definition.provider_kind == PINNED_FETCHED
                    else PACKAGED_CONTENT_INVALID
                )
                message = _safe_message(error, setup)
        return CatalogEntry(
            assessment_id=definition.metadata.assessment_id,
            display_name=definition.metadata.display_name,
            description=definition.description,
            level_count=definition.metadata.level_count,
            levels=definition.level_groups,
            profiles=tuple(
                _PROFILE_DOCUMENTS[profile_id]
                for profile_id in (FULL_PROFILE, DRILL_PROFILE)
                if definition.supports_profile(profile_id)
            ),
            provider_kind=definition.provider_kind,
            content_version=version,
            content_digest=digest,
            available=available,
            setup=setup,
            setup_message=message,
        )


def _safe_message(error: Exception, setup: str) -> str:
    """Never echo a filesystem path from a validation failure into the catalog."""
    if setup == FETCH_REQUIRED:
        return "fixture cache is not fetched or not valid; run codesignal-sim fetch"
    return "packaged content is missing or does not match its declared manifest"


__all__ = [
    "Catalog",
    "CatalogEntry",
    "CatalogService",
    "FETCH_REQUIRED",
    "PACKAGED_CONTENT_INVALID",
    "PROVIDER_UNAVAILABLE",
]
