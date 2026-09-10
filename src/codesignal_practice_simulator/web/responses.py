"""Stable, bounded JSON envelopes for the browser transport."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping

from ..candidate_document_models import CandidateDocument, SourceHistory
from ..evaluation_results import PracticeResult
from ..lifecycle import TimeObservation
from ..models import ScoreSummary, SessionState


WEB_SCHEMA_VERSION = "web/v1"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
HISTORY_PREVIEW_BYTES = 512


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """A serialized response before protocol headers are applied."""

    status: int
    document: Mapping[str, object]
    headers: Mapping[str, str]
    body: bytes | None = None


def success(
    data: object,
    *,
    status: int = 200,
    headers: Mapping[str, str] | None = None,
) -> HttpResponse:
    return HttpResponse(
        status,
        {"schema_version": WEB_SCHEMA_VERSION, "ok": True, "data": data},
        {} if headers is None else headers,
    )


def failure(
    status: int,
    code: str,
    message: str,
    *,
    headers: Mapping[str, str] | None = None,
) -> HttpResponse:
    return HttpResponse(
        status,
        {
            "schema_version": WEB_SCHEMA_VERSION,
            "ok": False,
            "error": {"code": code, "message": message},
        },
        {} if headers is None else headers,
    )


def encode(response: HttpResponse) -> bytes:
    """Encode and bound one transport response deterministically."""
    body = json.dumps(
        response.document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError("response exceeds transport limit")
    return body


def session_document(state: SessionState) -> dict[str, object]:
    return {"session": state.to_dict()}


def time_document(observation: TimeObservation) -> dict[str, object]:
    return {
        "session": observation.state.to_dict(),
        "observed_at": observation.observed_at.isoformat(),
        "elapsed_seconds": observation.elapsed_seconds,
        "remaining_seconds": observation.remaining_seconds,
    }


def source_document(document: CandidateDocument) -> dict[str, object]:
    return document.to_dict()


def history_document(history: SourceHistory) -> dict[str, object]:
    return {
        "current": source_document(history.current),
        "snapshots": [
            {
                "snapshot_id": snapshot.snapshot_id,
                "created_at": snapshot.created_at.isoformat(),
                "operation": snapshot.operation,
                "prior_hash": snapshot.prior_hash,
                "new_hash": snapshot.new_hash,
                "content_preview": _preview(snapshot.content),
            }
            for snapshot in history.snapshots
        ],
    }


def evaluation_document(
    state: SessionState,
    observation: TimeObservation,
    source: CandidateDocument,
    *,
    practice: PracticeResult | None = None,
    newly_submitted: bool = False,
) -> dict[str, object]:
    return {
        "session": state.to_dict(),
        "time": time_document(observation),
        "source": source_document(source),
        "score": None if state.score is None else score_document(state.score),
        "practice": None if practice is None else practice.to_dict(),
        "newly_submitted": newly_submitted,
    }


def score_document(score: ScoreSummary) -> dict[str, object]:
    return score.to_dict()


def _preview(content: str) -> str:
    encoded = content.encode("utf-8")
    if len(encoded) <= HISTORY_PREVIEW_BYTES:
        return content
    return encoded[:HISTORY_PREVIEW_BYTES].decode("utf-8", errors="ignore") + "…"


__all__ = [
    "HISTORY_PREVIEW_BYTES",
    "HttpResponse",
    "MAX_RESPONSE_BYTES",
    "WEB_SCHEMA_VERSION",
    "encode",
    "evaluation_document",
    "failure",
    "history_document",
    "score_document",
    "session_document",
    "source_document",
    "success",
    "time_document",
]
