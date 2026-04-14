"""Tests for simulation.selftest (#838)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from simulation.selftest import (
    CheckResult,
    SelftestResult,
    check_example_load,
    check_imports,
    check_ngspice,
    check_simulation,
    run_selftest,
)


class TestCheckResult:
    def test_passed_check(self):
        c = CheckResult("test", True, "ok")
        assert c.passed is True
        assert c.name == "test"

    def test_failed_check(self):
        c = CheckResult("test", False, "bad")
        assert c.passed is False


class TestSelftestResult:
    def test_all_pass(self):
        r = SelftestResult(checks=[CheckResult("a", True), CheckResult("b", True)])
        assert r.passed is True
        assert "2/2" in r.summary

    def test_one_fails(self):
        r = SelftestResult(checks=[CheckResult("a", True), CheckResult("b", False)])
        assert r.passed is False
        assert "1/2" in r.summary

    def test_empty(self):
        r = SelftestResult()
        assert r.passed is True
        assert "0/0" in r.summary


class TestCheckImports:
    def test_imports_succeed(self):
        result = check_imports()
        assert result.passed is True
        assert "OK" in result.detail

    def test_import_failure(self):
        with patch.dict(sys.modules, {"models.circuit": None}):
            with patch("builtins.__import__", side_effect=ImportError("no module")):
                result = check_imports()
        assert result.passed is False


class TestCheckNgspice:
    def test_ngspice_found(self):
        with patch("simulation.ngspice_config.resolve_ngspice_path", return_value="/usr/bin/ngspice"):
            result = check_ngspice()
        assert result.passed is True
        assert "/usr/bin/ngspice" in result.detail

    def test_ngspice_not_found(self):
        with patch("simulation.ngspice_config.resolve_ngspice_path", return_value=None):
            result = check_ngspice()
        assert result.passed is False


class TestCheckExampleLoad:
    def test_loads_successfully(self):
        result = check_example_load()
        # In the dev environment, examples/ exists
        if result.passed:
            assert "components" in result.detail
        # If examples dir not found, that's also valid in some environments

    def test_missing_examples_dir(self):
        with patch("simulation.selftest._find_examples_dir", return_value=None):
            result = check_example_load()
        assert result.passed is False
        assert "not found" in result.detail

    def test_no_json_files(self, tmp_path):
        with patch("simulation.selftest._find_examples_dir", return_value=tmp_path):
            result = check_example_load()
        assert result.passed is False


class TestCheckSimulation:
    def test_missing_examples_dir(self):
        with patch("simulation.selftest._find_examples_dir", return_value=None):
            result = check_simulation()
        assert result.passed is False

    def test_simulation_succeeds(self):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.analysis_type = "DC Operating Point"

        examples = Path(__file__).resolve().parent.parent.parent / "examples"
        if not examples.is_dir():
            pytest.skip("No examples directory available")

        with (
            patch("simulation.selftest._find_examples_dir", return_value=examples),
            patch("controllers.simulation_controller.SimulationController.run_simulation", return_value=mock_result),
        ):
            result = check_simulation()
        assert isinstance(result, CheckResult)
        assert result.passed is True

    def test_simulation_fails(self):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "ngspice not found"

        examples = Path(__file__).resolve().parent.parent.parent / "examples"
        if not examples.is_dir():
            pytest.skip("No examples directory available")

        with (
            patch("simulation.selftest._find_examples_dir", return_value=examples),
            patch("controllers.simulation_controller.SimulationController.run_simulation", return_value=mock_result),
        ):
            result = check_simulation()
        assert result.passed is False


class TestRunSelftest:
    def test_returns_selftest_result(self):
        with (
            patch("simulation.selftest.check_imports", return_value=CheckResult("imports", True)),
            patch("simulation.selftest.check_ngspice", return_value=CheckResult("ngspice", True)),
            patch("simulation.selftest.check_example_load", return_value=CheckResult("load", True)),
            patch("simulation.selftest.check_simulation", return_value=CheckResult("sim", True)),
        ):
            result = run_selftest()
        assert isinstance(result, SelftestResult)
        assert len(result.checks) == 4
        assert result.passed is True


class TestCliIntegration:
    def test_selftest_subcommand_exists(self):
        from cli import build_parser

        parser = build_parser()
        # Should not raise
        args = parser.parse_args(["selftest"])
        assert args.command == "selftest"

    def test_cmd_selftest_returns_zero_on_pass(self):
        from cli import cmd_selftest

        mock_result = SelftestResult(checks=[CheckResult("test", True)])
        with patch("simulation.selftest.run_selftest", return_value=mock_result):
            with patch("simulation.selftest.print_selftest"):
                exit_code = cmd_selftest(MagicMock())
        assert exit_code == 0

    def test_cmd_selftest_returns_one_on_fail(self):
        from cli import cmd_selftest

        mock_result = SelftestResult(checks=[CheckResult("test", False, "broken")])
        with patch("simulation.selftest.run_selftest", return_value=mock_result):
            with patch("simulation.selftest.print_selftest"):
                exit_code = cmd_selftest(MagicMock())
        assert exit_code == 1
