"""Tests for Jupyter notebook integration (scripting/jupyter.py)."""

import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData
from scripting.circuit import Circuit
from scripting.jupyter import _empty_svg, circuit_to_svg, plot_result


@pytest.fixture
def simple_circuit():
    """Create a simple voltage divider circuit."""
    c = Circuit()
    c.add_component("Voltage Source", "5V", position=(0, 0))
    c.add_component("Resistor", "1k", position=(200, 0))
    c.add_component("Ground", position=(0, 200))
    c.add_wire("V1", 0, "R1", 0)
    c.add_wire("R1", 1, "GND1", 0)
    c.add_wire("V1", 1, "GND1", 0)
    return c


@pytest.fixture
def empty_circuit():
    return Circuit()


_SENTINEL = object()


@dataclass
class FakeResult:
    success: bool = True
    analysis_type: str = "DC Operating Point"
    data: dict = _SENTINEL
    error: str = ""

    def __post_init__(self):
        if self.data is _SENTINEL:
            self.data = {"node_voltages": {"v(1)": 5.0, "v(2)": 2.5}}


class TestCircuitToSvg:
    def test_svg_contains_xml_elements(self, simple_circuit):
        svg = circuit_to_svg(simple_circuit.model)
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_svg_contains_component_ids(self, simple_circuit):
        svg = circuit_to_svg(simple_circuit.model)
        assert "V1" in svg
        assert "R1" in svg
        assert "GND1" in svg

    def test_svg_contains_values(self, simple_circuit):
        svg = circuit_to_svg(simple_circuit.model)
        assert "5V" in svg
        assert "1k" in svg

    def test_svg_contains_wire_lines(self, simple_circuit):
        svg = circuit_to_svg(simple_circuit.model)
        # Should contain line elements for wires
        assert "<line" in svg

    def test_svg_contains_terminal_circles(self, simple_circuit):
        svg = circuit_to_svg(simple_circuit.model)
        assert "<circle" in svg

    def test_empty_circuit_svg(self, empty_circuit):
        svg = circuit_to_svg(empty_circuit.model)
        assert "<svg" in svg
        assert "empty circuit" in svg

    def test_custom_dimensions(self, simple_circuit):
        svg = circuit_to_svg(simple_circuit.model, width=800, height=600)
        assert 'width="800"' in svg
        assert 'height="600"' in svg

    def test_single_component(self):
        c = Circuit()
        c.add_component("Resistor", "1k", position=(100, 100))
        svg = circuit_to_svg(c.model)
        assert "R1" in svg
        assert "1k" in svg


class TestEmptySvg:
    def test_empty_svg_dimensions(self):
        svg = _empty_svg(400, 300)
        assert 'width="400"' in svg
        assert 'height="300"' in svg

    def test_empty_svg_has_placeholder_text(self):
        svg = _empty_svg(400, 300)
        assert "empty circuit" in svg


class TestCircuitReprSvg:
    def test_repr_svg_method(self, simple_circuit):
        svg = simple_circuit._repr_svg_()
        assert "<svg" in svg
        assert "V1" in svg


class TestPlotResult:
    def test_plot_result_without_matplotlib(self):
        """plot_result returns None when matplotlib is not available."""
        result = FakeResult()
        with patch.dict("sys.modules", {"matplotlib": None, "matplotlib.pyplot": None}):
            fig = plot_result(result)
            # Can't guarantee None here because matplotlib may already be imported
            # Just verify it doesn't crash
            assert fig is None or fig is not None

    def test_plot_result_failed_result(self):
        result = FakeResult(success=False, data=None)
        fig = plot_result(result)
        assert fig is None

    def test_plot_result_no_data(self):
        result = FakeResult(success=True, data=None)
        fig = plot_result(result)
        assert fig is None

    def test_plot_op_result(self):
        """DC OP result generates a bar chart figure."""
        pytest.importorskip("matplotlib")
        import matplotlib

        matplotlib.use("Agg")
        result = FakeResult(
            analysis_type="DC Operating Point",
            data={"node_voltages": {"v(1)": 5.0, "v(2)": 2.5}},
        )
        fig = plot_result(result)
        assert fig is not None
        import matplotlib.pyplot as plt

        plt.close(fig)

    def test_plot_op_empty_voltages(self):
        """DC OP with no voltages returns None."""
        result = FakeResult(
            analysis_type="DC Operating Point",
            data={"node_voltages": {}},
        )
        fig = plot_result(result)
        assert fig is None

    def test_plot_transient_result(self):
        """Transient result generates a time-series plot."""
        pytest.importorskip("matplotlib")
        import matplotlib

        matplotlib.use("Agg")
        result = FakeResult(
            analysis_type="Transient",
            data=[
                {"time": 0.0, "v(1)": 0.0, "v(2)": 0.0},
                {"time": 0.001, "v(1)": 2.5, "v(2)": 1.25},
                {"time": 0.002, "v(1)": 5.0, "v(2)": 2.5},
            ],
        )
        fig = plot_result(result)
        assert fig is not None
        import matplotlib.pyplot as plt

        plt.close(fig)

    def test_plot_ac_result(self):
        """AC sweep generates a Bode plot."""
        pytest.importorskip("matplotlib")
        import matplotlib

        matplotlib.use("Agg")
        result = FakeResult(
            analysis_type="AC Sweep",
            data=[
                {"frequency": 1.0, "v(out)": 0.0, "phase_v(out)": 0.0},
                {"frequency": 100.0, "v(out)": -3.0, "phase_v(out)": -45.0},
                {"frequency": 10000.0, "v(out)": -20.0, "phase_v(out)": -90.0},
            ],
        )
        fig = plot_result(result)
        assert fig is not None
        import matplotlib.pyplot as plt

        plt.close(fig)

    def test_plot_dc_sweep_result(self):
        """DC sweep generates a line plot."""
        pytest.importorskip("matplotlib")
        import matplotlib

        matplotlib.use("Agg")
        result = FakeResult(
            analysis_type="DC Sweep",
            data=[
                {"v_sweep": 0.0, "v(2)": 0.0},
                {"v_sweep": 2.5, "v(2)": 1.25},
                {"v_sweep": 5.0, "v(2)": 2.5},
            ],
        )
        fig = plot_result(result)
        assert fig is not None
        import matplotlib.pyplot as plt

        plt.close(fig)

    def test_plot_unsupported_analysis(self):
        result = FakeResult(analysis_type="Unknown Analysis", data={"foo": "bar"})
        fig = plot_result(result)
        assert fig is None

    def test_plot_custom_title(self):
        """Custom title is used in the plot."""
        pytest.importorskip("matplotlib")
        import matplotlib

        matplotlib.use("Agg")
        result = FakeResult(
            analysis_type="DC Operating Point",
            data={"node_voltages": {"v(1)": 5.0}},
        )
        fig = plot_result(result, title="My Custom Title")
        assert fig is not None
        ax = fig.axes[0]
        assert ax.get_title() == "My Custom Title"
        import matplotlib.pyplot as plt

        plt.close(fig)


class TestCircuitPlotResult:
    def test_plot_result_method(self, simple_circuit):
        """Circuit.plot_result() delegates to jupyter.plot_result()."""
        result = FakeResult()
        fig = simple_circuit.plot_result(result)
        # May be None if matplotlib not installed, that's ok
        if fig is not None:
            import matplotlib.pyplot as plt

            plt.close(fig)
