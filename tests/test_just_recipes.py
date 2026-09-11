"""Execute Just routing and the real dev launcher in isolated workspaces."""

from __future__ import annotations

import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request


PROJECT = Path(__file__).resolve().parents[1]
JUST = shutil.which("just")


@unittest.skipUnless(JUST, "optional Just executable is not installed")
class JustRecipeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="simulator-just-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "project with spaces"
        self.root.mkdir()
        shutil.copy(PROJECT / "justfile", self.root / "justfile")
        shutil.copytree(PROJECT / ".justfiles", self.root / ".justfiles")
        self.environment = dict(os.environ)
        for key in ("PYTHON", "SIMULATOR_WORKSPACE", "JUST_UNSTABLE"):
            self.environment.pop(key, None)

    def run_just(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [JUST, *args], cwd=cwd or self.root, env=self.environment,
            capture_output=True, text=True, timeout=20,
        )

    def test_menus_are_namespaced_and_legacy_shortcuts_still_resolve(self) -> None:
        menu = self.run_just("--list")
        self.assertEqual(menu.returncode, 0, menu.stderr)
        for name in ("dev", "setup", "fetch", "verify", "app ...", "build ...", "check ...", "study ..."):
            self.assertIn(name, menu.stdout)
        self.assertNotIn("practice-drill", menu.stdout)
        for module in ("app", "build", "check", "study"):
            result = self.run_just(module)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Available recipes:", result.stdout)
        for recipe in ("practice", "resume", "status", "time", "test", "submit", "context", "task", "attempts", "test-compat", "study-spec", "study-stages", "test-all", "clean"):
            result = self.run_just("--dry-run", recipe)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_root_overrides_and_parameterized_compatibility(self) -> None:
        result = self.run_just("--dry-run", "python=/custom/python", "verify")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr.count("'/custom/python'"), 3)
        result = self.run_just("--dry-run", "workspace=/custom/work space", "fetch")
        self.assertIn("--workspace-root '/custom/work space'", result.stderr)
        result = self.run_just("--dry-run", "practice-drill", "60")
        self.assertIn("--drill-duration-seconds '60'", result.stderr)
        result = self.run_just("--dry-run", "study-check", "2", "/tmp/study file.py")
        self.assertIn("check.py '2' '/tmp/study file.py'", result.stderr)

    def test_missing_install_is_actionable_and_does_not_fetch(self) -> None:
        result = self.run_just("dev", "--no-open")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Run just setup", result.stderr)
        self.assertFalse((self.root / ".cache").exists())
        self.assertFalse((self.root / "attempts").exists())

    def write_executable(self, name: str, body: str) -> Path:
        script = self.root / name
        script.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
        script.chmod(0o700)
        return script

    def test_dev_forwards_arguments_without_shell_expansion(self) -> None:
        executable = self.write_executable(
            "fake simulator", "import json, sys\nprint(json.dumps(sys.argv[1:]))\n"
        )
        self.environment["SIMULATOR_WORKSPACE"] = str(self.root / "isolated workspace")
        result = self.run_just(
            f"simulator={executable}", "dev", "--no-open", "--port", "8123",
            "--workspace-root", "literal $(touch SHOULD_NOT_EXIST)",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [
            "web", "--workspace-root", self.environment["SIMULATOR_WORKSPACE"],
            "--port", "0", "--no-open", "--port", "8123", "--workspace-root",
            "literal $(touch SHOULD_NOT_EXIST)",
        ])
        self.assertFalse((self.root / "SHOULD_NOT_EXIST").exists())

    def test_module_commands_run_at_project_root_from_nested_directory(self) -> None:
        executable = self.write_executable(
            "fake python", "import os\nprint(os.getcwd())\n"
        )
        nested = self.root / "nested"
        nested.mkdir()
        result = self.run_just(f"check::python={executable}", "check", "unit", cwd=nested)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()).resolve(), self.root.resolve())
        result = self.run_just("app", "attempts", cwd=nested)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    @unittest.skipUnless(os.name == "posix", "POSIX launcher shutdown check")
    def test_dev_serves_real_bundled_app_and_stops_on_repeated_interrupts(self) -> None:
        executable = self.write_executable(
            "real simulator", "import sys\n"
            f"sys.path.insert(0, {str(PROJECT / 'src')!r})\n"
            "from codesignal_practice_simulator.cli import main\n"
            "from codesignal_practice_simulator.web.server import WebServer\n"
            "import os, signal\n"
            "original_stop = WebServer.stop\n"
            "def interrupted_stop(server):\n"
            "    os.kill(os.getpid(), signal.SIGINT)\n"
            "    os.kill(os.getpid(), signal.SIGINT)\n"
            "    original_stop(server)\n"
            "WebServer.stop = interrupted_stop\n"
            "raise SystemExit(main())\n",
        )
        process = subprocess.Popen(
            [JUST, f"simulator={executable}", "dev", "--no-open", "--json"],
            cwd=self.root, env=self.environment, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, start_new_session=True,
        )
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                self.assertTrue(selector.select(15), "dev did not report startup")
                startup = json.loads(process.stdout.readline())
            self.assertTrue(startup["ok"], "dev startup failed")
            port = startup["result"]["port"]
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(f"http://127.0.0.1:{port}/", timeout=5) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(b"<html", response.read().lower())
            self.assertFalse((self.root / "attempts").exists())
            self.assertFalse((self.root / ".cache").exists())
            os.killpg(process.pid, signal.SIGINT)
            _, stderr = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0)
            self.assertNotIn("Traceback", stderr)
            self.assertNotIn("KeyboardInterrupt", stderr)
            self.assertNotIn("terminated by signal", stderr)
            with self.assertRaises(urllib.error.URLError):
                opener.open(f"http://127.0.0.1:{port}/", timeout=1)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
            process.stdout.close()
            process.stderr.close()
