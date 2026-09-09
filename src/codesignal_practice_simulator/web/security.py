"""HTTP input validation for the fixed loopback capability boundary."""

from __future__ import annotations

import json
import re
import secrets
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import parse_qsl, unquote, urlsplit
from uuid import UUID

from ..candidate_document_models import is_canonical_etag


MAX_BODY_BYTES = 256 * 1024
_DECIMAL = re.compile(r"(0|[1-9][0-9]*)\Z")
_DUPLICATE_HEADER_PREFIXES = ("content-", "sec-", "x-simulator-")
_DUPLICATE_HEADERS = frozenset(
    {"authorization", "connection", "cookie", "host", "if-match", "origin"}
)


class RequestError(Exception):
    """A safe, already-mapped request rejection."""

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.status = status
        self.code = code
        self.message = message
        self.headers = {} if headers is None else dict(headers)
        super().__init__(message)


def require_token(handler: BaseHTTPRequestHandler, expected: str) -> None:
    values = handler.headers.get_all("X-Simulator-Token", [])
    if (
        len(values) != 1
        or not values[0].isascii()
        or not secrets.compare_digest(values[0], expected)
    ):
        raise RequestError(401, "unauthorized", "simulator capability is required")


def validate_request_headers(handler: BaseHTTPRequestHandler) -> None:
    """Reject ambiguous security and framing headers before routing."""
    seen: set[str] = set()
    for name in handler.headers:
        lowered = name.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        if not (
            lowered in _DUPLICATE_HEADERS
            or lowered.startswith(_DUPLICATE_HEADER_PREFIXES)
        ):
            continue
        values = handler.headers.get_all(name, [])
        if len(values) > 1:
            raise RequestError(400, "invalid_headers", "duplicate request headers are invalid")


def require_origin(handler: BaseHTTPRequestHandler, expected: str) -> None:
    values = handler.headers.get_all("Origin", [])
    if len(values) != 1 or values[0] != expected:
        raise RequestError(403, "forbidden_origin", "request Origin is not allowed")


def request_path(raw_target: str) -> tuple[str, str]:
    """Return one decoded path and raw query while rejecting controls."""
    try:
        split = urlsplit(raw_target)
        if split.scheme or split.netloc:
            raise ValueError("absolute request targets are not supported")
        path = unquote(split.path, errors="strict")
    except (UnicodeDecodeError, ValueError) as error:
        raise RequestError(404, "not_found", "resource is not available") from error
    if not path.startswith("/") or any(ord(char) < 32 for char in path):
        raise RequestError(404, "not_found", "resource is not available")
    return path, split.query


def query_values(query: str, allowed: frozenset[str]) -> dict[str, str]:
    try:
        pairs = parse_qsl(query, keep_blank_values=True, strict_parsing=True)
    except ValueError as error:
        raise RequestError(400, "invalid_query", "query parameters are invalid") from error
    result: dict[str, str] = {}
    for key, value in pairs:
        if key not in allowed or key in result or not value:
            raise RequestError(400, "invalid_query", "query parameters are invalid")
        result[key] = value
    if set(result) != set(allowed):
        raise RequestError(400, "invalid_query", "query parameters are invalid")
    return result


def optional_query_values(query: str, allowed: frozenset[str]) -> dict[str, str]:
    try:
        pairs = parse_qsl(query, keep_blank_values=True, strict_parsing=True)
    except ValueError as error:
        raise RequestError(400, "invalid_query", "query parameters are invalid") from error
    result: dict[str, str] = {}
    for key, value in pairs:
        if key not in allowed or key in result or not value:
            raise RequestError(400, "invalid_query", "query parameters are invalid")
        result[key] = value
    return result


def canonical_uuid(value: str, label: str = "attempt ID") -> str:
    try:
        parsed = UUID(value)
    except ValueError as error:
        raise RequestError(422, "invalid_input", f"{label} is invalid") from error
    if str(parsed) != value:
        raise RequestError(422, "invalid_input", f"{label} is invalid")
    return value


def if_match(handler: BaseHTTPRequestHandler) -> str:
    values = handler.headers.get_all("If-Match", [])
    if len(values) != 1 or not is_canonical_etag(values[0]):
        raise RequestError(422, "invalid_input", "If-Match is invalid")
    return values[0]


def json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    """Read one bounded JSON object after checking framing and media type."""
    content_type = handler.headers.get("Content-Type", "")
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise RequestError(400, "invalid_body", "Content-Type must be application/json")
    transfer_encoding = handler.headers.get("Transfer-Encoding", "")
    if transfer_encoding and transfer_encoding.lower() != "identity":
        raise RequestError(400, "invalid_body", "request framing is not supported")
    length_values = handler.headers.get_all("Content-Length", [])
    if len(length_values) != 1:
        raise RequestError(400, "invalid_body", "Content-Length is required")
    length_text = length_values[0]
    if _DECIMAL.fullmatch(length_text) is None:
        raise RequestError(400, "invalid_body", "Content-Length is invalid")
    length = int(length_text)
    if length < 0:
        raise RequestError(400, "invalid_body", "Content-Length is invalid")
    if length > MAX_BODY_BYTES:
        raise RequestError(413, "body_too_large", "request body is too large")
    try:
        raw = handler.rfile.read(length)
        if len(raw) != length:
            raise ValueError("request body ended before Content-Length")
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_object_pairs_without_duplicates,
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RequestError(400, "invalid_json", "request body is not valid JSON") from error
    except ValueError as error:
        raise RequestError(400, "invalid_json", "request body is not valid JSON") from error
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise RequestError(422, "invalid_input", "request body must be an object")
    return value


def _object_pairs_without_duplicates(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


def exact_fields(
    value: Mapping[str, object],
    required: frozenset[str],
    optional: frozenset[str] = frozenset(),
) -> None:
    if set(value) - required - optional or not required <= set(value):
        raise RequestError(422, "invalid_input", "request fields are invalid")


__all__ = [
    "MAX_BODY_BYTES",
    "RequestError",
    "canonical_uuid",
    "exact_fields",
    "if_match",
    "json_body",
    "optional_query_values",
    "query_values",
    "request_path",
    "require_origin",
    "require_token",
    "validate_request_headers",
]
