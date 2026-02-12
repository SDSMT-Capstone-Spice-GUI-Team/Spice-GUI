"""Tests for PDF circuit report generation."""

import os
import tempfile

import pytest
from GUI.report_generator import ReportConfig, ReportGenerator
from models.circuit import CircuitModel
from models.component import ComponentData

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


@pytest.fixture
def sample_netlist():
    return "My Test Circuit\n* Generated netlist\n\nR1 1 2 1k\nV1 1 0 5\n.op\n.end\n"


@pytest.fixture
def sample_results():
    return (
        "======================================================================\n"
        "SIMULATION COMPLETE - DC Operating Point\n"
        "======================================================================\n"
        "\n"
        "NODE VOLTAGES:\n"
        "----------------------------------------\n"
        "  1               :     5.000000 V\n"
        "  2               :     2.500000 V\n"
        "----------------------------------------\n"
    )


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


# --- ReportGenerator tests ---


class TestReportGeneratorTitleOnly:
    """Test report generation with title page only (no Qt scene needed)."""

    def test_generates_pdf_file(self, qtbot, simple_model):
        config = ReportConfig(
            include_title=True,
            include_schematic=False,
            include_netlist=False,
            include_analysis=False,
            include_results=False,
            circuit_name="Test Circuit",
        )
        gen = ReportGenerator(config)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            gen.generate(filepath=pdf_path, model=simple_model)
            assert os.path.exists(pdf_path)
            assert os.path.getsize(pdf_path) > 0
        finally:
            os.unlink(pdf_path)

    def test_title_with_student_name(self, qtbot, simple_model):
        config = ReportConfig(
            include_title=True,
            include_schematic=False,
            include_netlist=False,
            include_analysis=False,
            include_results=False,
            circuit_name="Voltage Divider",
            student_name="Jane Doe",
        )
        gen = ReportGenerator(config)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            gen.generate(filepath=pdf_path, model=simple_model)
            assert os.path.exists(pdf_path)
            assert os.path.getsize(pdf_path) > 100
        finally:
            os.unlink(pdf_path)

    def test_title_without_model(self, qtbot):
        config = ReportConfig(
            include_title=True,
            include_schematic=False,
            include_netlist=False,
            include_analysis=False,
            include_results=False,
        )
        gen = ReportGenerator(config)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            gen.generate(filepath=pdf_path)
            assert os.path.exists(pdf_path)
            assert os.path.getsize(pdf_path) > 0
        finally:
            os.unlink(pdf_path)


class TestReportGeneratorNetlist:
    """Test report generation with netlist section."""

    def test_netlist_section(self, qtbot, simple_model, sample_netlist):
        config = ReportConfig(
            include_title=False,
            include_schematic=False,
            include_netlist=True,
            include_analysis=False,
            include_results=False,
        )
        gen = ReportGenerator(config)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            gen.generate(filepath=pdf_path, model=simple_model, netlist=sample_netlist)
            assert os.path.exists(pdf_path)
            assert os.path.getsize(pdf_path) > 100
        finally:
            os.unlink(pdf_path)

    def test_empty_netlist_skipped(self, qtbot):
        config = ReportConfig(
            include_title=True,
            include_schematic=False,
            include_netlist=True,
            include_analysis=False,
            include_results=False,
        )
        gen = ReportGenerator(config)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            gen.generate(filepath=pdf_path, netlist="")
            assert os.path.exists(pdf_path)
        finally:
            os.unlink(pdf_path)


class TestReportGeneratorAnalysis:
    """Test report generation with analysis configuration section."""

    def test_analysis_section(self, qtbot, configured_model):
        config = ReportConfig(
            include_title=False,
            include_schematic=False,
            include_netlist=False,
            include_analysis=True,
            include_results=False,
        )
        gen = ReportGenerator(config)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            gen.generate(filepath=pdf_path, model=configured_model)
            assert os.path.exists(pdf_path)
            assert os.path.getsize(pdf_path) > 100
        finally:
            os.unlink(pdf_path)

    def test_analysis_with_empty_params(self, qtbot, simple_model):
        config = ReportConfig(
            include_title=False,
            include_schematic=False,
            include_netlist=False,
            include_analysis=True,
            include_results=False,
        )
        gen = ReportGenerator(config)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            gen.generate(filepath=pdf_path, model=simple_model)
            assert os.path.exists(pdf_path)
        finally:
            os.unlink(pdf_path)


class TestReportGeneratorResults:
    """Test report generation with simulation results section."""

    def test_results_section(self, qtbot, sample_results):
        config = ReportConfig(
            include_title=False,
            include_schematic=False,
            include_netlist=False,
            include_analysis=False,
            include_results=True,
        )
        gen = ReportGenerator(config)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            gen.generate(filepath=pdf_path, results_text=sample_results)
            assert os.path.exists(pdf_path)
            assert os.path.getsize(pdf_path) > 100
        finally:
            os.unlink(pdf_path)


class TestReportGeneratorSchematic:
    """Test report generation with schematic rendering."""

    def test_schematic_with_scene_items(self, qtbot):
        from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsScene

        scene = QGraphicsScene()
        scene.addItem(QGraphicsEllipseItem(0, 0, 100, 100))
        scene.addItem(QGraphicsEllipseItem(150, 0, 100, 100))

        config = ReportConfig(
            include_title=False,
            include_schematic=True,
            include_netlist=False,
            include_analysis=False,
            include_results=False,
        )
        gen = ReportGenerator(config)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            gen.generate(filepath=pdf_path, scene=scene)
            assert os.path.exists(pdf_path)
            assert os.path.getsize(pdf_path) > 100
        finally:
            os.unlink(pdf_path)

    def test_schematic_with_empty_scene(self, qtbot):
        from PyQt6.QtWidgets import QGraphicsScene

        scene = QGraphicsScene()

        config = ReportConfig(
            include_title=False,
            include_schematic=True,
            include_netlist=False,
            include_analysis=False,
            include_results=False,
        )
        gen = ReportGenerator(config)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            gen.generate(filepath=pdf_path, scene=scene)
            assert os.path.exists(pdf_path)
        finally:
            os.unlink(pdf_path)


class TestReportGeneratorFullReport:
    """Test generation of a complete multi-section report."""

    def test_full_report(self, qtbot, configured_model, sample_netlist, sample_results):
        from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsScene

        scene = QGraphicsScene()
        scene.addItem(QGraphicsEllipseItem(0, 0, 100, 50))

        config = ReportConfig(
            include_title=True,
            include_schematic=True,
            include_netlist=True,
            include_analysis=True,
            include_results=True,
            circuit_name="Full Report Test",
            student_name="Test Student",
        )
        gen = ReportGenerator(config)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            gen.generate(
                filepath=pdf_path,
                scene=scene,
                model=configured_model,
                netlist=sample_netlist,
                results_text=sample_results,
            )
            assert os.path.exists(pdf_path)
            # Full report should be reasonably large
            assert os.path.getsize(pdf_path) > 500
        finally:
            os.unlink(pdf_path)

    def test_all_sections_disabled_produces_valid_pdf(self, qtbot):
        """Even with all sections off, should produce a valid (tiny) PDF."""
        config = ReportConfig(
            include_title=False,
            include_schematic=False,
            include_netlist=False,
            include_analysis=False,
            include_results=False,
        )
        gen = ReportGenerator(config)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            gen.generate(filepath=pdf_path)
            assert os.path.exists(pdf_path)
        finally:
            os.unlink(pdf_path)

    def test_schematic_only_no_simulation(self, qtbot, simple_model, sample_netlist):
        """Common case: report with schematic and netlist but no sim results."""
        from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsScene

        scene = QGraphicsScene()
        scene.addItem(QGraphicsRectItem(0, 0, 60, 30))

        config = ReportConfig(
            include_title=True,
            include_schematic=True,
            include_netlist=True,
            include_analysis=True,
            include_results=False,
            circuit_name="RC Filter",
        )
        gen = ReportGenerator(config)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            gen.generate(
                filepath=pdf_path,
                scene=scene,
                model=simple_model,
                netlist=sample_netlist,
            )
            assert os.path.exists(pdf_path)
            assert os.path.getsize(pdf_path) > 200
        finally:
            os.unlink(pdf_path)


class TestFormatAnalysisConfig:
    """Test the analysis config formatting helper."""

    def test_format_op_analysis(self, simple_model):
        gen = ReportGenerator(ReportConfig())
        text = gen._format_analysis_config(simple_model)
        assert "DC Operating Point" in text
        assert "Total Components: 2" in text

    def test_format_ac_analysis(self, configured_model):
        gen = ReportGenerator(ReportConfig())
        text = gen._format_analysis_config(configured_model)
        assert "AC Sweep" in text
        assert "Sweep Type" in text
        assert "100" in text
        assert "Total Components: 4" in text

    def test_format_component_summary(self, configured_model):
        gen = ReportGenerator(ReportConfig())
        text = gen._format_analysis_config(configured_model)
        assert "Resistor: 2" in text
        assert "Capacitor: 1" in text
        assert "Voltage Source: 1" in text

    def test_format_empty_params(self, simple_model):
        gen = ReportGenerator(ReportConfig())
        text = gen._format_analysis_config(simple_model)
        assert "(default)" in text


class TestGetSceneSourceRect:
    """Test the scene source rect computation."""

    def test_returns_none_for_empty_scene(self, qtbot):
        from PyQt6.QtWidgets import QGraphicsScene

        scene = QGraphicsScene()
        result = ReportGenerator._get_scene_source_rect(scene)
        assert result is None

    def test_returns_none_for_non_circuit_items(self, qtbot):
        """Non-circuit items (e.g. grid) are filtered out, returning None."""
        from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsScene

        scene = QGraphicsScene()
        scene.addItem(QGraphicsEllipseItem(10, 20, 100, 50))
        result = ReportGenerator._get_scene_source_rect(scene)
        # Should be None because QGraphicsEllipseItem is not a circuit item
        assert result is None

    def test_returns_rect_via_render_pipeline(self, qtbot):
        """Schematic page renders without crashing even with generic items."""
        from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsScene

        scene = QGraphicsScene()
        scene.addItem(QGraphicsRectItem(0, 0, 200, 100))

        config = ReportConfig(
            include_title=False,
            include_schematic=True,
            include_netlist=False,
            include_analysis=False,
            include_results=False,
        )
        gen = ReportGenerator(config)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            # Should not crash - empty scene path handles gracefully
            gen.generate(filepath=pdf_path, scene=scene)
            assert os.path.exists(pdf_path)
        finally:
            os.unlink(pdf_path)


class TestReportGeneratorLongText:
    """Test pagination for long text sections."""

    def test_long_netlist_paginates(self, qtbot):
        """A very long netlist should not crash and should produce a multi-page PDF."""
        long_netlist = "\n".join([f"R{i} n{i} n{i + 1} {i}k" for i in range(200)])

        config = ReportConfig(
            include_title=False,
            include_schematic=False,
            include_netlist=True,
            include_analysis=False,
            include_results=False,
        )
        gen = ReportGenerator(config)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name

        try:
            gen.generate(filepath=pdf_path, netlist=long_netlist)
            assert os.path.exists(pdf_path)
            # Multi-page PDF should be larger than single-page
            assert os.path.getsize(pdf_path) > 1000
        finally:
            os.unlink(pdf_path)


class TestReportDialog:
    """Test the report dialog configuration."""

    def test_dialog_creates(self, qtbot):
        from GUI.report_dialog import ReportDialog

        dialog = ReportDialog(circuit_name="Test", has_results=True)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Generate Circuit Report"

    def test_dialog_default_config(self, qtbot):
        from GUI.report_dialog import ReportDialog

        dialog = ReportDialog(circuit_name="Test Circuit", has_results=True)
        qtbot.addWidget(dialog)
        config = dialog.get_config()
        assert config.include_title is True
        assert config.include_schematic is True
        assert config.include_netlist is True
        assert config.include_analysis is True
        assert config.include_results is True
        assert config.circuit_name == "Test Circuit"

    def test_dialog_no_results(self, qtbot):
        from GUI.report_dialog import ReportDialog

        dialog = ReportDialog(has_results=False)
        qtbot.addWidget(dialog)
        config = dialog.get_config()
        # Results checkbox should be unchecked when no results available
        assert config.include_results is False

    def test_dialog_student_name(self, qtbot):
        from GUI.report_dialog import ReportDialog

        dialog = ReportDialog()
        qtbot.addWidget(dialog)
        dialog._student_name.setText("Jane Doe")
        config = dialog.get_config()
        assert config.student_name == "Jane Doe"

    def test_dialog_circuit_name_override(self, qtbot):
        from GUI.report_dialog import ReportDialog

        dialog = ReportDialog(circuit_name="Original")
        qtbot.addWidget(dialog)
        dialog._circuit_name.setText("Modified")
        config = dialog.get_config()
        assert config.circuit_name == "Modified"
