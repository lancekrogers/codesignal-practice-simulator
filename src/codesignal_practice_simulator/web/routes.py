"""Explicit API and static-resource route table for the browser transport."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler

from ..application import EvaluationSnapshot, RuntimeApplication
from ..candidate_document_models import (
    CandidateDocumentCorruptError,
    CandidateDocumentConflictError,
    CandidateDocumentError,
    CandidateDocumentUnavailableError,
    UnsafeCandidateDocumentError,
)
from ..errors import (
    DomainError,
    IllegalLifecycleError,
    InvalidInputError,
    SessionUnavailableError,
)
from .resources import read_asset
from .responses import (
    HttpResponse,
    evaluation_document,
    failure,
    history_document,
    session_document,
    source_document,
    success,
    time_document,
)
from .security import (
    RequestError,
    canonical_uuid,
    exact_fields,
    if_match,
    json_body,
    optional_query_values,
    query_values,
    request_path,
    require_origin,
    require_token,
    validate_request_headers,
)


class RouteHandler:
    """Dispatch only the documented browser routes."""

    def __init__(
        self,
        application: RuntimeApplication,
        *,
        token: str,
        origin: str,
    ) -> None:
        self.application = application
        self.token = token
        self.origin = origin

    def dispatch(
        self,
        method: str,
        target: str,
        handler: BaseHTTPRequestHandler,
    ) -> HttpResponse:
        try:
            validate_request_headers(handler)
            path, query = request_path(target)
            if path.startswith("/api/"):
                require_token(handler, self.token)
                return self._api(method, path, query, handler)
            return self._static(method, path, query)
        except RequestError as error:
            return failure(
                error.status,
                error.code,
                error.message,
                headers=error.headers,
            )
        except DomainError as error:
            return _domain_failure(error)
        except Exception:
            return failure(500, "internal_error", "request could not be completed safely")

    def _static(self, method: str, path: str, query: str) -> HttpResponse:
        if method not in {"GET", "HEAD"}:
            return failure(
                405,
                "method_not_allowed",
                "method is not allowed",
                headers={"Allow": "GET, HEAD"},
            )
        if query:
            return failure(404, "not_found", "resource is not available")
        name = "index.html" if path == "/" else path.removeprefix("/")
        if "/" in name:
            return failure(404, "not_found", "resource is not available")
        try:
            asset = read_asset(name)
        except FileNotFoundError:
            return failure(404, "not_found", "resource is not available")
        return HttpResponse(
            200,
            {},
            {
                "Content-Type": asset.media_type,
                "Cache-Control": asset.cache_control,
            },
            asset.body,
        )

    def _api(
        self,
        method: str,
        path: str,
        query: str,
        handler: BaseHTTPRequestHandler,
    ) -> HttpResponse:
        if path == "/api/bootstrap":
            return self._read(method, "GET", query, self.application.bootstrap)
        if path == "/api/attempts":
            return self._start(method, query, handler)
        if path == "/api/source" and method == "PUT":
            return self._save_source(method, query, handler)
        if path in {"/api/session", "/api/time", "/api/source", "/api/source/history"}:
            return self._read_selected(method, path, query)
        if path.startswith("/api/prompts/"):
            return self._prompt(method, path, query)
        if path in {"/api/source/reset", "/api/source/restore"}:
            return self._source_action(method, path, query, handler)
        if path in {"/api/test", "/api/submit"}:
            return self._evaluate(method, path, query, handler)
        return failure(404, "not_found", "API route is not available")

    def _save_source(
        self,
        method: str,
        query: str,
        handler: BaseHTTPRequestHandler,
    ) -> HttpResponse:
        _require_method(method, "PUT")
        attempt_id = _attempt_id(query)
        require_origin(handler, self.origin)
        expected = if_match(handler)
        body = json_body(handler)
        exact_fields(body, frozenset({"content"}))
        content = body["content"]
        if not isinstance(content, str):
            raise RequestError(422, "invalid_input", "source content is invalid")
        document = self.application.save_source(
            attempt_id=attempt_id,
            content=content,
            if_match=expected,
        )
        return success(
            {"source": source_document(document)},
            headers={"ETag": document.etag},
        )

    def _read(
        self,
        method: str,
        expected: str,
        query: str,
        callback,
    ) -> HttpResponse:
        _require_method(method, expected)
        if query:
            optional_query_values(query, frozenset())
        return success(callback())

    def _start(
        self,
        method: str,
        query: str,
        handler: BaseHTTPRequestHandler,
    ) -> HttpResponse:
        _require_method(method, "POST")
        if query:
            optional_query_values(query, frozenset())
        require_origin(handler, self.origin)
        body = json_body(handler)
        exact_fields(
            body,
            frozenset(),
            frozenset(("assessment", "mode", "drill_duration_seconds")),
        )
        assessment = body.get("assessment", "file_storage")
        mode = body.get("mode", "full")
        duration = body.get("drill_duration_seconds")
        if not isinstance(assessment, str) or not isinstance(mode, str):
            raise RequestError(422, "invalid_input", "start fields are invalid")
        if duration is not None and (
            isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0
        ):
            raise RequestError(422, "invalid_input", "drill duration is invalid")
        snapshot = self.application.start_web_snapshot(
            assessment=assessment,
            mode=mode,  # type: ignore[arg-type]
            drill_duration_seconds=duration,
        )
        return success(
            _evaluation_snapshot(snapshot),
            status=201,
        )

    def _read_selected(
        self,
        method: str,
        path: str,
        query: str,
    ) -> HttpResponse:
        _require_method(method, "GET")
        attempt_id = _attempt_id(query)
        if path == "/api/session":
            return success(session_document(self.application.status(attempt_id=attempt_id)))
        if path == "/api/time":
            return success(time_document(self.application.time(attempt_id=attempt_id)))
        if path == "/api/source":
            document = self.application.source(attempt_id=attempt_id)
            return success(
                source_document(document),
                headers={"ETag": document.etag},
            )
        history = self.application.source_history(attempt_id=attempt_id)
        return success(history_document(history), headers={"ETag": history.current.etag})

    def _prompt(self, method: str, path: str, query: str) -> HttpResponse:
        _require_method(method, "GET")
        segments = path.split("/")
        if len(segments) != 4 or segments[3] not in {"1", "2", "3", "4"}:
            return failure(404, "not_found", "prompt is not available")
        attempt_id = _attempt_id(query)
        result = self.application.task(
            attempt_id=attempt_id,
            level=int(segments[3]),
        )
        return success(result.to_dict())

    def _source_action(
        self,
        method: str,
        path: str,
        query: str,
        handler: BaseHTTPRequestHandler,
    ) -> HttpResponse:
        _require_method(method, "POST")
        attempt_id = _attempt_id(query)
        require_origin(handler, self.origin)
        expected = if_match(handler)
        body = json_body(handler)
        if path.endswith("/reset"):
            exact_fields(body, frozenset())
            document = self.application.reset_source(
                attempt_id=attempt_id,
                if_match=expected,
            )
        else:
            exact_fields(body, frozenset({"snapshot_id"}))
            snapshot_id = body["snapshot_id"]
            if not isinstance(snapshot_id, str):
                raise RequestError(422, "invalid_input", "snapshot ID is invalid")
            document = self.application.restore_source(
                attempt_id=attempt_id,
                snapshot_id=canonical_uuid(snapshot_id, "snapshot ID"),
                if_match=expected,
            )
        return success(
            {"source": source_document(document)},
            headers={"ETag": document.etag},
        )

    def _evaluate(
        self,
        method: str,
        path: str,
        query: str,
        handler: BaseHTTPRequestHandler,
    ) -> HttpResponse:
        _require_method(method, "POST")
        attempt_id = _attempt_id(query)
        require_origin(handler, self.origin)
        expected = if_match(handler)
        body = json_body(handler)
        exact_fields(body, frozenset({"content"}))
        content = body["content"]
        if not isinstance(content, str):
            raise RequestError(422, "invalid_input", "source content is invalid")
        if path == "/api/test":
            snapshot = self.application.test_snapshot(
                attempt_id=attempt_id,
                source_content=content,
                if_match=expected,
            )
        else:
            snapshot = self.application.submit_snapshot(
                attempt_id=attempt_id,
                source_content=content,
                if_match=expected,
            )
        return success(_evaluation_snapshot(snapshot))

def _attempt_id(query: str) -> str:
    values = query_values(query, frozenset({"attempt_id"}))
    return canonical_uuid(values["attempt_id"])


def _require_method(actual: str, expected: str) -> None:
    if actual != expected:
        raise RequestError(
            405,
            "method_not_allowed",
            "method is not allowed",
            headers={"Allow": expected},
        )


def _domain_failure(error: DomainError) -> HttpResponse:
    if isinstance(error, CandidateDocumentConflictError):
        return failure(
            409,
            "conflict",
            "candidate source changed; reload before saving",
            headers={"ETag": error.current_etag},
        )
    if isinstance(error, IllegalLifecycleError):
        return failure(423, "lifecycle_locked", "attempt does not accept this action")
    if isinstance(
        error,
        (
            SessionUnavailableError,
            CandidateDocumentUnavailableError,
            CandidateDocumentCorruptError,
            UnsafeCandidateDocumentError,
        ),
    ):
        return failure(404, "session_unavailable", "selected session is unavailable")
    if isinstance(error, (CandidateDocumentError, InvalidInputError)):
        return failure(422, "invalid_input", "request values are invalid")
    return failure(500, "internal_error", "request could not be completed safely")


def _evaluation_snapshot(snapshot: EvaluationSnapshot) -> dict[str, object]:
    return evaluation_document(
        snapshot.state,
        snapshot.time,
        snapshot.source,
        newly_submitted=snapshot.newly_submitted,
    )


__all__ = ["RouteHandler"]
