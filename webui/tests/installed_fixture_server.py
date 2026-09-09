"""Start the browser fixture using the installed simulator package only."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

import codesignal_practice_simulator as package
from codesignal_practice_simulator.web import resources
from codesignal_practice_simulator.application import RuntimeApplication
from codesignal_practice_simulator.web.server import WebServer, WebServerConfig
from codesignal_practice_simulator.workspace import CACHE_INPUTS, ValidatedFixtureCache


TOKEN = "installed-browser-fixture-token-" + "a" * 32


def main() -> None:
    _assert_installed_origins()
    with tempfile.TemporaryDirectory(prefix="installed-browser-fixture-") as directory:
        workspace = Path(directory) / "workspace"
        cache = workspace / ".cache" / "codesignal-fixtures" / "synthetic"
        paths = _cache_paths()
        _write_cache(cache, paths)
        manifest = workspace / "docs" / "migration-manifest.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(
            json.dumps(
                {
                    "fixture_cache_root": ".cache/codesignal-fixtures/synthetic",
                    "fetches": [
                        {
                            "cache_path": relative,
                            "sha256": hashlib.sha256(
                                (cache / relative).read_bytes()
                            ).hexdigest(),
                        }
                        for relative in paths
                    ],
                }
            ),
            encoding="utf-8",
        )
        application = RuntimeApplication(
            workspace,
            cache=ValidatedFixtureCache.from_manifest(manifest),
        )
        application.start(
            assessment="file_storage",
            mode="drill",
            drill_duration_seconds=60,
        )
        server = WebServer(
            WebServerConfig(workspace, no_open=True, token=TOKEN),
            application=application,
        )
        try:
            url = server.start()
            print(json.dumps({"origin": url.split("/#", 1)[0], "token": TOKEN}), flush=True)
            sys.stdin.buffer.read()
        finally:
            server.stop()


def _assert_installed_origins() -> None:
    prefix = Path(sys.prefix).resolve()
    origins = (
        Path(package.__file__).resolve(),
        Path(resources.__file__).resolve(),
    )
    if not all(origin.is_relative_to(prefix) for origin in origins):
        raise RuntimeError(f"browser server imported outside venv: {origins}")
    source = os.environ.get("SIMULATOR_SOURCE_ROOT")
    if source and any(origin.is_relative_to(Path(source).resolve()) for origin in origins):
        raise RuntimeError(f"browser server imported from checkout: {origins}")


def _cache_paths() -> tuple[str, ...]:
    return ("vendor-readme.md",) + tuple(
        f"assessment/file_storage/{name}" for name in CACHE_INPUTS
    )


def _write_cache(cache: Path, paths: tuple[str, ...]) -> None:
    for relative in paths:
        path = cache / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if relative.endswith("simulation.py"):
            content = "print('synthetic safe workspace')\n"
        elif relative.endswith(".md"):
            content = f"synthetic prompt for {relative}\n"
        else:
            content = f"# synthetic fixture for {relative}\n"
        path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
