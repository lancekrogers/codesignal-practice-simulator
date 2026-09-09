"""Manifest-bound package resources for the loopback browser shell."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from typing import Mapping


STATIC_PACKAGE = "codesignal_practice_simulator.web.static"
MANIFEST_NAME = "manifest.json"
MAX_ASSET_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class StaticResource:
    """A validated packaged asset and its explicit delivery policy."""

    name: str
    media_type: str
    cache_control: str
    body: bytes


def read_asset(name: str) -> StaticResource:
    """Read one allowlisted asset without accepting a filesystem path."""
    manifest = _load_manifest()
    record = manifest.get(name)
    if record is None:
        raise FileNotFoundError(name)
    resource = resources.files(STATIC_PACKAGE).joinpath(name)
    if (
        "/" in name
        or name in (".", "..")
        or _is_symlink(resource)
        or not resource.is_file()
    ):
        raise FileNotFoundError(name)
    body = resource.read_bytes()
    if len(body) > MAX_ASSET_BYTES:
        raise OSError("packaged asset is too large")
    return StaticResource(
        name=name,
        media_type=record["media_type"],
        cache_control=record["cache_control"],
        body=body,
    )


def asset_names() -> tuple[str, ...]:
    """Return the sorted explicit asset names for diagnostics and tests."""
    return tuple(sorted(_load_manifest()))


def _load_manifest() -> dict[str, dict[str, str]]:
    resource = resources.files(STATIC_PACKAGE).joinpath(MANIFEST_NAME)
    try:
        if _is_symlink(resource):
            raise OSError("manifest is a symlink")
        value = json.loads(
            resource.read_text(encoding="utf-8"),
            object_pairs_hook=_manifest_pairs,
        )
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise OSError("packaged static manifest is unavailable") from error
    if not isinstance(value, Mapping):
        raise OSError("packaged static manifest is invalid")
    manifest: dict[str, dict[str, str]] = {}
    for name, record in value.items():
        if (
            not isinstance(name, str)
            or not name
            or "/" in name
            or "\\" in name
            or name in (".", "..")
            or not name.isascii()
            or not isinstance(record, Mapping)
            or set(record) != {"media_type", "cache_control"}
            or not isinstance(record.get("media_type"), str)
            or not isinstance(record.get("cache_control"), str)
            or not _safe_header_value(record["media_type"])
            or not _safe_header_value(record["cache_control"])
        ):
            raise OSError("packaged static manifest is invalid")
        asset = resources.files(STATIC_PACKAGE).joinpath(name)
        if _is_symlink(asset) or not asset.is_file():
            raise OSError("packaged static manifest is invalid")
        manifest[name] = {
            "media_type": record["media_type"],
            "cache_control": record["cache_control"],
        }
    return manifest


def _manifest_pairs(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate manifest key")
        result[key] = value
    return result


def _safe_header_value(value: object) -> bool:
    return isinstance(value, str) and value.isascii() and not any(
        ord(character) < 32 or ord(character) == 127 for character in value
    )


def _is_symlink(resource: object) -> bool:
    checker = getattr(resource, "is_symlink", None)
    return bool(checker()) if callable(checker) else False


__all__ = [
    "MAX_ASSET_BYTES",
    "MANIFEST_NAME",
    "STATIC_PACKAGE",
    "StaticResource",
    "asset_names",
    "read_asset",
]
