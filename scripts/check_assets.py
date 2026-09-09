"""Validate the generated browser asset boundary.

This checker intentionally uses only the Python standard library so it can run
without installing the simulator's runtime dependencies or Node tooling.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_NAME = "manifest.json"
PACKAGE_MARKERS = frozenset({"__init__.py"})
REQUIRED_NAMES = frozenset(
    {"ASSET_PROVENANCE.txt", "NOTICE.txt", "app.js", "index.html", "manifest.json", "styles.css"}
)
REQUIRED_PATTERNS = (
    re.compile(r"^app-[A-Za-z0-9_-]+\.js$"),
    re.compile(r"^styles-[A-Za-z0-9_-]+\.css$"),
    re.compile(r"^editor\.worker-[A-Za-z0-9_-]+\.js$"),
    re.compile(r"^language\.worker-[A-Za-z0-9_-]+\.js$"),
    re.compile(r"^[A-Za-z0-9_-]+-[A-Za-z0-9_-]+\.ttf$"),
)
FORBIDDEN_TEXT = (
    re.compile(r"\bFETCH_ONLY\b", re.IGNORECASE),
    re.compile(r"codesignal-fixtures|assessment/file_storage", re.IGNORECASE),
    re.compile(r"(?:^|[\\/])node_modules(?:[\\/]|$)", re.IGNORECASE),
    re.compile(
        r"(?:^|[\\/])(?:\.cache|__pycache__|\.pytest_cache|\.npm|npm-cache|"
        r"playwright-report|playwright-reports|playwright-cache|test-results)"
        r"(?:[\\/]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|[\s\"'=:(])(?:/Users/[^ \t\r\n\"'<>]+|/private/(?:tmp|var)/"
        r"[^ \t\r\n\"'<>]+|/tmp/[^ \t\r\n\"'<>]+|/var/folders/[^ \t\r\n\"'<>]+|"
        r"[A-Za-z]:[\\/](?:Users|tmp)[\\/][^ \t\r\n\"'<>]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"file:///(?:Users|private/var|tmp|var/folders)/"
        r"[^ \t\r\n\"'<>]+",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:fetch|WebSocket|sendBeacon|new\s+URL|import)\s*\(\s*['\"]"
        r"(?:file|https?):",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:src|href|action)\s*=\s*['\"](?:file|https?):",
        re.IGNORECASE,
    ),
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    re.compile(
        r"\b(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{12,}\b|"
        r"\bgh[pousr]_[A-Za-z0-9]{20,}\b|"
        r"\bxox[baprs]-[A-Za-z0-9-]{12,}\b|"
        r"\bAKIA[0-9A-Z]{16}\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|secret|password)"
        r"\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{16,}",
        re.IGNORECASE,
    ),
)
MEDIA_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ttf": "font/ttf",
    ".txt": "text/plain; charset=utf-8",
}
HASHED_ASSET = re.compile(
    r"^(?:app|styles|editor\.worker|language\.worker)-[A-Za-z0-9_-]+\.(?:js|css)$"
    r"|^[A-Za-z0-9_-]+-[A-Za-z0-9_-]+\.ttf$"
)
REQUIRED_RUNTIME_NOTICE_MAPPING = {
    "entry_points": ["monaco-editor"],
    "packages": {
        "dompurify": [
            {"source": "LICENSE", "snapshot": "dompurify.Apache-2.0.txt"},
            {"source": "LICENSE-MPL", "snapshot": "dompurify.MPL-2.0.txt"},
        ],
        "marked": [{"source": "LICENSE.md", "snapshot": "marked.MIT.txt"}],
        "monaco-editor": [
            {"source": "LICENSE", "snapshot": "monaco-editor.MIT.txt"},
            {
                "source": "ThirdPartyNotices.txt",
                "snapshot": "monaco-editor.ThirdPartyNotices.txt",
            },
        ],
    },
}
REQUIRED_RUNTIME_NOTICE_SNAPSHOT_SHA256 = {
    "dompurify.Apache-2.0.txt": "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30",
    "dompurify.MPL-2.0.txt": "fab3dd6bdab226f1c08630b1dd917e11fcb4ec5e1e020e2c16f83a0a13863e85",
    "marked.MIT.txt": "8e3a3f82f59a60958f56ca08f445647c32a4733dc7ca6c2c46f6eb898471ab9c",
    "monaco-editor.MIT.txt": "33e4ff1a06ef62ba21788ea162564ee8165269a24a9ce6ef301837447eab0ac6",
    "monaco-editor.ThirdPartyNotices.txt": "790537262fc78a764e121e6b92b959bcd3f5c310b47d9d9b9e92e17fe0af5336",
}
FORBIDDEN_DIRECTORIES = frozenset(
    {
        "node_modules",
        ".cache",
        ".pytest_cache",
        ".tmp",
        "test-results",
        "playwright-report",
        "playwright-reports",
        "playwright-cache",
        ".playwright",
        ".npm",
        "npm-cache",
        "npm_cache",
        "dist",
        "build",
    }
)
ALLOWED_EXTERNAL_URLS = frozenset(
    {
        # Monaco/VS Code diagnostic and standards literals retained by the bundle.
        "http://www.w3.org/1998/Math/MathML",
        "http://www.w3.org/1999/xhtml",
        "http://www.w3.org/2000/svg",
        "https://code.visualstudio.com/docs/editor/codebasics#_find-and-replace",
        "https://code.visualstudio.com/docs/editor/codebasics#_multicursor-modifier",
        "https://github.com/markedjs/marked",
        "https://github.com/microsoft/monaco-editor#faq",
        "https://github.com/microsoft/vscode/blob/main/LICENSE.txt",
        "https://github.com/microsoft/vscode/issues/103170",
        "https://github.com/microsoft/vscode/issues/new",
        "https://microsoft.com",
        # URLs required by retained third-party license notices.
        "http://www.apache.org/licenses/",
        "http://www.apache.org/licenses/LICENSE-2.0",
        "http://mozilla.org/MPL/2.0/",
        "https://github.com/puppeteer/puppeteer",
        "https://github.com/puppeteer/puppeteer/blob/master/LICENSE",
    }
)
EXTERNAL_URL = re.compile(r"(?i)(?:https?|wss?):\/\/[^\s\"'`<>]+")
NETWORK_FUNCTION_NAMES = (
    r"fetch|WebSocket|EventSource|importScripts|sendBeacon"
)
NETWORK_CALL_PREFIXES = (
    re.compile(
        rf"""(?ix)
        (?:\b(?:globalThis|window|self)\s*(?:\.\s*|\[\s*['"])   # global fetch
        \s*)?\b(?:{NETWORK_FUNCTION_NAMES})\b\s*(?:['"]\s*\])?
        \s*(?:\.\s*(?:call|apply|bind)\s*)?
        \(\s*[^;{{}}]{{0,256}}\Z
        """
    ),
    re.compile(
        r"""(?ix)
        \bXMLHttpRequest\s*
        (?:\(\s*[^;{}]{0,80}\)\s*)?
        (?:\.\s*prototype\s*)?
        \.\s*open\s*(?:\.\s*(?:call|apply|bind)\s*)?\([^;{}]{0,256}\Z
        """
    ),
    re.compile(r"(?ix)\bnew\s+URL\s*\([^;{}]{0,256}\Z"),
    re.compile(r"(?ix)\bimport\s*(?:\(\s*)?[^;{}]{0,256}\Z"),
)
NETWORK_ALIAS_DECLARATION = re.compile(
    r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*([^;\n]+)"
)
NETWORK_ALIAS_REFERENCE = re.compile(
    rf"""(?ix)\A
    (?:
        (?:globalThis|window|self)\s*(?:\.\s*|\[\s*['"])
        \s*(?:{NETWORK_FUNCTION_NAMES})\s*(?:['"]\s*\])?
      | (?:navigator\s*\.\s*)?sendBeacon
      | (?:{NETWORK_FUNCTION_NAMES})
      | XMLHttpRequest\s*(?:\.\s*prototype\s*)?\s*\.\s*open
    )
    \Z"""
)


class AssetCheckError(ValueError):
    """Raised when generated assets violate the package contract."""


@dataclass(frozen=True)
class AssetReport:
    """Aggregate information suitable for logs or retained verification evidence."""

    root: Path
    names: tuple[str, ...]
    manifest_sha256: str
    asset_hashes: tuple[tuple[str, str], ...]


def check_static_root(static_root: Path) -> AssetReport:
    """Validate one generated static directory and return only aggregate data."""
    root = Path(static_root)
    if root.is_symlink():
        raise AssetCheckError("static output root must not be a symlink")
    if not root.is_dir():
        raise AssetCheckError(f"static output directory does not exist: {static_root}")
    _reject_symlinks(root)
    manifest = _read_manifest(root)
    _check_tree(root, set(manifest))
    _check_required_files(manifest)
    hashes: list[tuple[str, str]] = []
    for name, record in sorted(manifest.items()):
        path = root / name
        body = path.read_bytes()
        _check_record(name, record, body)
        hashes.append((name, hashlib.sha256(body).hexdigest()))
        _scan_text(name, body)
    _check_required_contents(root)
    manifest_bytes = (root / MANIFEST_NAME).read_bytes()
    return AssetReport(
        root=root,
        names=tuple(sorted(manifest)),
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        asset_hashes=tuple(hashes),
    )


def _read_manifest(root: Path) -> dict[str, dict[str, object]]:
    path = root / MANIFEST_NAME
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_pairs,
        )
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise AssetCheckError("manifest.json is not valid UTF-8 JSON") from error
    if not isinstance(value, Mapping):
        raise AssetCheckError("manifest.json must contain an object")
    manifest: dict[str, dict[str, object]] = {}
    for name, record in value.items():
        if (
            not isinstance(name, str)
            or not _safe_name(name)
            or not isinstance(record, Mapping)
            or not {"media_type", "cache_control"} <= set(record)
            or set(record) - {"media_type", "cache_control", "sha256", "size"}
        ):
            raise AssetCheckError(f"invalid manifest record: {name!r}")
        manifest[name] = dict(record)
    if MANIFEST_NAME not in manifest:
        raise AssetCheckError("manifest.json must describe itself")
    return manifest


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate manifest key: {key}")
        result[key] = value
    return result


def _check_tree(root: Path, declared: set[str]) -> None:
    actual: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise AssetCheckError(f"symlink in static output: {relative}")
        if path.is_file():
            if _is_runtime_cache_artifact(path.relative_to(root)):
                continue
            actual.add(relative)
        elif not path.is_dir():
            raise AssetCheckError(f"unsupported static output entry: {relative}")
        elif path.name in FORBIDDEN_DIRECTORIES:
            raise AssetCheckError(f"forbidden directory in static output: {relative}")
        elif path.name == "__pycache__":
            continue
    unexpected = sorted(actual - declared - PACKAGE_MARKERS)
    missing = sorted(declared - actual)
    if unexpected:
        raise AssetCheckError(f"undeclared static files: {', '.join(unexpected)}")
    if missing:
        raise AssetCheckError(f"manifest files are missing: {', '.join(missing)}")


def _check_required_files(manifest: Mapping[str, Mapping[str, object]]) -> None:
    missing = sorted(name for name in REQUIRED_NAMES if name not in manifest)
    missing.extend(
        f"/{pattern.pattern}"
        for pattern in REQUIRED_PATTERNS
        if not any(pattern.fullmatch(name) for name in manifest)
    )
    if missing:
        raise AssetCheckError(f"required packaged assets are missing: {', '.join(missing)}")
    notice = manifest["NOTICE.txt"]
    provenance = manifest["ASSET_PROVENANCE.txt"]
    if notice.get("media_type") != MEDIA_TYPES[".txt"]:
        raise AssetCheckError("NOTICE.txt has the wrong MIME type")
    if provenance.get("media_type") != MEDIA_TYPES[".txt"]:
        raise AssetCheckError("ASSET_PROVENANCE.txt has the wrong MIME type")


def _check_required_contents(root: Path) -> None:
    notice = (root / "NOTICE.txt").read_bytes()
    _check_runtime_notice_boundary(notice)
    provenance = (root / "ASSET_PROVENANCE.txt").read_bytes()
    for marker in (
        b"Generated by webui/build.mjs.",
        b"Runtime dependencies are bundled same-origin assets",
        b"monaco-editor 0.56.0",
    ):
        if marker not in provenance:
            raise AssetCheckError(
                f"ASSET_PROVENANCE.txt is missing required marker: {marker.decode()}"
            )


def _check_runtime_notice_boundary(notice: bytes) -> None:
    try:
        specification = json.loads(
            (PROJECT_ROOT / "webui" / "LICENSES" / "runtime-notices.json").read_text(
                encoding="utf-8",
            ),
            object_pairs_hook=_unique_pairs,
        )
        lockfile = json.loads(
            (PROJECT_ROOT / "webui" / "package-lock.json").read_text(
                encoding="utf-8",
            ),
            object_pairs_hook=_unique_pairs,
        )
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise AssetCheckError("runtime notice metadata is unavailable") from error
    if specification != REQUIRED_RUNTIME_NOTICE_MAPPING:
        raise AssetCheckError("runtime-notices.json does not match the locked runtime mapping")
    packages = _runtime_package_closure(specification, lockfile)
    if packages != tuple(sorted(REQUIRED_RUNTIME_NOTICE_MAPPING["packages"])):
        raise AssetCheckError("runtime lockfile closure does not match the locked notice packages")
    expected_headings: list[bytes] = []
    expected_sections: list[bytes] = []
    for name in packages:
        record = lockfile.get("packages", {}).get(f"node_modules/{name}")
        notices = specification.get("packages", {}).get(name)
        if not isinstance(record, Mapping) or not isinstance(notices, list):
            raise AssetCheckError(f"{name} has no lockfile-driven runtime notice")
        for item in notices:
            if not isinstance(item, Mapping):
                raise AssetCheckError(f"{name} has an invalid notice mapping")
            source = item.get("source")
            snapshot_name = item.get("snapshot")
            if not isinstance(source, str) or not isinstance(snapshot_name, str):
                raise AssetCheckError(f"{name} has an invalid notice source")
            snapshot_path = (
                PROJECT_ROOT / "webui" / "LICENSES" / snapshot_name
            )
            try:
                snapshot = snapshot_path.read_bytes()
            except OSError as error:
                raise AssetCheckError(
                    f"{name}/{source} notice snapshot is missing"
                ) from error
            expected_digest = REQUIRED_RUNTIME_NOTICE_SNAPSHOT_SHA256.get(snapshot_name)
            if (
                expected_digest is None
                or hashlib.sha256(snapshot).hexdigest() != expected_digest
            ):
                raise AssetCheckError(
                    f"{name}/{source} notice snapshot hash is not locked"
                )
            heading = f"===== {name}@{record.get('version')} :: {source} =====".encode()
            expected_headings.append(heading)
            if heading not in notice or snapshot.rstrip() not in notice:
                raise AssetCheckError(
                    f"NOTICE.txt is missing the complete {name}/{source} notice"
                )
            expected_sections.append(heading + b"\n" + snapshot.rstrip())
    actual_headings = [
        match.group(0)
        for match in re.finditer(rb"^===== [^\n]+ =====$", notice, re.MULTILINE)
    ]
    if actual_headings != expected_headings:
        raise AssetCheckError("NOTICE.txt runtime sections are incomplete or unexpected")
    actual_starts = [
        match.start()
        for match in re.finditer(rb"^===== [^\n]+ =====$", notice, re.MULTILINE)
    ]
    for index, expected_section in enumerate(expected_sections):
        end = actual_starts[index + 1] if index + 1 < len(actual_starts) else len(notice)
        actual_section = notice[actual_starts[index] : end].rstrip()
        if actual_section != expected_section:
            raise AssetCheckError("NOTICE.txt runtime section contents are not exact")
    if b"===== playwright@" in notice or b"===== esbuild@" in notice:
        raise AssetCheckError("test-only notices crossed into the runtime boundary")


def _runtime_package_closure(
    specification: Mapping[str, object],
    lockfile: Mapping[str, object],
) -> tuple[str, ...]:
    packages = lockfile.get("packages", {})
    discovered: set[str] = set()

    def visit(name: str) -> None:
        if name in discovered:
            return
        record = packages.get(f"node_modules/{name}")
        if not isinstance(record, Mapping):
            raise AssetCheckError(
                f"runtime package is missing from package-lock.json: {name}"
            )
        discovered.add(name)
        dependencies = record.get("dependencies", {})
        if not isinstance(dependencies, Mapping):
            raise AssetCheckError(f"{name} has invalid lockfile dependencies")
        for dependency in sorted(dependencies):
            visit(dependency)

    entry_points = specification.get("entry_points")
    if not isinstance(entry_points, list) or not all(
        isinstance(name, str) for name in entry_points
    ):
        raise AssetCheckError("runtime notice entry points are invalid")
    for name in entry_points:
        visit(name)
    return tuple(sorted(discovered))


def _check_record(name: str, record: Mapping[str, object], body: bytes) -> None:
    suffix = Path(name).suffix.lower()
    expected_media_type = MEDIA_TYPES.get(suffix)
    if expected_media_type is None or record.get("media_type") != expected_media_type:
        raise AssetCheckError(f"{name} has the wrong MIME type")
    cache_control = record.get("cache_control")
    expected_cache = (
        "public, max-age=31536000, immutable"
        if HASHED_ASSET.fullmatch(name)
        else "no-store"
    )
    if cache_control != expected_cache:
        raise AssetCheckError(f"{name} has the wrong cache policy")
    if name == MANIFEST_NAME:
        if set(record) != {"media_type", "cache_control"}:
            raise AssetCheckError("manifest.json must not contain a self-referential hash")
        return
    digest = record.get("sha256")
    size = record.get("size")
    if (
        not isinstance(digest, str)
        or not re.fullmatch(r"[0-9a-f]{64}", digest)
        or digest != hashlib.sha256(body).hexdigest()
    ):
        raise AssetCheckError(f"{name} has the wrong SHA-256 digest")
    if isinstance(size, bool) or not isinstance(size, int) or size != len(body):
        raise AssetCheckError(f"{name} has the wrong byte size")


def scan_text(name: str, body: bytes) -> None:
    """Reject forbidden generated content while preserving exact allowlisted URLs."""
    if Path(name).suffix.lower() not in {".css", ".html", ".js", ".json", ".svg", ".txt"}:
        return
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        raise AssetCheckError(f"{name} is not valid UTF-8 text")
    for pattern in FORBIDDEN_TEXT:
        if pattern.search(text):
            raise AssetCheckError(f"{name} contains forbidden content: {pattern.pattern}")
    if Path(name).name == "NOTICE.txt":
        # License text is a static attribution boundary, not an executable
        # network target. Preserve its exact upstream URLs.
        return
    aliases = _network_aliases(text)
    for match in EXTERNAL_URL.finditer(text):
        url = _normalize_url(match.group())
        if url not in ALLOWED_EXTERNAL_URLS:
            raise AssetCheckError(f"{name} contains an unallowlisted external URL: {url}")
        if _network_target_near(text, match.start(), aliases):
            raise AssetCheckError(f"{name} contains an external network target")


def _scan_text(name: str, body: bytes) -> None:
    """Backward-compatible private alias used by older callers."""
    scan_text(name, body)


def _network_aliases(text: str) -> frozenset[str]:
    """Find simple aliases for browser network-capable functions and methods."""
    aliases: set[str] = set()
    declarations = list(NETWORK_ALIAS_DECLARATION.finditer(text))
    changed = True
    while changed:
        changed = False
        for declaration in declarations:
            name, reference = declaration.groups()
            if name in aliases:
                continue
            if NETWORK_ALIAS_REFERENCE.fullmatch(reference.strip()) or reference.strip() in aliases:
                aliases.add(name)
                changed = True
    return frozenset(aliases)


def _network_target_near(text: str, start: int, aliases: frozenset[str]) -> bool:
    """Detect network-call syntax immediately before an external URL literal."""
    prefix = text[max(0, start - 512) : start]
    if any(pattern.search(prefix) for pattern in NETWORK_CALL_PREFIXES):
        return True
    if not aliases:
        return False
    names = "|".join(re.escape(alias) for alias in sorted(aliases, key=len, reverse=True))
    alias_call = re.compile(
        rf"(?ix)\b(?:{names})\b\s*(?:\.\s*(?:call|apply|bind)\s*)?"
        rf"\(\s*[^;{{}}]{{0,256}}\Z"
    )
    return alias_call.search(prefix) is not None


def _reject_symlinks(root: Path) -> None:
    if root.is_symlink():
        raise AssetCheckError("static output root must not be a symlink")
    for path in root.rglob("*"):
        if path.is_symlink():
            raise AssetCheckError(f"symlink in static output: {path.relative_to(root)}")


def _safe_name(name: str) -> bool:
    return bool(
        name
        and name.isascii()
        and "/" not in name
        and "\\" not in name
        and name not in {".", ".."}
    )


def _is_runtime_cache_artifact(relative: Path) -> bool:
    return (
        relative.parent.name == "__pycache__"
        and relative.suffix == ".pyc"
    )


def _normalize_url(value: str) -> str:
    return value.rstrip(".,;:!?)]}")


def _default_root() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "src"
        / "codesignal_practice_simulator"
        / "web"
        / "static"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--static-root",
        type=Path,
        default=_default_root(),
        help="generated static directory to validate",
    )
    arguments = parser.parse_args(argv)
    try:
        report = check_static_root(arguments.static_root)
    except (AssetCheckError, OSError) as error:
        print(f"asset check failed: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "assets": len(report.names),
                "manifest_sha256": report.manifest_sha256,
                "asset_hashes": dict(report.asset_hashes),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
