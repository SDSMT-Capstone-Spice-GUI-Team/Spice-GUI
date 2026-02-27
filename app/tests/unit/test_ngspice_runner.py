"""Tests for NgspiceRunner - empty output detection (#497)."""

import os
from unittest.mock import MagicMock, patch

import pytest
from simulation.ngspice_runner import NgspiceRunner


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
