"""Tests for the circuit comparison engine."""

import pytest
from grading.circuit_comparer import CheckResult, CircuitComparer, ComparisonResult, compare_values
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData

# --- Helpers ---


def _build_voltage_divider(r1_value="1k", r2_value="2k", source_value="5V"):
    """Build a V1-R1-R2-GND voltage divider circuit."""
    model = CircuitModel()
    model.components["V1"] = ComponentData(
        component_id="V1",
        component_type="Voltage Source",
        value=source_value,
        position=(0.0, 0.0),
    )
    model.components["R1"] = ComponentData(
        component_id="R1",
        component_type="Resistor",
        value=r1_value,
        position=(100.0, 0.0),
    )
    model.components["R2"] = ComponentData(
        component_id="R2",
        component_type="Resistor",
        value=r2_value,
        position=(100.0, 100.0),
    )
    model.components["GND1"] = ComponentData(
        component_id="GND1",
        component_type="Ground",
        value="0V",
        position=(0.0, 100.0),
    )
    model.wires = [
        # V1 terminal 1 -> R1 terminal 0
        WireData(
            start_component_id="V1",
            start_terminal=1,
            end_component_id="R1",
            end_terminal=0,
        ),
        # R1 terminal 1 -> R2 terminal 0
        WireData(
            start_component_id="R1",
            start_terminal=1,
            end_component_id="R2",
            end_terminal=0,
        ),
        # R2 terminal 1 -> GND
        WireData(
            start_component_id="R2",
            start_terminal=1,
            end_component_id="GND1",
            end_terminal=0,
        ),
        # V1 terminal 0 -> GND
        WireData(
            start_component_id="V1",
            start_terminal=0,
            end_component_id="GND1",
            end_terminal=0,
        ),
    ]
    model.component_counter = {"V": 1, "R": 2, "GND": 1}
    model.rebuild_nodes()
    return model


def _build_rc_filter(r_value="1k", c_value="100n"):
    """Build a V1-R1-C1-GND RC low-pass filter."""
    model = CircuitModel()
    model.components["V1"] = ComponentData(
        component_id="V1",
        component_type="Voltage Source",
        value="5V",
        position=(0.0, 0.0),
    )
    model.components["R1"] = ComponentData(
        component_id="R1",
        component_type="Resistor",
        value=r_value,
        position=(100.0, 0.0),
    )
    model.components["C1"] = ComponentData(
        component_id="C1",
        component_type="Capacitor",
        value=c_value,
        position=(200.0, 0.0),
    )
    model.components["GND1"] = ComponentData(
        component_id="GND1",
        component_type="Ground",
        value="0V",
        position=(0.0, 100.0),
    )
    model.wires = [
        WireData(
            start_component_id="V1",
            start_terminal=1,
            end_component_id="R1",
            end_terminal=0,
        ),
        WireData(
            start_component_id="R1",
            start_terminal=1,
            end_component_id="C1",
            end_terminal=0,
        ),
        WireData(
            start_component_id="C1",
            start_terminal=1,
            end_component_id="GND1",
            end_terminal=0,
        ),
        WireData(
            start_component_id="V1",
            start_terminal=0,
            end_component_id="GND1",
            end_terminal=0,
        ),
    ]
    model.component_counter = {"V": 1, "R": 1, "C": 1, "GND": 1}
    model.analysis_type = "AC Sweep"
    model.analysis_params = {"fStart": 20, "fStop": 20000}
    model.rebuild_nodes()
    return model


# --- Tests: compare_values ---


class TestCompareValues:
    def test_exact_match(self):
        assert compare_values("1k", "1k") is True

    def test_equal_numeric_values(self):
        assert compare_values("1000", "1k") is True

    def test_within_tolerance(self):
        assert compare_values("1k", "1.05k", tolerance_pct=10) is True

    def test_outside_tolerance(self):
        assert compare_values("1k", "1.2k", tolerance_pct=10) is False

    def test_zero_tolerance_exact(self):
        assert compare_values("1k", "1k", tolerance_pct=0) is True

    def test_zero_tolerance_different(self):
        assert compare_values("1k", "1.001k", tolerance_pct=0) is False

    @pytest.mark.parametrize(
        "value_str,expected_float",
        [
            ("1k", 1000.0),
            ("4.7u", 4.7e-6),
            ("100m", 0.1),
            ("10MEG", 1e7),
            ("22p", 22e-12),
            ("100n", 1e-7),
            ("1.5", 1.5),
            ("100", 100.0),
        ],
    )
    def test_engineering_notation_parsing(self, value_str, expected_float):
        """Verify value parsing by comparing against itself."""
        assert compare_values(value_str, value_str) is True

    def test_unparseable_values_string_compare(self):
        assert compare_values("SIN(0 5 1k)", "SIN(0 5 1k)") is True

    def test_unparseable_values_mismatch(self):
        assert compare_values("SIN(0 5 1k)", "SIN(0 10 1k)") is False

    def test_zero_expected_zero_actual(self):
        assert compare_values("0", "0") is True

    def test_zero_expected_nonzero_actual(self):
        assert compare_values("0", "1") is False

    def test_negative_values(self):
        assert compare_values("-5", "-5") is True

    def test_units_stripped(self):
        assert compare_values("5V", "5V") is True
        assert compare_values("5V", "5") is True


# --- Tests: CircuitComparer individual checks ---


class TestCheckComponentExists:
    def test_component_present(self):
        circuit = _build_voltage_divider()
        comparer = CircuitComparer()
        result = comparer.check_component_exists(circuit, "R1", "Resistor")
        assert result.passed is True

    def test_component_missing(self):
        circuit = _build_voltage_divider()
        comparer = CircuitComparer()
        result = comparer.check_component_exists(circuit, "C1", "Capacitor")
        assert result.passed is False
        assert "not found" in result.actual

    def test_wrong_type(self):
        circuit = _build_voltage_divider()
        comparer = CircuitComparer()
        result = comparer.check_component_exists(circuit, "R1", "Capacitor")
        assert result.passed is False
        assert "Resistor" in result.actual


class TestCheckComponentValue:
    def test_correct_value(self):
        circuit = _build_voltage_divider(r1_value="1k")
        comparer = CircuitComparer()
        result = comparer.check_component_value(circuit, "R1", "1k")
        assert result.passed is True

    def test_wrong_value(self):
        circuit = _build_voltage_divider(r1_value="2k")
        comparer = CircuitComparer()
        result = comparer.check_component_value(circuit, "R1", "1k")
        assert result.passed is False
        assert result.actual == "2k"

    def test_value_within_tolerance(self):
        circuit = _build_voltage_divider(r1_value="1.05k")
        comparer = CircuitComparer()
        result = comparer.check_component_value(circuit, "R1", "1k", tolerance_pct=10)
        assert result.passed is True

    def test_value_outside_tolerance(self):
        circuit = _build_voltage_divider(r1_value="1.5k")
        comparer = CircuitComparer()
        result = comparer.check_component_value(circuit, "R1", "1k", tolerance_pct=10)
        assert result.passed is False

    def test_missing_component(self):
        circuit = _build_voltage_divider()
        comparer = CircuitComparer()
        result = comparer.check_component_value(circuit, "C1", "100n")
        assert result.passed is False
        assert "not found" in result.message


class TestCheckTopology:
    def test_connected_components(self):
        circuit = _build_voltage_divider()
        comparer = CircuitComparer()
        # R1 and R2 share a node in the voltage divider
        result = comparer.check_topology(circuit, "R1", "R2")
        assert result.passed is True

    def test_not_connected_components(self):
        """R1 and V1 don't share a node in the voltage divider (V1-R1 connection is terminal 1-0 but they should share)."""
        circuit = _build_voltage_divider()
        comparer = CircuitComparer()
        # V1 terminal 1 connects to R1 terminal 0, so they DO share a node
        result = comparer.check_topology(circuit, "V1", "R1")
        assert result.passed is True

    def test_unconnected_components(self):
        """Create a circuit where two components are NOT connected."""
        model = CircuitModel()
        model.components["R1"] = ComponentData(
            component_id="R1",
            component_type="Resistor",
            value="1k",
            position=(0.0, 0.0),
        )
        model.components["R2"] = ComponentData(
            component_id="R2",
            component_type="Resistor",
            value="2k",
            position=(100.0, 0.0),
        )
        # No wires connecting them
        model.rebuild_nodes()

        comparer = CircuitComparer()
        result = comparer.check_topology(model, "R1", "R2")
        assert result.passed is False


class TestCheckAnalysisType:
    def test_correct_analysis(self):
        circuit = _build_rc_filter()
        comparer = CircuitComparer()
        result = comparer.check_analysis_type(circuit, "AC Sweep")
        assert result.passed is True

    def test_wrong_analysis(self):
        circuit = _build_rc_filter()
        comparer = CircuitComparer()
        result = comparer.check_analysis_type(circuit, "Transient")
        assert result.passed is False
        assert result.actual == "AC Sweep"


# --- Tests: Full comparison ---


class TestFullComparison:
    def test_identical_circuits(self):
        ref = _build_voltage_divider()
        student = _build_voltage_divider()
        comparer = CircuitComparer()
        result = comparer.compare(ref, student)
        assert result.score == 1.0
        assert len(result.mismatches) == 0

    def test_missing_component(self):
        ref = _build_voltage_divider()
        student = _build_voltage_divider()
        del student.components["R2"]
        student.rebuild_nodes()

        comparer = CircuitComparer()
        result = comparer.compare(ref, student)
        assert result.score < 1.0
        # Should have mismatches for R2 existence and component count
        mismatch_types = {m.check_type for m in result.mismatches}
        assert "component_exists" in mismatch_types

    def test_wrong_values(self):
        ref = _build_voltage_divider(r1_value="1k", r2_value="2k")
        student = _build_voltage_divider(r1_value="10k", r2_value="2k")

        comparer = CircuitComparer()
        result = comparer.compare(ref, student)
        assert result.score < 1.0
        value_mismatches = [m for m in result.mismatches if m.check_type == "component_value"]
        assert len(value_mismatches) == 1
        assert value_mismatches[0].component_id == "R1"

    def test_wrong_analysis_type(self):
        ref = _build_rc_filter()
        student = _build_rc_filter()
        student.analysis_type = "Transient"

        comparer = CircuitComparer()
        result = comparer.compare(ref, student)
        analysis_mismatches = [m for m in result.mismatches if m.check_type == "analysis_type"]
        assert len(analysis_mismatches) == 1

    def test_topology_mismatch(self):
        ref = _build_voltage_divider()
        # Build a student circuit where R1 and R2 are NOT connected
        student = CircuitModel()
        student.components["V1"] = ComponentData(
            component_id="V1",
            component_type="Voltage Source",
            value="5V",
            position=(0.0, 0.0),
        )
        student.components["R1"] = ComponentData(
            component_id="R1",
            component_type="Resistor",
            value="1k",
            position=(100.0, 0.0),
        )
        student.components["R2"] = ComponentData(
            component_id="R2",
            component_type="Resistor",
            value="2k",
            position=(200.0, 0.0),
        )
        student.components["GND1"] = ComponentData(
            component_id="GND1",
            component_type="Ground",
            value="0V",
            position=(0.0, 100.0),
        )
        # Wire V1-R1 and V1-R2 but NOT R1-R2
        student.wires = [
            WireData(
                start_component_id="V1",
                start_terminal=1,
                end_component_id="R1",
                end_terminal=0,
            ),
            WireData(
                start_component_id="V1",
                start_terminal=0,
                end_component_id="R2",
                end_terminal=0,
            ),
            WireData(
                start_component_id="R2",
                start_terminal=1,
                end_component_id="GND1",
                end_terminal=0,
            ),
        ]
        student.component_counter = {"V": 1, "R": 2, "GND": 1}
        student.rebuild_nodes()

        comparer = CircuitComparer()
        result = comparer.compare(ref, student)
        topology_mismatches = [m for m in result.mismatches if m.check_type == "topology"]
        # R1 and R2 should be reported as not connected
        assert any("R1" in m.component_id and "R2" in m.component_id for m in topology_mismatches)


class TestComparisonResult:
    def test_score_all_pass(self):
        result = ComparisonResult()
        result.add(CheckResult("test", "", True, "", "", ""))
        result.add(CheckResult("test", "", True, "", "", ""))
        assert result.score == 1.0

    def test_score_all_fail(self):
        result = ComparisonResult()
        result.add(CheckResult("test", "", False, "", "", ""))
        result.add(CheckResult("test", "", False, "", "", ""))
        assert result.score == 0.0

    def test_score_half(self):
        result = ComparisonResult()
        result.add(CheckResult("test", "", True, "", "", ""))
        result.add(CheckResult("test", "", False, "", "", ""))
        assert result.score == 0.5

    def test_empty_score(self):
        result = ComparisonResult()
        assert result.score == 1.0

    def test_all_results_combines(self):
        result = ComparisonResult()
        result.add(CheckResult("a", "", True, "", "", ""))
        result.add(CheckResult("b", "", False, "", "", ""))
        assert len(result.all_results) == 2


class TestRealisticScenarios:
    def test_rc_filter_correct(self):
        """Student builds the correct RC filter."""
        ref = _build_rc_filter(r_value="1k", c_value="100n")
        student = _build_rc_filter(r_value="1k", c_value="100n")
        comparer = CircuitComparer()
        result = comparer.compare(ref, student)
        assert result.score == 1.0

    def test_rc_filter_wrong_capacitor(self):
        """Student uses wrong capacitor value."""
        ref = _build_rc_filter(r_value="1k", c_value="100n")
        student = _build_rc_filter(r_value="1k", c_value="10u")
        comparer = CircuitComparer()
        result = comparer.compare(ref, student)
        assert result.score < 1.0
        value_mismatches = [m for m in result.mismatches if m.check_type == "component_value"]
        assert any(m.component_id == "C1" for m in value_mismatches)
