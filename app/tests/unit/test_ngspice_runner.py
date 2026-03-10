"""Tests for NgspiceRunner (#497, #502)."""

import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest
from simulation.ngspice_runner import NgspiceRunner


class TestInit:
    """Constructor tests."""

    def test_creates_output_dir(self, tmp_path):
        output_dir = tmp_path / "sim_out"
        runner = NgspiceRunner(output_dir=str(output_dir))
        assert output_dir.exists()
        assert runner.ngspice_cmd is None


class TestFindNgspice:
    """Tests for find_ngspice()."""

    def test_found_via_shutil_which(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        with patch("simulation.ngspice_runner.shutil.which", return_value="/usr/bin/ngspice"):
            result = runner.find_ngspice()
        assert result == "/usr/bin/ngspice"
        assert runner.ngspice_cmd == "/usr/bin/ngspice"

    def test_not_found_returns_none(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        with (
            patch("simulation.ngspice_runner.shutil.which", return_value=None),
            patch("simulation.ngspice_runner.os.path.exists", return_value=False),
        ):
            result = runner.find_ngspice()
        assert result is None
        assert runner.ngspice_cmd is None

    def test_fallback_path_found(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))

        def fake_exists(path):
            return path == "/usr/local/bin/ngspice"

        with (
            patch("simulation.ngspice_runner.shutil.which", return_value=None),
            patch("simulation.ngspice_runner.platform.system", return_value="Linux"),
            patch("simulation.ngspice_runner.os.path.exists", side_effect=fake_exists),
        ):
            result = runner.find_ngspice()
        assert result == "/usr/local/bin/ngspice"


class TestRunSimulation:
    """Tests for run_simulation()."""

    def test_ngspice_not_found(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        with (
            patch("simulation.ngspice_runner.shutil.which", return_value=None),
            patch("simulation.ngspice_runner.os.path.exists", return_value=False),
        ):
            success, output_file, stdout, stderr = runner.run_simulation("test netlist")
        assert success is False
        assert "not found" in stderr

    def test_timeout_returns_failure(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        runner.ngspice_cmd = "/usr/bin/ngspice"
        with patch(
            "simulation.ngspice_runner.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="ngspice", timeout=30),
        ):
            success, output_file, stdout, stderr = runner.run_simulation("test netlist")
        assert success is False
        assert "timed out" in stderr.lower()

    def test_subprocess_error_returns_failure(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        runner.ngspice_cmd = "/usr/bin/ngspice"
        with patch(
            "simulation.ngspice_runner.subprocess.run",
            side_effect=OSError("Permission denied"),
        ):
            success, output_file, stdout, stderr = runner.run_simulation("test netlist")
        assert success is False
        assert "Permission denied" in stderr

    def test_netlist_write_error(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        runner.ngspice_cmd = "/usr/bin/ngspice"
        with patch("builtins.open", side_effect=OSError("disk full")):
            success, output_file, stdout, stderr = runner.run_simulation("test netlist")
        assert success is False
        assert "disk full" in stderr


class TestReadOutput:
    """Tests for read_output()."""

    def test_reads_existing_file(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        outfile = tmp_path / "output.txt"
        outfile.write_text("v(1) = 5.0\n")
        result = runner.read_output(str(outfile))
        assert "v(1) = 5.0" in result

    def test_missing_file_returns_error_string(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        result = runner.read_output("/nonexistent/output.txt")
        assert "Error reading output" in result


class TestEmptyOutputDetection:
    """Issue #497: empty output file must not be treated as success."""

    def test_empty_output_file_returns_failure(self, tmp_path):
        """An empty output file should return success=False."""
        runner = NgspiceRunner(output_dir=str(tmp_path))
        runner.ngspice_cmd = "/usr/bin/true"  # placeholder

        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch("simulation.ngspice_runner.subprocess.run", return_value=mock_result):
            original_exists = os.path.exists

            def mock_exists(path):
                if "output_" in str(path):
                    # Create the empty file so it exists but has size 0
                    open(path, "w").close()
                    return True
                return original_exists(path)

            with patch("simulation.ngspice_runner.os.path.exists", side_effect=mock_exists):
                success, output_file, stdout, stderr = runner.run_simulation("test netlist")

        assert success is False
        assert output_file is None

    def test_nonempty_output_file_returns_success(self, tmp_path):
        """A non-empty output file should return success=True."""
        runner = NgspiceRunner(output_dir=str(tmp_path))
        runner.ngspice_cmd = "/usr/bin/true"

        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        def fake_run(cmd, **kwargs):
            # cmd is [ngspice, "-b", netlist, "-o", output]
            output_path = cmd[4]
            with open(output_path, "w") as f:
                f.write("simulation results\n")
            return mock_result

        with patch("simulation.ngspice_runner.subprocess.run", side_effect=fake_run):
            success, output_file, stdout, stderr = runner.run_simulation("test netlist")

        assert success is True
        assert output_file is not None

    def test_missing_output_file_returns_failure(self, tmp_path):
        """A missing output file should return success=False."""
        runner = NgspiceRunner(output_dir=str(tmp_path))
        runner.ngspice_cmd = "/usr/bin/true"

        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch("simulation.ngspice_runner.subprocess.run", return_value=mock_result):
            success, output_file, stdout, stderr = runner.run_simulation("test netlist")

        assert success is False
        assert output_file is None
        assert "no output" in stderr.lower() or "not created" in stderr.lower()
