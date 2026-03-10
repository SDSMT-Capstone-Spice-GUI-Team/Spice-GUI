"""Tests for report data assembly (pure Python, no Qt)."""

import pytest
from models.circuit import CircuitModel
from models.component import ComponentData
from services.report_generator import ReportConfig, ReportData, ReportDataBuilder

# --- Fixtures ---


@pytest.fixture
def simple_model():
    """A simple circuit model with a few components."""
    model = CircuitModel()
    model.components = {
        "R1": ComponentData("R1", "Resistor", "1k", (100, 100)),
        "V1": ComponentData("V1", "Voltage Source", "5", (0, 100)),
    }
    model.analysis_type = "DC Operating Point"
    model.analysis_params = {}
    return model


@pytest.fixture
def configured_model():
    """A model with analysis params and multiple component types."""
    model = CircuitModel()
    model.components = {
        "R1": ComponentData("R1", "Resistor", "1k", (100, 100)),
        "R2": ComponentData("R2", "Resistor", "2k", (200, 100)),
        "C1": ComponentData("C1", "Capacitor", "1u", (100, 200)),
        "V1": ComponentData("V1", "Voltage Source", "5", (0, 100)),
    }
    model.analysis_type = "AC Sweep"
    model.analysis_params = {
        "sweep_type": "dec",
        "num_points": "100",
        "fStart": "1",
        "fStop": "100k",
    }
    return model


# --- ReportConfig tests ---


class TestReportConfig:
    def test_default_config(self):
        config = ReportConfig()
        assert config.include_title is True
        assert config.include_schematic is True
        assert config.include_netlist is True
        assert config.include_analysis is True
        assert config.include_results is True
        assert config.student_name == ""
        assert config.circuit_name == ""

    def test_custom_config(self):
        config = ReportConfig(
            include_schematic=False,
            student_name="Alice",
            circuit_name="RC Filter",
        )
        assert config.include_schematic is False
        assert config.student_name == "Alice"
        assert config.circuit_name == "RC Filter"


# --- ReportData tests ---


class TestReportData:
    def test_default_data(self):
        data = ReportData()
        assert data.title == ""
        assert data.subtitle == "Circuit Analysis Report"
        assert data.component_count == 0
        assert data.netlist == ""

    def test_data_with_config(self):
        config = ReportConfig(circuit_name="My Circuit", student_name="Bob")
        data = ReportData(config=config, title="My Circuit")
        assert data.config.circuit_name == "My Circuit"
        assert data.title == "My Circuit"


# --- ReportDataBuilder tests ---


class TestReportDataBuilder:
    def test_build_minimal(self):
        config = ReportConfig()
        data = ReportDataBuilder.build(config)
        assert data.title == "Circuit Report"
        assert data.date_str != ""
        assert data.component_count == 0

    def test_build_with_model(self, simple_model):
        config = ReportConfig(circuit_name="Test Circuit")
        data = ReportDataBuilder.build(config, model=simple_model)
        assert data.title == "Test Circuit"
        assert data.analysis_type == "DC Operating Point"
        assert data.component_count == 2
        assert "DC Operating Point" in data.analysis_text

    def test_build_with_netlist_and_results(self):
        config = ReportConfig()
        data = ReportDataBuilder.build(config, netlist="R1 1 0 1k", results_text="V(1) = 5V")
        assert data.netlist == "R1 1 0 1k"
        assert data.results_text == "V(1) = 5V"

    def test_build_without_model(self):
        config = ReportConfig(circuit_name="No Model")
        data = ReportDataBuilder.build(config)
        assert data.title == "No Model"
        assert data.analysis_type == ""
        assert data.analysis_text == ""


# --- _format_analysis_config tests ---


class TestFormatAnalysisConfig:
    """Test the analysis config formatting helper."""

    def test_format_op_analysis(self, simple_model):
        text = ReportDataBuilder._format_analysis_config(simple_model)
        assert "DC Operating Point" in text
        assert "Total Components: 2" in text

    def test_format_ac_analysis(self, configured_model):
        text = ReportDataBuilder._format_analysis_config(configured_model)
        assert "AC Sweep" in text
        assert "Sweep Type" in text
        assert "100" in text
        assert "Total Components: 4" in text

    def test_format_component_summary(self, configured_model):
        text = ReportDataBuilder._format_analysis_config(configured_model)
        assert "Resistor: 2" in text
        assert "Capacitor: 1" in text
        assert "Voltage Source: 1" in text

    def test_format_empty_params(self, simple_model):
        text = ReportDataBuilder._format_analysis_config(simple_model)
        assert "(default)" in text
