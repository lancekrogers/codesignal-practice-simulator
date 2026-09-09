"""Safe filesystem helpers for candidate document state."""

from __future__ import annotations

from pathlib import Path

from .candidate_document_models import (
    CandidateDocumentCorruptError,
    CandidateDocumentError,
    CandidateDocumentUnavailableError,
    HISTORY_ORDER_FILENAME,
    HistoryOrder,
    INITIAL_SOURCE_FILENAME,
    INITIAL_SOURCE_SCHEMA_VERSION,
    InvalidCandidateEncodingError,
    UnsafeCandidateDocumentError,
    etag_for,
    validate_content,
)
from .filesystem import Filesystem
from .persistence import Persistence


def initial_record(content: str, filename: str) -> dict[str, object]:
    return {
        "schema_version": INITIAL_SOURCE_SCHEMA_VERSION,
        "filename": filename,
        "sha256": etag_for(content).removeprefix("sha256:"),
        "content": content,
    }


def safe_candidate_path(attempt: Path, filename: str) -> Path:
    if (
        not isinstance(filename, str)
        or filename != "simulation.py"
        or Path(filename).name != filename
    ):
        raise UnsafeCandidateDocumentError("registered candidate filename is unsafe")
    if attempt.is_symlink() or not attempt.is_dir():
        raise UnsafeCandidateDocumentError("candidate attempt is unsafe")
    return attempt / filename


def read_source(filesystem: Filesystem, source: Path) -> str:
    """Read a regular source path while rejecting ordinary symlinks.

    A malicious same-user process can swap a path between these checks and the
    read; that race is outside the documented local threat model, so no
    OS-specific file-descriptor layer is used here.
    """
    if source.is_symlink():
        raise UnsafeCandidateDocumentError("registered candidate source is unsafe")
    if not source.exists():
        raise CandidateDocumentUnavailableError("registered candidate source is missing")
    if not source.is_file():
        raise UnsafeCandidateDocumentError("registered candidate source is unsafe")
    try:
        raw = filesystem.read_bytes(source)
    except OSError as error:
        raise CandidateDocumentUnavailableError(
            "registered candidate source could not be read"
        ) from error
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise InvalidCandidateEncodingError(
            "candidate source must be valid UTF-8"
        ) from error
    return validate_content(content)


def parse_initial(value: object, filename: str) -> str:
    if not isinstance(value, dict) or set(value) != {
        "schema_version",
        "filename",
        "sha256",
        "content",
    }:
        raise CandidateDocumentCorruptError("initial candidate baseline is corrupt")
    if (
        value["schema_version"] != INITIAL_SOURCE_SCHEMA_VERSION
        or value["filename"] != filename
        or not isinstance(value["filename"], str)
    ):
        raise CandidateDocumentCorruptError("initial candidate baseline is corrupt")
    try:
        content = validate_content(value["content"])
    except CandidateDocumentError as error:
        raise CandidateDocumentCorruptError(
            "initial candidate baseline is corrupt"
        ) from error
    if value["sha256"] != etag_for(content).removeprefix("sha256:"):
        raise CandidateDocumentCorruptError("initial candidate baseline is corrupt")
    return content


def write_initial_source_baseline(
    filesystem: Filesystem,
    persistence: Persistence,
    attempt: Path,
    *,
    filename: str = "simulation.py",
) -> None:
    """Capture the source and initialize its durable operation order."""
    source = safe_candidate_path(attempt, filename)
    content = read_source(filesystem, source)
    persistence.atomic_json(
        attempt / INITIAL_SOURCE_FILENAME, initial_record(content, filename)
    )
    persistence.atomic_json(
        attempt / HISTORY_ORDER_FILENAME,
        HistoryOrder(1).to_dict(),
    )

