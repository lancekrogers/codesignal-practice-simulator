"""Start the real Python web server with a synthetic, safe workspace."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from codesignal_practice_simulator.application import RuntimeApplication
from codesignal_practice_simulator.web.server import WebServer, WebServerConfig
from codesignal_practice_simulator.workspace import CACHE_INPUTS, ValidatedFixtureCache
from fixture_controls import clock_from_environment, install_score_call_recorder


TOKEN = "browser-fixture-token-" + "a" * 32


def main() -> None:
    configured = os.environ.get("SIMULATOR_WORKSPACE")
    if configured:
        workspace = Path(configured)
        workspace.mkdir(parents=True, exist_ok=True)
        _serve(workspace)
        return
    with tempfile.TemporaryDirectory(prefix="browser-fixture-") as directory:
        _serve(Path(directory) / "workspace")


def _serve(workspace: Path) -> None:
    cache = workspace / ".cache" / "codesignal-fixtures" / "synthetic"
    _write_cache(cache)
    manifest = workspace / "docs" / "migration-manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    fetches = [
            {
                "cache_path": relative,
                "sha256": hashlib.sha256((cache / relative).read_bytes()).hexdigest(),
            }
            for relative in _cache_paths()
    ]
    manifest.write_text(
        json.dumps(
            {
                "fixture_cache_root": ".cache/codesignal-fixtures/synthetic",
                "fetches": fetches,
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
            no_open=True,
            token=TOKEN,
        ),
        application=application,
    )
    try:
        url = server.start()
        print(json.dumps({"origin": url.split("/#", 1)[0], "token": TOKEN}), flush=True)
        sys.stdin.buffer.read()
    finally:
        server.stop()


def _cache_paths() -> tuple[str, ...]:
    return ("vendor-readme.md",) + tuple(
        f"assessment/file_storage/{name}" for name in CACHE_INPUTS
    )


def _write_cache(cache: Path) -> None:
    for relative in _cache_paths():
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
