"""Read-only review of one stored attempt.

This module is the review read boundary. It never takes a lifecycle lock, never
repairs a journal, never initializes a source baseline, and never consults the
assessment registry: a stored result stays readable after its content version is
uninstalled. Mutation and scoring keep their own strict paths.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from .candidate_document_models import CandidateDocumentError
from .candidate_document_storage import read_source, safe_candidate_path
from .errors import (
    InvalidInputError,
    ReviewPendingError,
    SessionCorruptError,
    SessionUnavailableError,
)
from .filesystem import Filesystem, LocalFilesystem
from .models import (
    CONTENT_IDENTITY_PINNED,
    CONTENT_IDENTITY_UNAVAILABLE,
    SUBMITTED,
    ModeProfile,
    PinnedAssessment,
    ReviewRecord,
    ScoreSummary,
    SessionRecord,
    adapt_session_record,
    review_digest,
)
from .persistence import MAX_SESSION_BYTES, SESSION_FILENAME, Persistence


CAPTURED = "captured"
NOT_CAPTURED = "not_captured"
NOT_APPLICABLE = "not_applicable"

LEGACY_BINDING_UNAVAILABLE = "submitted_source_binding_unavailable"
SOURCE_UNREADABLE_AT_SUBMISSION = "submitted_source_was_unreadable"
LEGACY_SOURCE_UNAVAILABLE = "legacy_source_unavailable"
CONTENT_IDENTITY_UNAVAILABLE_ISSUE = "content_identity_unavailable"

CANDIDATE_FILENAME = "simulation.py"


@dataclass(frozen=True, slots=True)
class ReviewAssessment:
    """Assessment identity exactly as the attempt stored it."""

    assessment_id: str
    display_name: str
    level_count: int
    content_identity: Literal["pinned", "unavailable"]
    content_version: str | None = None
    content_digest: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "assessment_id": self.assessment_id,
            "display_name": self.display_name,
            "level_count": self.level_count,
            "content_identity": self.content_identity,
            "content_version": self.content_version,
            "content_digest": self.content_digest,
        }


@dataclass(frozen=True, slots=True)
class ReviewSourceView:
    """Source shown for a review, labeled by how well it is bound.

    ``captured`` came from the immutable review member. ``legacy_unbound`` is the
    attempt's current file, offered only because nothing proves what was
    submitted; it must never be presented as the submitted bytes.
    """

    filename: str
    sha256: str
    content: str
    binding: Literal["captured", "legacy_unbound"]

    def to_dict(self) -> dict[str, object]:
        return {
            "filename": self.filename,
            "sha256": self.sha256,
            "content": self.content,
            "binding": self.binding,
        }


@dataclass(frozen=True, slots=True)
class AttemptReview:
    """One attempt's stored metadata, content identity, and source binding."""

    attempt_id: str
    schema_version: str
    status: str
    assessment: ReviewAssessment
    profile: ModeProfile
    started_at: datetime
    deadline_at: datetime
    submitted_at: datetime | None
    score: ScoreSummary | None
    source_binding: Literal["captured", "not_captured", "not_applicable"]
    source: ReviewSourceView | None
    issues: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "attempt_id": self.attempt_id,
            "schema_version": self.schema_version,
            "status": self.status,
            "assessment": self.assessment.to_dict(),
            "profile": self.profile.to_dict(),
            "started_at": self.started_at.isoformat(),
            "deadline_at": self.deadline_at.isoformat(),
            "submitted_at": (
                None if self.submitted_at is None else self.submitted_at.isoformat()
            ),
            "score": None if self.score is None else self.score.to_dict(),
            "source_binding": self.source_binding,
            "source": None if self.source is None else self.source.to_dict(),
            "issues": list(self.issues),
        }


class AttemptReviewService:
    """Serve one explicitly requested attempt review without side effects."""

    def __init__(
        self,
        attempts_directory: Path,
        *,
        persistence: Persistence | None = None,
        filesystem: Filesystem | None = None,
    ) -> None:
        if persistence is not None and filesystem is None:
            filesystem = persistence.filesystem
        if filesystem is None:
            filesystem = LocalFilesystem()
        if persistence is None:
            persistence = Persistence(filesystem)
        elif persistence.filesystem is not filesystem:
            raise InvalidInputError(
                "filesystem and persistence must use the same filesystem"
            )
        self.attempts_directory = attempts_directory
        self.persistence = persistence
        self.filesystem = filesystem

    def get_review(
        self, attempt_id: str, *, include_source: bool = True
    ) -> AttemptReview:
        """Return one attempt's review, reading nothing it does not need."""
        attempt = self._attempt_directory(attempt_id)
        # Finalization owns repair. A pending marker means the durable outcome is
        # still being published, so this read reports retryable unavailability.
        if (attempt / ".submission-recovery.json").exists():
            raise ReviewPendingError(
                f"attempt is being finalized; retry: {attempt_id}"
            )
        before = self._session_bytes(attempt, attempt_id)
        state = self.persistence.read_session(attempt)
        if state.attempt_id != attempt.name:
            raise SessionCorruptError(f"attempt identity does not match: {attempt_id}")
        review = self.persistence.read_review(attempt)
        if self._session_bytes(attempt, attempt_id) != before:
            # The record changed between reads; a mixed generation is never served.
            raise ReviewPendingError(f"attempt changed while reading; retry: {attempt_id}")
        return self._assemble(attempt, state, review, include_source)

    def _assemble(
        self,
        attempt: Path,
        state: SessionRecord,
        review: ReviewRecord | None,
        include_source: bool,
    ) -> AttemptReview:
        adapted = adapt_session_record(state)
        issues: list[str] = []
        if not adapted.content_identity_available:
            issues.append(CONTENT_IDENTITY_UNAVAILABLE_ISSUE)
        if review is not None:
            self._require_matching_review(state, review)
        if state.status != SUBMITTED:
            binding, source = NOT_APPLICABLE, None
        elif review is None:
            binding = NOT_CAPTURED
            issues.append(LEGACY_BINDING_UNAVAILABLE)
            source = self._legacy_source(attempt, issues) if include_source else None
        elif review.source is None:
            binding, source = NOT_CAPTURED, None
            issues.append(SOURCE_UNREADABLE_AT_SUBMISSION)
        else:
            binding = CAPTURED
            source = (
                ReviewSourceView(
                    filename=review.source.filename,
                    sha256=review.source.sha256,
                    content=review.source.content,
                    binding=CAPTURED,
                )
                if include_source
                else None
            )
        # session.json is mutable; a verified review is not. When one exists it
        # is what the review shows, so a session edited underneath cannot present
        # a fabricated identity, profile or timing through this boundary.
        assessment = review.assessment if review is not None else state.assessment
        pinned = isinstance(assessment, PinnedAssessment)
        return AttemptReview(
            attempt_id=adapted.attempt_id,
            schema_version=adapted.schema_version,
            status=adapted.status,
            assessment=ReviewAssessment(
                assessment_id=assessment.assessment_id,
                display_name=assessment.display_name,
                level_count=assessment.level_count,
                content_identity=(
                    CONTENT_IDENTITY_PINNED if pinned else CONTENT_IDENTITY_UNAVAILABLE
                ),
                content_version=assessment.content_version if pinned else None,
                content_digest=assessment.content_digest if pinned else None,
            ),
            profile=review.profile if review is not None else adapted.profile,
            started_at=review.started_at if review is not None else adapted.started_at,
            deadline_at=(
                review.deadline_at if review is not None else adapted.deadline_at
            ),
            submitted_at=(
                review.submitted_at if review is not None else adapted.submitted_at
            ),
            score=review.score if review is not None else adapted.score,
            source_binding=binding,
            source=source,
            issues=tuple(issues),
        )

    @staticmethod
    def _require_matching_review(state: SessionRecord, review: ReviewRecord) -> None:
        """Bind the published review to this exact submitted revision."""
        if state.status != SUBMITTED:
            raise SessionCorruptError(
                f"review does not match its session: {state.attempt_id}"
            )
        if (
            review.attempt_id != state.attempt_id
            or review.state_revision != state.revision
            or review.submitted_at != state.submitted_at
            or review.score != state.score
            or review.assessment != state.assessment
            or review.profile != state.profile
            or review.started_at != state.started_at
            or review.deadline_at != state.deadline_at
        ):
            raise SessionCorruptError(
                f"review does not match its session: {state.attempt_id}"
            )
        expected = getattr(state, "review_digest", None)
        if expected is not None and expected != review_digest(review):
            raise SessionCorruptError(
                f"review digest does not match its session: {state.attempt_id}"
            )

    def _legacy_source(self, attempt: Path, issues: list[str]) -> ReviewSourceView | None:
        """Offer the current file only as explicitly unbound legacy source."""
        try:
            path = safe_candidate_path(attempt, CANDIDATE_FILENAME)
            content = read_source(self.filesystem, path)
        except CandidateDocumentError:
            issues.append(LEGACY_SOURCE_UNAVAILABLE)
            return None
        return ReviewSourceView(
            filename=CANDIDATE_FILENAME,
            sha256=_digest(content),
            content=content,
            binding="legacy_unbound",
        )

    def _attempt_directory(self, attempt_id: str) -> Path:
        if not isinstance(attempt_id, str):
            raise InvalidInputError("attempt ID must be a canonical UUID")
        try:
            parsed = UUID(attempt_id)
        except ValueError as error:
            raise InvalidInputError("attempt ID must be a canonical UUID") from error
        if str(parsed) != attempt_id:
            raise InvalidInputError("attempt ID must be a canonical UUID")
        attempts = self.attempts_directory
        if attempts.is_symlink() or (attempts.exists() and not attempts.is_dir()):
            raise SessionCorruptError("attempts directory is unsafe")
        attempt = attempts / attempt_id
        if attempt.is_symlink() or not attempt.is_dir():
            raise SessionUnavailableError(f"attempt is unavailable: {attempt_id}")
        return attempt

    def _session_bytes(self, attempt: Path, attempt_id: str) -> bytes:
        path = attempt / SESSION_FILENAME
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise SessionCorruptError(f"session is unsafe: {attempt_id}")
        try:
            return self.filesystem.read_bytes_limited(path, MAX_SESSION_BYTES)
        except FileNotFoundError as error:
            raise SessionUnavailableError(
                f"attempt is unavailable: {attempt_id}"
            ) from error
        except OSError as error:
            raise SessionUnavailableError(f"cannot read attempt: {attempt_id}") from error


def _digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


__all__ = [
    "CAPTURED",
    "CONTENT_IDENTITY_UNAVAILABLE_ISSUE",
    "LEGACY_BINDING_UNAVAILABLE",
    "LEGACY_SOURCE_UNAVAILABLE",
    "NOT_APPLICABLE",
    "NOT_CAPTURED",
    "SOURCE_UNREADABLE_AT_SUBMISSION",
    "AttemptReview",
    "AttemptReviewService",
    "ReviewAssessment",
    "ReviewSourceView",
]
