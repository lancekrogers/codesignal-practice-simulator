"""Tests for the canonical local compatibility-check orchestrator."""

from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))

import run_legacy_checks  # noqa: E402


class LegacyCheckRunnerTests(unittest.TestCase):
    def test_commands_are_ordered_and_never_include_upstream_tests(self) -> None:
        interpreter = "/test/python"

        self.assertEqual(
            run_legacy_checks.commands(interpreter),
            [
                [
                    interpreter,
                    "scripts/verify_manifest.py",
                    "--manifest",
                    "docs/migration-manifest.json",
                    "--scope",
                    "tracked",
                ],
                [
                    interpreter,
                    "scripts/verify_manifest.py",
                    "--manifest",
                    "docs/migration-manifest.json",
                    "--scope",
                    "fixture-cache",
                ],
                [
                    interpreter,
                    "scripts/verify_manifest.py",
                    "--manifest",
                    "docs/migration-manifest.json",
                    "--scope",
                    "git-boundary",
                ],
                [interpreter, "solution/test_spec.py"],
                [interpreter, "solution/test_stages.py"],
                [interpreter, "study/check.py", "1", "study/level1.py"],
                [interpreter, "study/check.py", "2", "study/level2.py"],
                [interpreter, "study/check.py", "3", "study/level3.py"],
                [interpreter, "study/check.py", "4", "study/level4.py"],
            ],
        )
        self.assertFalse(
            any(
                "test_simulation.py" in argument
                for command in run_legacy_checks.commands(interpreter)
                for argument in command
            )
        )

    def test_commands_use_supplied_interpreter_and_project_root(self) -> None:
        project_root = Path("/temporary/project")
        interpreter = "/temporary/python"
        expected_commands = run_legacy_checks.commands(interpreter)

        with (
            patch.object(
                run_legacy_checks.subprocess,
                "run",
                side_effect=lambda command, **_kwargs: subprocess.CompletedProcess(
                    command, 0
                ),
            ) as run,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(run_legacy_checks.run_checks(project_root, interpreter), 0)

        self.assertEqual(
            [call.args[0] for call in run.call_args_list],
            expected_commands,
        )
        for call in run.call_args_list:
            self.assertEqual(call.kwargs, {"cwd": project_root, "check": False})

    def test_failure_stops_before_later_commands(self) -> None:
        commands = run_legacy_checks.commands("/temporary/python")

        def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess:
            return subprocess.CompletedProcess(command, 23 if command == commands[2] else 0)

        with (
            patch.object(run_legacy_checks.subprocess, "run", side_effect=run) as mocked_run,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(
                run_legacy_checks.run_checks(Path("/temporary/project"), commands[0][0]),
                23,
            )

        self.assertEqual(
            [call.args[0] for call in mocked_run.call_args_list],
            commands[:3],
        )

    def test_fixture_cache_failures_preserve_errors_and_show_recovery_guidance(
        self,
    ) -> None:
        interpreter = "/temporary/python"
        commands = run_legacy_checks.commands(interpreter)
        guidance = run_legacy_checks.fixture_cache_guidance(
            run_legacy_checks.PROJECT_ROOT
        )
        failures = (
            "ERROR: fixture cache is absent: /temporary/cache.",
            "ERROR: fixture cache has an invalid file set: missing test.py.",
            "ERROR: fixture cache hash mismatch for test.py: expected expected, got actual.",
        )

        for failure in failures:
            with self.subTest(failure=failure):
                def run(
                    command: list[str], **_kwargs: object
                ) -> subprocess.CompletedProcess:
                    if command[-1] == "fixture-cache":
                        print(failure, file=sys.stderr)
                        return subprocess.CompletedProcess(command, 1)
                    return subprocess.CompletedProcess(command, 0)

                stderr = io.StringIO()
                with (
                    patch.object(
                        run_legacy_checks.subprocess, "run", side_effect=run
                    ) as mocked_run,
                    contextlib.redirect_stderr(stderr),
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    self.assertEqual(
                        run_legacy_checks.run_checks(
                            run_legacy_checks.PROJECT_ROOT, interpreter
                        ),
                        1,
                    )

                self.assertEqual(stderr.getvalue().splitlines(), [failure, guidance])
                self.assertEqual(
                    [call.args[0] for call in mocked_run.call_args_list], commands[:2]
                )


if __name__ == "__main__":
    unittest.main()
