"""Tests for NgspiceRunner (#497, #502)."""

import os
import subprocess
from datetime import datetime
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
    """Tests for find_ngspice() — delegates to ngspice_config.resolve_ngspice_path."""

    def test_found_sets_cmd(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        with patch("simulation.ngspice_runner.resolve_ngspice_path", return_value="/usr/bin/ngspice"):
            result = runner.find_ngspice()
        assert result == "/usr/bin/ngspice"
        assert runner.ngspice_cmd == "/usr/bin/ngspice"

    def test_not_found_returns_none(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        with patch("simulation.ngspice_runner.resolve_ngspice_path", return_value=None):
            result = runner.find_ngspice()
        assert result is None
        assert runner.ngspice_cmd is None


class TestRunSimulation:
    """Tests for run_simulation()."""

    def test_ngspice_not_found(self, tmp_path):
        runner = NgspiceRunner(output_dir=str(tmp_path))
        with patch("simulation.ngspice_runner.resolve_ngspice_path", return_value=None):
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

    def test_nonzero_exit_code_with_output_returns_failure(self, tmp_path):
        """Non-zero exit code must be treated as failure even when output exists (#508)."""
        runner = NgspiceRunner(output_dir=str(tmp_path))
        runner.ngspice_cmd = "/usr/bin/ngspice"

        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = "Error: some ngspice error"
        mock_result.returncode = 1

        def fake_run(cmd, **kwargs):
            output_path = cmd[4]
            with open(output_path, "w") as f:
                f.write("partial output before error\n")
            return mock_result

        with patch("simulation.ngspice_runner.subprocess.run", side_effect=fake_run):
            success, output_file, stdout, stderr = runner.run_simulation("test netlist")

        assert success is False
        assert output_file is not None  # output preserved for diagnosis
        assert "Error" in stderr

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


# ── Temp-file cleanup (issue #780) ───────────────────────────────────


def _fake_run_writing_output(output_content="results\n"):
    """Return a fake subprocess.run side_effect that writes to the output file."""

    def _inner(cmd, **kwargs):
        output_path = cmd[4]
        with open(output_path, "w") as f:
            f.write(output_content)
        m = MagicMock()
        m.stdout = ""
        m.stderr = ""
        m.returncode = 0
        return m

    return _inner


class TestTempFileCleanup:
    """Verify that successive runs do not accumulate stale temp files (#780)."""

    def test_second_run_removes_first_run_files(self, tmp_path):
        """Files from run 1 must be deleted before run 2 starts."""
        runner = NgspiceRunner(output_dir=str(tmp_path))
        runner.ngspice_cmd = "/fake/ngspice"

        # Mock datetime so each call returns a unique timestamp, ensuring
        # run 1 and run 2 produce differently-named files.
        ts1 = datetime(2024, 1, 1, 0, 0, 1)
        ts2 = datetime(2024, 1, 1, 0, 0, 2)

        with patch("simulation.ngspice_runner.datetime") as mock_dt:
            mock_dt.now.return_value = ts1
            with patch("simulation.ngspice_runner.subprocess.run", side_effect=_fake_run_writing_output()):
                runner.run_simulation("netlist 1")

        # After run 1, files still exist (accessible for result reading).
        first_run_files = {f.name for f in tmp_path.iterdir()}
        assert any("netlist_" in n for n in first_run_files)

        with patch("simulation.ngspice_runner.datetime") as mock_dt:
            mock_dt.now.return_value = ts2
            with patch("simulation.ngspice_runner.subprocess.run", side_effect=_fake_run_writing_output()):
                runner.run_simulation("netlist 2")

        # Run-1 files must be gone; only run-2 files remain.
        remaining = {f.name for f in tmp_path.iterdir()}
        for name in first_run_files:
            assert name not in remaining, f"Stale file from run 1 still present: {name}"

    def test_keep_files_env_var_prevents_cleanup(self, tmp_path, monkeypatch):
        """SPICE_KEEP_SIM_OUTPUT=1 must suppress all file deletion."""
        monkeypatch.setenv("SPICE_KEEP_SIM_OUTPUT", "1")
        runner = NgspiceRunner(output_dir=str(tmp_path))
        runner.ngspice_cmd = "/fake/ngspice"

        ts1 = datetime(2024, 1, 1, 0, 0, 1)
        ts2 = datetime(2024, 1, 1, 0, 0, 2)

        with patch("simulation.ngspice_runner.datetime") as mock_dt:
            mock_dt.now.return_value = ts1
            with patch("simulation.ngspice_runner.subprocess.run", side_effect=_fake_run_writing_output()):
                runner.run_simulation("netlist 1")

        first_run_files = {f.name for f in tmp_path.iterdir()}

        with patch("simulation.ngspice_runner.datetime") as mock_dt:
            mock_dt.now.return_value = ts2
            with patch("simulation.ngspice_runner.subprocess.run", side_effect=_fake_run_writing_output()):
                runner.run_simulation("netlist 2")

        # All files from run 1 must still be present (no cleanup).
        remaining = {f.name for f in tmp_path.iterdir()}
        for name in first_run_files:
            assert name in remaining, f"File was deleted despite SPICE_KEEP_SIM_OUTPUT=1: {name}"

    def test_single_run_files_persist_for_result_reading(self, tmp_path):
        """Files from the current run must still exist after run_simulation returns."""
        runner = NgspiceRunner(output_dir=str(tmp_path))
        runner.ngspice_cmd = "/fake/ngspice"

        with patch("simulation.ngspice_runner.subprocess.run", side_effect=_fake_run_writing_output()):
            success, output_file, _, _ = runner.run_simulation("netlist")

        assert success is True
        assert output_file is not None
        assert os.path.exists(output_file), "Output file must exist after run for result reading"

    def test_failed_run_netlist_cleaned_on_next_run(self, tmp_path):
        """Even when the run fails (no output), the netlist is cleaned up on the next run."""
        runner = NgspiceRunner(output_dir=str(tmp_path))
        runner.ngspice_cmd = "/fake/ngspice"

        ts1 = datetime(2024, 1, 1, 0, 0, 1)
        ts2 = datetime(2024, 1, 1, 0, 0, 2)

        # First run produces no output file → failure
        noop_result = MagicMock()
        noop_result.stdout = ""
        noop_result.stderr = "error"
        noop_result.returncode = 1
        with patch("simulation.ngspice_runner.datetime") as mock_dt:
            mock_dt.now.return_value = ts1
            with patch("simulation.ngspice_runner.subprocess.run", return_value=noop_result):
                success, _, _, _ = runner.run_simulation("bad netlist")
        assert success is False

        files_after_fail = {f.name for f in tmp_path.iterdir()}
        assert any("netlist_" in n for n in files_after_fail), "Netlist file should exist after failed run"

        # Second run should clean up the netlist from the failed run.
        with patch("simulation.ngspice_runner.datetime") as mock_dt:
            mock_dt.now.return_value = ts2
            with patch("simulation.ngspice_runner.subprocess.run", side_effect=_fake_run_writing_output()):
                runner.run_simulation("good netlist")

        remaining = {f.name for f in tmp_path.iterdir()}
        # The failed run's netlist must be gone.
        for name in files_after_fail:
            assert name not in remaining, f"Stale netlist from failed run still present: {name}"
