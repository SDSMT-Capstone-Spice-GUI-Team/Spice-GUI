"""Tests for rubric auto-generation from a reference circuit."""

import pytest
from grading.rubric import VALID_CHECK_TYPES
from grading.rubric_generator import generate_rubric
from models.circuit import CircuitModel

from ..conftest import make_component, make_wire


def _build_model(components, wires):
    """Build a CircuitModel from component and wire lists."""
    model = CircuitModel()
    for comp in components:
        model.add_component(comp)
    for wire in wires:
        model.add_wire(wire)
    return model


class TestGenerateRubric:
    """Tests for the generate_rubric function."""

    def test_empty_circuit_returns_empty_rubric(self):
        """An empty circuit produces a rubric with no checks."""
        model = CircuitModel()
        rubric = generate_rubric(model)
        assert rubric.title == "Auto-Generated Rubric"
        assert rubric.total_points == 0
        assert rubric.checks == []

    def test_custom_title(self):
        """Custom title is used in the generated rubric."""
        model = CircuitModel()
        rubric = generate_rubric(model, title="My Assignment")
        assert rubric.title == "My Assignment"

    def test_component_exists_checks(self):
        """Each non-ground component gets an existence check."""
        model = _build_model(
            [
                make_component("Resistor", "R1", "1k"),
                make_component("Capacitor", "C1", "1u"),
                make_component("Ground", "GND1", "0V"),
            ],
            [],
        )
        rubric = generate_rubric(model)
        exists_checks = [c for c in rubric.checks if c.check_type == "component_exists"]
        assert len(exists_checks) == 2
        ids = {c.params["component_id"] for c in exists_checks}
        assert ids == {"R1", "C1"}

    def test_ground_not_in_exists_checks(self):
        """Ground components are excluded from existence checks."""
        model = _build_model(
            [make_component("Ground", "GND1", "0V")],
            [],
        )
        rubric = generate_rubric(model)
        exists_checks = [c for c in rubric.checks if c.check_type == "component_exists"]
        assert len(exists_checks) == 0

    def test_component_value_checks_for_non_default(self):
        """Value checks are generated for components with non-default values."""
        model = _build_model(
            [
                make_component("Resistor", "R1", "10k"),  # default is 1k
                make_component("Resistor", "R2", "1k"),  # matches default
            ],
            [],
        )
        rubric = generate_rubric(model)
        value_checks = [c for c in rubric.checks if c.check_type == "component_value"]
        assert len(value_checks) == 1
        assert value_checks[0].params["component_id"] == "R1"
        assert value_checks[0].params["expected_value"] == "10k"
        assert value_checks[0].params["tolerance_pct"] == 5.0

    def test_topology_checks_for_wires(self):
        """Topology checks are generated for wire connections between non-ground components."""
        r1 = make_component("Resistor", "R1", "1k")
        r2 = make_component("Resistor", "R2", "1k")
        model = _build_model(
            [r1, r2],
            [make_wire("R1", 1, "R2", 0)],
        )
        rubric = generate_rubric(model)
        topo_checks = [c for c in rubric.checks if c.check_type == "topology"]
        assert len(topo_checks) == 1
        params = topo_checks[0].params
        assert set([params["component_a"], params["component_b"]]) == {"R1", "R2"}
        assert params["shared_node"] is True

    def test_no_duplicate_topology_checks(self):
        """Multiple wires between the same pair of components produce only one topology check."""
        r1 = make_component("Resistor", "R1", "1k")
        r2 = make_component("Resistor", "R2", "1k")
        model = _build_model(
            [r1, r2],
            [
                make_wire("R1", 0, "R2", 0),
                make_wire("R1", 1, "R2", 1),
            ],
        )
        rubric = generate_rubric(model)
        topo_checks = [c for c in rubric.checks if c.check_type == "topology"]
        assert len(topo_checks) == 1

    def test_topology_excludes_ground_wires(self):
        """Wires to ground components don't generate topology checks."""
        r1 = make_component("Resistor", "R1", "1k")
        gnd = make_component("Ground", "GND1", "0V")
        model = _build_model(
            [r1, gnd],
            [make_wire("R1", 1, "GND1", 0)],
        )
        rubric = generate_rubric(model)
        topo_checks = [c for c in rubric.checks if c.check_type == "topology"]
        assert len(topo_checks) == 0

    def test_ground_check_present(self):
        """A ground check is generated when the circuit has a ground component."""
        model = _build_model(
            [make_component("Ground", "GND1", "0V")],
            [],
        )
        rubric = generate_rubric(model)
        ground_checks = [c for c in rubric.checks if c.check_type == "ground"]
        assert len(ground_checks) == 1

    def test_no_ground_check_without_ground(self):
        """No ground check when the circuit has no ground component."""
        model = _build_model(
            [make_component("Resistor", "R1", "1k")],
            [],
        )
        rubric = generate_rubric(model)
        ground_checks = [c for c in rubric.checks if c.check_type == "ground"]
        assert len(ground_checks) == 0

    def test_analysis_type_check_non_default(self):
        """Analysis type check generated for non-default analysis."""
        model = CircuitModel()
        model.add_component(make_component("Resistor", "R1", "1k"))
        model.analysis_type = "AC Sweep"
        rubric = generate_rubric(model)
        at_checks = [c for c in rubric.checks if c.check_type == "analysis_type"]
        assert len(at_checks) == 1
        assert at_checks[0].params["expected_type"] == "AC Sweep"

    def test_no_analysis_type_check_for_default(self):
        """No analysis type check when using default DC Operating Point."""
        model = CircuitModel()
        model.add_component(make_component("Resistor", "R1", "1k"))
        rubric = generate_rubric(model)
        at_checks = [c for c in rubric.checks if c.check_type == "analysis_type"]
        assert len(at_checks) == 0

    def test_equal_point_distribution(self):
        """Points are distributed equally across all checks."""
        model = _build_model(
            [
                make_component("Resistor", "R1", "10k"),
                make_component("Resistor", "R2", "20k"),
                make_component("Ground", "GND1", "0V"),
            ],
            [make_wire("R1", 1, "R2", 0)],
        )
        rubric = generate_rubric(model)
        assert len(rubric.checks) > 0
        points = [c.points for c in rubric.checks]
        # All checks have the same points
        assert len(set(points)) == 1
        # Total points matches
        assert rubric.total_points == sum(points)

    def test_unique_check_ids(self):
        """All generated check IDs are unique."""
        model = _build_model(
            [
                make_component("Resistor", "R1", "10k"),
                make_component("Resistor", "R2", "20k"),
                make_component("Voltage Source", "V1", "12V"),
                make_component("Ground", "GND1", "0V"),
            ],
            [
                make_wire("V1", 0, "R1", 0),
                make_wire("R1", 1, "R2", 0),
                make_wire("R2", 1, "GND1", 0),
                make_wire("V1", 1, "GND1", 0),
            ],
        )
        rubric = generate_rubric(model)
        ids = [c.check_id for c in rubric.checks]
        assert len(ids) == len(set(ids))

    def test_all_check_types_valid(self):
        """All generated checks use valid check types."""
        model = _build_model(
            [
                make_component("Resistor", "R1", "10k"),
                make_component("Ground", "GND1", "0V"),
            ],
            [make_wire("R1", 1, "GND1", 0)],
        )
        model.analysis_type = "Transient"
        rubric = generate_rubric(model)
        for check in rubric.checks:
            assert check.check_type in VALID_CHECK_TYPES

    def test_feedback_messages_populated(self):
        """Generated checks have non-empty feedback messages."""
        model = _build_model(
            [make_component("Resistor", "R1", "10k")],
            [],
        )
        rubric = generate_rubric(model)
        for check in rubric.checks:
            assert check.feedback_pass
            assert check.feedback_fail

    def test_full_circuit_rubric(self):
        """Integration test: voltage divider produces expected check types."""
        model = _build_model(
            [
                make_component("Voltage Source", "V1", "12V"),
                make_component("Resistor", "R1", "10k"),
                make_component("Resistor", "R2", "20k"),
                make_component("Ground", "GND1", "0V"),
            ],
            [
                make_wire("V1", 0, "R1", 0),
                make_wire("R1", 1, "R2", 0),
                make_wire("R2", 1, "GND1", 0),
                make_wire("V1", 1, "GND1", 0),
            ],
        )
        rubric = generate_rubric(model, title="Voltage Divider")
        assert rubric.title == "Voltage Divider"

        check_types = {c.check_type for c in rubric.checks}
        assert "component_exists" in check_types
        assert "component_value" in check_types
        assert "topology" in check_types
        assert "ground" in check_types

        # 3 exists (V1, R1, R2) + 3 values (all non-default) + 2 topology + 1 ground = 9
        exists_count = sum(1 for c in rubric.checks if c.check_type == "component_exists")
        value_count = sum(1 for c in rubric.checks if c.check_type == "component_value")
        topo_count = sum(1 for c in rubric.checks if c.check_type == "topology")
        ground_count = sum(1 for c in rubric.checks if c.check_type == "ground")

        assert exists_count == 3
        assert value_count == 3
        assert topo_count == 2  # V1-R1, R1-R2 (ground wires excluded)
        assert ground_count == 1
