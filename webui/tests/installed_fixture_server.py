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
from fixture_controls import (
    browser_opener_from_environment,
    clock_from_environment,
    install_score_call_recorder,
)


TOKEN = "installed-browser-fixture-token-" + "a" * 32


def main() -> None:
    _assert_installed_origins()
    configured = os.environ.get("SIMULATOR_WORKSPACE")
    if configured:
        _serve(Path(configured))
        return
    with tempfile.TemporaryDirectory(prefix="installed-browser-fixture-") as directory:
        _serve(Path(directory) / "workspace")


def _serve(workspace: Path) -> None:
    token = os.environ.get("SIMULATOR_FIXTURE_TOKEN", TOKEN)
    workspace.mkdir(parents=True, exist_ok=True)
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
        clock=clock_from_environment(),
        cache=ValidatedFixtureCache.from_manifest(manifest),
    )
    install_score_call_recorder(application)
    server = WebServer(
        WebServerConfig(
            workspace,
            port=int(os.environ.get("SIMULATOR_SERVER_PORT", "0")),
            no_open=False,
            token=token,
            browser_opener=browser_opener_from_environment(),
        ),
        application=application,
    )
    try:
        url = server.start()
        server.open_browser()
        print(json.dumps({"origin": url.split("/#", 1)[0]}), flush=True)
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
        if relative == "assessment/file_storage/simulation.py":
            content = (
                "def evaluate(group):\n"
                "    return 'ok'\n"
            )
        elif relative == "assessment/file_storage/test_simulation.py":
            content = (
                "import unittest\n"
                "from simulation import evaluate\n"
                "\n"
                "class TestSimulateCodingFramework(unittest.TestCase):\n"
                "    def test_group_1(self): self.assertEqual(evaluate(1), 'ok')\n"
                "    def test_group_2(self): self.assertEqual(evaluate(2), 'ok')\n"
                "    def test_group_3(self): self.assertEqual(evaluate(3), 'ok')\n"
                "    def test_group_4(self): self.assertEqual(evaluate(4), 'ok')\n"
            )
        elif relative.endswith(".md"):
            content = f"synthetic prompt for {relative}\n"
        else:
            content = f"# synthetic fixture for {relative}\n"
        path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
