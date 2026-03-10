"""Tests for rubric auto-generation from reference circuits."""

import pytest
from grading.rubric import validate_rubric
from grading.rubric_generator import generate_rubric_from_circuit
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData

# --- Helpers ---


def _build_rc_filter():
    """Build a V1-R1-C1-GND RC low-pass filter with AC Sweep analysis."""
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
        value="1k",
        position=(100.0, 0.0),
    )
    model.components["C1"] = ComponentData(
        component_id="C1",
        component_type="Capacitor",
        value="100n",
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
    model.rebuild_nodes()
    return model


def _build_simple_resistor():
    """Build a minimal circuit: single resistor, no wires, default analysis."""
    model = CircuitModel()
    model.components["R1"] = ComponentData(
        component_id="R1",
        component_type="Resistor",
        value="10k",
        position=(0.0, 0.0),
    )
    model.rebuild_nodes()
    return model


# --- Tests ---


class TestGenerateRubricFromCircuit:
    """Tests for the core generate_rubric_from_circuit() function."""

    def test_returns_rubric_with_correct_title(self):
        model = _build_rc_filter()
        rubric = generate_rubric_from_circuit(model, title="My Rubric")
        assert rubric.title == "My Rubric"

    def test_returns_rubric_with_correct_total_points(self):
        model = _build_rc_filter()
        rubric = generate_rubric_from_circuit(model, total_points=200)
        assert rubric.total_points == 200

    def test_points_sum_equals_total(self):
        model = _build_rc_filter()
        rubric = generate_rubric_from_circuit(model)
        actual_sum = sum(c.points for c in rubric.checks)
        assert actual_sum == rubric.total_points

    def test_points_sum_equals_total_odd_distribution(self):
        """Ensure remainder points are distributed correctly."""
        model = _build_rc_filter()
        rubric = generate_rubric_from_circuit(model, total_points=97)
        actual_sum = sum(c.points for c in rubric.checks)
        assert actual_sum == 97

    def test_generated_rubric_passes_validation(self):
        """The generated rubric must pass validate_rubric()."""
        model = _build_rc_filter()
        rubric = generate_rubric_from_circuit(model)
        # Should not raise
        validate_rubric(rubric.to_dict())

    def test_default_title_and_points(self):
        model = _build_simple_resistor()
        rubric = generate_rubric_from_circuit(model)
        assert rubric.title == "Auto-Generated Rubric"
        assert rubric.total_points == 100


class TestComponentExistsChecks:
    """Tests for component_exists check generation."""

    def test_generates_exists_for_non_ground_components(self):
        model = _build_rc_filter()
        rubric = generate_rubric_from_circuit(model)
        exists_checks = [c for c in rubric.checks if c.check_type == "component_exists"]
        exists_ids = {c.params["component_id"] for c in exists_checks}
        assert "V1" in exists_ids
        assert "R1" in exists_ids
        assert "C1" in exists_ids

    def test_skips_ground_components(self):
        model = _build_rc_filter()
        rubric = generate_rubric_from_circuit(model)
        exists_checks = [c for c in rubric.checks if c.check_type == "component_exists"]
        exists_ids = {c.params["component_id"] for c in exists_checks}
        assert "GND1" not in exists_ids

    def test_includes_component_type_in_params(self):
        model = _build_rc_filter()
        rubric = generate_rubric_from_circuit(model)
        r1_check = next(c for c in rubric.checks if c.check_id == "exists_R1")
        assert r1_check.params["component_type"] == "Resistor"

    def test_feedback_text_is_populated(self):
        model = _build_rc_filter()
        rubric = generate_rubric_from_circuit(model)
        r1_check = next(c for c in rubric.checks if c.check_id == "exists_R1")
        assert "R1" in r1_check.feedback_pass
        assert "R1" in r1_check.feedback_fail
        assert "Resistor" in r1_check.feedback_pass

    def test_check_ids_are_unique(self):
        model = _build_rc_filter()
        rubric = generate_rubric_from_circuit(model)
        ids = [c.check_id for c in rubric.checks]
        assert len(ids) == len(set(ids))


class TestComponentValueChecks:
    """Tests for component_value check generation."""

    def test_generates_value_checks_for_value_types(self):
        model = _build_rc_filter()
        rubric = generate_rubric_from_circuit(model)
        value_checks = [c for c in rubric.checks if c.check_type == "component_value"]
        value_ids = {c.params["component_id"] for c in value_checks}
        assert "R1" in value_ids
        assert "C1" in value_ids
        assert "V1" in value_ids

    def test_skips_value_for_ground(self):
        model = _build_rc_filter()
        rubric = generate_rubric_from_circuit(model)
        value_checks = [c for c in rubric.checks if c.check_type == "component_value"]
        value_ids = {c.params["component_id"] for c in value_checks}
        assert "GND1" not in value_ids

    def test_skips_value_for_non_value_types(self):
        """Op-Amp, BJT, MOSFET, Ground, Diode, etc. should not get value checks."""
        model = CircuitModel()
        model.components["OA1"] = ComponentData(
            component_id="OA1",
            component_type="Op-Amp",
            value="Ideal",
            position=(0.0, 0.0),
        )
        model.components["D1"] = ComponentData(
            component_id="D1",
            component_type="Diode",
            value="IS=1e-14 N=1",
            position=(100.0, 0.0),
        )
        model.rebuild_nodes()
        rubric = generate_rubric_from_circuit(model)
        value_checks = [c for c in rubric.checks if c.check_type == "component_value"]
        assert len(value_checks) == 0

    def test_expected_value_matches_component(self):
        model = _build_rc_filter()
        rubric = generate_rubric_from_circuit(model)
        r1_val = next(c for c in rubric.checks if c.check_id == "value_R1")
        assert r1_val.params["expected_value"] == "1k"

    def test_default_tolerance(self):
        model = _build_rc_filter()
        rubric = generate_rubric_from_circuit(model)
        r1_val = next(c for c in rubric.checks if c.check_id == "value_R1")
        assert r1_val.params["tolerance_pct"] == 5.0


class TestTopologyChecks:
    """Tests for topology check generation."""

    def test_generates_topology_for_wire_connections(self):
        model = _build_rc_filter()
        rubric = generate_rubric_from_circuit(model)
        topo_checks = [c for c in rubric.checks if c.check_type == "topology"]
        # RC filter has 4 wires connecting: V1-R1, R1-C1, C1-GND1, V1-GND1
        assert len(topo_checks) == 4

    def test_topology_params_have_component_pair(self):
        model = _build_rc_filter()
        rubric = generate_rubric_from_circuit(model)
        topo_checks = [c for c in rubric.checks if c.check_type == "topology"]
        for tc in topo_checks:
            assert "component_a" in tc.params
            assert "component_b" in tc.params
            assert tc.params["shared_node"] is True

    def test_deduplicates_wire_pairs(self):
        """Multiple wires between the same pair should produce only one check."""
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
        model.wires = [
            WireData(
                start_component_id="R1",
                start_terminal=0,
                end_component_id="R2",
                end_terminal=0,
            ),
            WireData(
                start_component_id="R2",
                start_terminal=1,
                end_component_id="R1",
                end_terminal=1,
            ),
        ]
        model.rebuild_nodes()
        rubric = generate_rubric_from_circuit(model)
        topo_checks = [c for c in rubric.checks if c.check_type == "topology"]
        assert len(topo_checks) == 1

    def test_no_topology_when_no_wires(self):
        model = _build_simple_resistor()
        rubric = generate_rubric_from_circuit(model)
        topo_checks = [c for c in rubric.checks if c.check_type == "topology"]
        assert len(topo_checks) == 0


class TestGroundCheck:
    """Tests for ground check generation."""

    def test_generates_ground_check_when_ground_exists(self):
        model = _build_rc_filter()
        rubric = generate_rubric_from_circuit(model)
        ground_checks = [c for c in rubric.checks if c.check_type == "ground"]
        assert len(ground_checks) == 1
        assert ground_checks[0].check_id == "ground_exists"

    def test_no_ground_check_when_no_ground(self):
        model = _build_simple_resistor()
        rubric = generate_rubric_from_circuit(model)
        ground_checks = [c for c in rubric.checks if c.check_type == "ground"]
        assert len(ground_checks) == 0


class TestAnalysisTypeCheck:
    """Tests for analysis_type check generation."""

    def test_generates_analysis_check_for_non_default(self):
        model = _build_rc_filter()  # AC Sweep
        rubric = generate_rubric_from_circuit(model)
        analysis_checks = [c for c in rubric.checks if c.check_type == "analysis_type"]
        assert len(analysis_checks) == 1
        assert analysis_checks[0].params["expected_type"] == "AC Sweep"

    def test_no_analysis_check_for_default(self):
        """DC Operating Point is the default — no check should be generated."""
        model = _build_simple_resistor()
        assert model.analysis_type == "DC Operating Point"
        rubric = generate_rubric_from_circuit(model)
        analysis_checks = [c for c in rubric.checks if c.check_type == "analysis_type"]
        assert len(analysis_checks) == 0


class TestEmptyCircuit:
    """Edge case: empty circuit."""

    def test_empty_circuit_produces_empty_checks(self):
        model = CircuitModel()
        rubric = generate_rubric_from_circuit(model)
        assert len(rubric.checks) == 0
        assert rubric.total_points == 100

    def test_empty_circuit_rubric_title(self):
        model = CircuitModel()
        rubric = generate_rubric_from_circuit(model)
        assert rubric.title == "Auto-Generated Rubric"


class TestPointDistribution:
    """Tests for the equal point distribution logic."""

    def test_equal_distribution_divides_evenly(self):
        """With 10 checks and 100 points, each should get 10."""
        model = CircuitModel()
        for i in range(10):
            cid = f"R{i + 1}"
            model.components[cid] = ComponentData(
                component_id=cid,
                component_type="Resistor",
                value="1k",
                position=(float(i * 100), 0.0),
            )
        model.rebuild_nodes()
        rubric = generate_rubric_from_circuit(model, total_points=100)
        # 10 resistors -> 10 exists + 10 value = 20 checks
        points = [c.points for c in rubric.checks]
        assert sum(points) == 100
        assert all(p == 5 for p in points)

    def test_remainder_distributed_to_first_checks(self):
        model = CircuitModel()
        model.components["R1"] = ComponentData(
            component_id="R1",
            component_type="Resistor",
            value="1k",
            position=(0.0, 0.0),
        )
        model.rebuild_nodes()
        # 2 checks (exists + value), 7 points -> 3 + 4, remainder 1 to first
        rubric = generate_rubric_from_circuit(model, total_points=7)
        assert len(rubric.checks) == 2
        assert rubric.checks[0].points == 4  # gets remainder
        assert rubric.checks[1].points == 3
        assert sum(c.points for c in rubric.checks) == 7


class TestControlledSourceValueChecks:
    """Controlled sources (VCVS, CCVS, VCCS, CCCS) should get value checks."""

    def test_vcvs_gets_value_check(self):
        model = CircuitModel()
        model.components["E1"] = ComponentData(
            component_id="E1",
            component_type="VCVS",
            value="10",
            position=(0.0, 0.0),
        )
        model.rebuild_nodes()
        rubric = generate_rubric_from_circuit(model)
        value_checks = [c for c in rubric.checks if c.check_type == "component_value"]
        assert len(value_checks) == 1
        assert value_checks[0].params["component_id"] == "E1"
        assert value_checks[0].params["expected_value"] == "10"
