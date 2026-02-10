"""Tests for cross-platform compatibility across the simulation pipeline."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from simulation.ngspice_runner import NgspiceRunner


class TestNgspiceRunnerPlatformDetection:
    """Verify ngspice discovery uses platform-appropriate paths."""

    def test_find_ngspice_uses_shutil_which_first(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        with patch("shutil.which", return_value="/usr/bin/ngspice"):
            result = runner.find_ngspice()
        assert result == "/usr/bin/ngspice"

    def test_find_ngspice_returns_none_when_not_found(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        with (
            patch("shutil.which", return_value=None),
            patch("os.path.exists", return_value=False),
        ):
            result = runner.find_ngspice()
        assert result is None

    def test_find_ngspice_checks_linux_paths(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        checked_paths = []
        with (
            patch("shutil.which", return_value=None),
            patch("platform.system", return_value="Linux"),
            patch("os.path.exists", side_effect=lambda p: (checked_paths.append(p), False)[1]),
        ):
            runner.find_ngspice()
        assert "/usr/bin/ngspice" in checked_paths
        assert "/usr/local/bin/ngspice" in checked_paths

    def test_find_ngspice_checks_macos_paths(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        checked_paths = []
        with (
            patch("shutil.which", return_value=None),
            patch("platform.system", return_value="Darwin"),
            patch("os.path.exists", side_effect=lambda p: (checked_paths.append(p), False)[1]),
        ):
            runner.find_ngspice()
        assert "/usr/local/bin/ngspice" in checked_paths
        assert "/opt/homebrew/bin/ngspice" in checked_paths

    def test_find_ngspice_checks_windows_paths(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        checked_paths = []
        with (
            patch("shutil.which", return_value=None),
            patch("platform.system", return_value="Windows"),
            patch("os.path.exists", side_effect=lambda p: (checked_paths.append(p), False)[1]),
        ):
            runner.find_ngspice()
        assert any("ngspice" in p.lower() for p in checked_paths)
        assert any("Program Files" in p for p in checked_paths)


class TestOutputDirCreation:
    """Verify output directory is created cross-platform."""

    def test_output_dir_created(self, tmp_path):
        out_dir = tmp_path / "sim_output"
        NgspiceRunner(output_dir=str(out_dir))
        assert out_dir.exists()

    def test_nested_output_dir_created(self, tmp_path):
        out_dir = tmp_path / "a" / "b" / "output"
        NgspiceRunner(output_dir=str(out_dir))
        assert out_dir.exists()


class TestPathHandling:
    """Verify paths work consistently across platforms."""

    def test_pathlib_home_exists(self):
        """Path.home() should work on all platforms."""
        home = Path.home()
        assert home.exists()

    def test_os_path_join_produces_valid_path(self, tmp_path):
        """os.path.join should produce valid paths on any platform."""
        path = os.path.join(str(tmp_path), "subdir", "file.txt")
        parent = os.path.dirname(path)
        os.makedirs(parent, exist_ok=True)
        with open(path, "w") as f:
            f.write("test")
        assert os.path.exists(path)
