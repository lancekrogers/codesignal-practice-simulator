"""Focused unit tests for packaging prerequisite and resource checks."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
import venv
import zipfile
from pathlib import Path
from unittest.mock import patch


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))

import packaging_support  # noqa: E402
import run_packaged_browser  # noqa: E402


PACKAGE = run_packaged_browser.PACKAGE_NAME


def _write_wheel(path: Path, members: list[str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for member in members:
            archive.writestr(member, b"synthetic")


def _write_sdist(path: Path, members: list[str]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for member in members:
            info = tarfile.TarInfo(member)
            info.size = len(b"synthetic")
            archive.addfile(info, io.BytesIO(b"synthetic"))


class PackagingInterpreterTests(unittest.TestCase):
    def test_discovery_rejects_missing_wheel_and_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first-python"
            second = Path(directory) / "second-python"
            first.touch()
            second.touch()
            required = packaging_support._required_modules(require_build=True)
            with (
                patch.dict(
                    os.environ,
                    {"ASSET_BUILDER": str(first)},
                    clear=False,
                ),
                patch.object(packaging_support.sys, "executable", str(second)),
                patch.object(packaging_support.shutil, "which", return_value=None),
                patch.object(
                    packaging_support, "_probe", side_effect=(False, True)
                ) as probe,
            ):
                selected = packaging_support.discover_packaging_interpreter(
                    require_build=True
                )
        self.assertEqual(selected, second.absolute())
        self.assertEqual(
            probe.call_args_list,
            [
                ((first.absolute(),), {"required_modules": required}),
                ((second.absolute(),), {"required_modules": required}),
            ],
        )
        self.assertIn("wheel", required)
        self.assertIn("build", required)

    def test_probe_imports_every_declared_prerequisite(self) -> None:
        required = packaging_support._required_modules(require_build=True)
        with tempfile.TemporaryDirectory() as directory:
            venv_root = Path(directory) / "packaging-venv"
            builder = venv.EnvBuilder(with_pip=False)
            context = builder.ensure_directories(venv_root)
            builder.create(venv_root)
            child_info = json.loads(
                subprocess.check_output(
                    [
                        context.env_exec_cmd,
                        "-c",
                        (
                            "import json, sys, sysconfig; "
                            "print(json.dumps({"
                            "'executable': sys.executable, "
                            "'platform': sysconfig.get_platform(), "
                            "'site_packages': sysconfig.get_path('purelib')"
                            "}))"
                        ),
                    ],
                    text=True,
                )
            )
            interpreter = Path(child_info["executable"])
            site_packages = Path(child_info["site_packages"])
            self.assertTrue(child_info["platform"])
            for module in ("setuptools", "pip", "build"):
                (site_packages / f"{module}.py").write_text(
                    "# synthetic empty prerequisite stub\n",
                    encoding="utf-8",
                )

            clean_environment = {
                key: value
                for key, value in os.environ.items()
                if not key.startswith("PYTHON")
            }
            with patch.dict(os.environ, clean_environment, clear=True):
                self.assertFalse(
                    packaging_support._probe(
                        interpreter, required_modules=required
                    )
                )
                (site_packages / "wheel.py").write_text(
                    "# synthetic empty prerequisite stub\n",
                    encoding="utf-8",
                )
                self.assertTrue(
                    packaging_support._probe(
                        interpreter, required_modules=required
                    )
                )

    def test_missing_prerequisite_error_names_wheel_and_remediation(self) -> None:
        error = packaging_support.packaging_prerequisite_error(require_build=True)
        self.assertIn("wheel", error)
        self.assertIn("build", error)
        self.assertIn("ASSET_BUILDER", error)
        self.assertIn("ensurepip", error)


class ArchiveResourceTests(unittest.TestCase):
    def test_declared_resources_and_package_files_are_accepted(self) -> None:
        wheel_members = [
            f"{PACKAGE}/__init__.py",
            f"{PACKAGE}/web/server.py",
            f"{PACKAGE}/resources/fixture-manifest.json",
            f"{PACKAGE}/web/static/app.js",
        ]
        source_members = [
            f"package-0.1/src/{PACKAGE}/__init__.py",
            f"package-0.1/src/{PACKAGE}/web/server.py",
            f"package-0.1/src/{PACKAGE}/resources/fixture-manifest.json",
            f"package-0.1/src/{PACKAGE}/web/static/app.js",
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wheel = root / "package.whl"
            source = root / "package.tar.gz"
            _write_wheel(wheel, wheel_members)
            _write_sdist(source, source_members)
            with zipfile.ZipFile(wheel) as archive:
                run_packaged_browser._assert_runtime_package_resources(
                    [member.filename for member in archive.infolist() if not member.is_dir()],
                    prefix=f"{PACKAGE}/",
                    static_prefix=run_packaged_browser.STATIC_PREFIX,
                )
            with tarfile.open(source) as archive:
                run_packaged_browser._assert_runtime_package_resources(
                    [member.name for member in archive.getmembers() if member.isfile()],
                    prefix="/src/" + f"{PACKAGE}/",
                    static_prefix="/src/" + run_packaged_browser.STATIC_PREFIX,
                )

    def test_wheel_rejects_unexpected_resource_names(self) -> None:
        for resource in ("resources/fixture.json", "resources/nested/fixture.json"):
            with self.subTest(resource=resource), tempfile.TemporaryDirectory() as directory:
                wheel = Path(directory) / "package.whl"
                _write_wheel(wheel, [f"{PACKAGE}/{resource}"])
                with zipfile.ZipFile(wheel) as archive:
                    with self.assertRaisesRegex(
                        RuntimeError, r"unexpected non-static package resource member"
                    ):
                        run_packaged_browser._assert_runtime_package_resources(
                            [
                                member.filename
                                for member in archive.infolist()
                                if not member.is_dir()
                            ],
                            prefix=f"{PACKAGE}/",
                            static_prefix=run_packaged_browser.STATIC_PREFIX,
                        )

    def test_sdist_rejects_unexpected_resource_names(self) -> None:
        for resource in ("resources/fixture.json", "resources/nested/fixture.json"):
            with self.subTest(resource=resource), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "package.tar.gz"
                _write_sdist(source, [f"package-0.1/src/{PACKAGE}/{resource}"])
                with tarfile.open(source) as archive:
                    with self.assertRaisesRegex(
                        RuntimeError, r"unexpected non-static package resource member"
                    ):
                        run_packaged_browser._assert_runtime_package_resources(
                            [
                                member.name
                                for member in archive.getmembers()
                                if member.isfile()
                            ],
                            prefix="/src/" + f"{PACKAGE}/",
                            static_prefix="/src/" + run_packaged_browser.STATIC_PREFIX,
                        )


if __name__ == "__main__":
    unittest.main()
