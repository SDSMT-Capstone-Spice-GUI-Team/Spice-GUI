"""Unit tests for simulation/ngspice_runner.py — NgspiceRunner.

All subprocess and filesystem interactions are mocked so no ngspice
installation is required.
"""

import os
import subprocess
from unittest.mock import MagicMock, mock_open, patch

import pytest
from simulation.ngspice_runner import NgspiceRunner

# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestNgspiceRunnerInit:
    def test_creates_output_dir(self, tmp_path):
        out = tmp_path / "sim_output"
        NgspiceRunner(output_dir=str(out))
        assert out.is_dir()

    def test_stores_output_dir(self, tmp_path):
        out = tmp_path / "sim_output"
        runner = NgspiceRunner(output_dir=str(out))
        assert runner.output_dir == str(out)

    def test_ngspice_cmd_initially_none(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path / "out"))
        assert runner.ngspice_cmd is None

    def test_existing_dir_ok(self, tmp_path):
        out = tmp_path / "existing"
        out.mkdir()
        runner = NgspiceRunner(output_dir=str(out))
        assert runner.output_dir == str(out)


# ---------------------------------------------------------------------------
# find_ngspice
# ---------------------------------------------------------------------------


class TestFindNgspice:
    def test_found_via_which(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        with patch("simulation.ngspice_runner.shutil.which", return_value="/usr/bin/ngspice"):
            result = runner.find_ngspice()
        assert result == "/usr/bin/ngspice"
        assert runner.ngspice_cmd == "/usr/bin/ngspice"

    def test_fallback_linux(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        with (
            patch("simulation.ngspice_runner.shutil.which", return_value=None),
            patch("simulation.ngspice_runner.platform.system", return_value="Linux"),
            patch("simulation.ngspice_runner.os.path.exists", side_effect=lambda p: p == "/usr/local/bin/ngspice"),
        ):
            result = runner.find_ngspice()
        assert result == "/usr/local/bin/ngspice"
        assert runner.ngspice_cmd == "/usr/local/bin/ngspice"

    def test_fallback_windows(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        expected = r"C:\Program Files\ngspice\bin\ngspice.exe"
        with (
            patch("simulation.ngspice_runner.shutil.which", return_value=None),
            patch("simulation.ngspice_runner.platform.system", return_value="Windows"),
            patch("simulation.ngspice_runner.os.path.exists", side_effect=lambda p: p == expected),
        ):
            result = runner.find_ngspice()
        assert result == expected

    def test_fallback_darwin(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        with (
            patch("simulation.ngspice_runner.shutil.which", return_value=None),
            patch("simulation.ngspice_runner.platform.system", return_value="Darwin"),
            patch("simulation.ngspice_runner.os.path.exists", side_effect=lambda p: p == "/opt/homebrew/bin/ngspice"),
        ):
            result = runner.find_ngspice()
        assert result == "/opt/homebrew/bin/ngspice"

    def test_not_found_anywhere(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        with (
            patch("simulation.ngspice_runner.shutil.which", return_value=None),
            patch("simulation.ngspice_runner.platform.system", return_value="Linux"),
            patch("simulation.ngspice_runner.os.path.exists", return_value=False),
        ):
            result = runner.find_ngspice()
        assert result is None
        assert runner.ngspice_cmd is None

    def test_unknown_platform_no_fallbacks(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        with (
            patch("simulation.ngspice_runner.shutil.which", return_value=None),
            patch("simulation.ngspice_runner.platform.system", return_value="FreeBSD"),
        ):
            result = runner.find_ngspice()
        assert result is None


# ---------------------------------------------------------------------------
# run_simulation
# ---------------------------------------------------------------------------


class TestRunSimulation:
    def test_success(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        runner.ngspice_cmd = "/usr/bin/ngspice"

        mock_result = MagicMock()
        mock_result.stdout = "sim stdout"
        mock_result.stderr = ""

        with (
            patch("simulation.ngspice_runner.subprocess.run", return_value=mock_result),
            patch("simulation.ngspice_runner.os.path.exists", return_value=True),
        ):
            success, outfile, stdout, stderr = runner.run_simulation("* test netlist\n.end")

        assert success is True
        assert outfile is not None
        assert stdout == "sim stdout"

    def test_output_file_not_created(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        runner.ngspice_cmd = "/usr/bin/ngspice"

        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = "error occurred"

        with (
            patch("simulation.ngspice_runner.subprocess.run", return_value=mock_result),
            patch("simulation.ngspice_runner.os.path.exists", return_value=False),
        ):
            success, outfile, stdout, stderr = runner.run_simulation("* test\n.end")

        assert success is False
        assert outfile is None
        assert stderr == "error occurred"

    def test_output_file_not_created_empty_stderr(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        runner.ngspice_cmd = "/usr/bin/ngspice"

        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""

        with (
            patch("simulation.ngspice_runner.subprocess.run", return_value=mock_result),
            patch("simulation.ngspice_runner.os.path.exists", return_value=False),
        ):
            success, outfile, stdout, stderr = runner.run_simulation("* test\n.end")

        assert success is False
        assert stderr == "Output file not created"

    def test_timeout(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        runner.ngspice_cmd = "/usr/bin/ngspice"

        with patch(
            "simulation.ngspice_runner.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="ngspice", timeout=60),
        ):
            success, outfile, stdout, stderr = runner.run_simulation("* test\n.end")

        assert success is False
        assert outfile is None
        assert "timed out" in stderr.lower()

    def test_oserror_on_subprocess(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        runner.ngspice_cmd = "/usr/bin/ngspice"

        with patch(
            "simulation.ngspice_runner.subprocess.run",
            side_effect=OSError("exec failed"),
        ):
            success, outfile, stdout, stderr = runner.run_simulation("* test\n.end")

        assert success is False
        assert "exec failed" in stderr

    def test_oserror_on_netlist_write(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        runner.ngspice_cmd = "/usr/bin/ngspice"

        with patch("builtins.open", side_effect=OSError("permission denied")):
            success, outfile, stdout, stderr = runner.run_simulation("* test\n.end")

        assert success is False
        assert "permission denied" in stderr.lower()

    def test_auto_finds_ngspice_when_cmd_is_none(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        assert runner.ngspice_cmd is None

        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""

        with (
            patch("simulation.ngspice_runner.shutil.which", return_value="/usr/bin/ngspice"),
            patch("simulation.ngspice_runner.subprocess.run", return_value=mock_result),
            patch("simulation.ngspice_runner.os.path.exists", return_value=True),
        ):
            success, outfile, stdout, stderr = runner.run_simulation("* test\n.end")

        assert success is True
        assert runner.ngspice_cmd == "/usr/bin/ngspice"

    def test_returns_error_when_ngspice_not_found(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        assert runner.ngspice_cmd is None

        with (
            patch("simulation.ngspice_runner.shutil.which", return_value=None),
            patch("simulation.ngspice_runner.platform.system", return_value="Linux"),
            patch("simulation.ngspice_runner.os.path.exists", return_value=False),
        ):
            success, outfile, stdout, stderr = runner.run_simulation("* test\n.end")

        assert success is False
        assert "not found" in stderr.lower()

    def test_subprocess_called_with_correct_args(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        runner.ngspice_cmd = "/usr/bin/ngspice"

        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""

        with (
            patch("simulation.ngspice_runner.subprocess.run", return_value=mock_result) as mock_run,
            patch("simulation.ngspice_runner.os.path.exists", return_value=True),
        ):
            runner.run_simulation("* test netlist\n.end")

        mock_run.assert_called_once()
        args = mock_run.call_args
        cmd_list = args[0][0]
        assert cmd_list[0] == "/usr/bin/ngspice"
        assert "-b" in cmd_list
        assert "-o" in cmd_list
        assert args[1]["capture_output"] is True
        assert args[1]["text"] is True
        assert args[1]["timeout"] == 60  # SIMULATION_TIMEOUT


# ---------------------------------------------------------------------------
# read_output
# ---------------------------------------------------------------------------


class TestReadOutput:
    def test_reads_existing_file(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        out_file = tmp_path / "result.txt"
        out_file.write_text("simulation results here")

        result = runner.read_output(str(out_file))
        assert result == "simulation results here"

    def test_missing_file(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        result = runner.read_output(str(tmp_path / "nonexistent.txt"))
        assert "Error reading output" in result
