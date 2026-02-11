"""Tests for noise analysis support (#233).

Covers the full noise analysis pipeline: dialog configuration,
netlist generation, result parsing, display routing, menu
infrastructure, preset availability, and CSV export.
"""

import inspect

import pytest
from controllers.simulation_controller import SimulationController
from GUI.analysis_dialog import AnalysisDialog
from models.circuit import CircuitModel


class TestNoiseAnalysisDialog:
    """Test noise analysis dialog configuration."""

    def test_noise_in_analysis_configs(self):
        """Noise should be a recognized analysis type."""
        assert "Noise" in AnalysisDialog.ANALYSIS_CONFIGS

    def test_noise_has_six_fields(self, qtbot):
        """Noise dialog should have output_node, source, fStart, fStop, points, sweepType."""
        dialog = AnalysisDialog(analysis_type="Noise")
        qtbot.addWidget(dialog)
        expected = {"output_node", "source", "fStart", "fStop", "points", "sweepType"}
        assert set(dialog.field_widgets.keys()) == expected

    def test_noise_description_set(self, qtbot):
        """Noise dialog should have a description label."""
        dialog = AnalysisDialog(analysis_type="Noise")
        qtbot.addWidget(dialog)
        assert dialog.desc_label.text() != ""
        assert "noise" in dialog.desc_label.text().lower()

    def test_noise_default_values(self, qtbot):
        """Noise fields should have sensible defaults."""
        dialog = AnalysisDialog(analysis_type="Noise")
        qtbot.addWidget(dialog)
        params = dialog.get_parameters()
        assert params is not None
        assert params["output_node"] == "out"
        assert params["source"] == "V1"
        assert params["fStart"] == 1.0
        assert params["fStop"] == 1e6
        assert params["points"] == 100
        assert params["sweepType"] == "dec"

    def test_noise_get_parameters_returns_analysis_type(self, qtbot):
        """get_parameters() should include analysis_type key."""
        dialog = AnalysisDialog(analysis_type="Noise")
        qtbot.addWidget(dialog)
        params = dialog.get_parameters()
        assert params["analysis_type"] == "Noise"

    def test_noise_tooltips_present(self):
        """All noise fields should have tooltips."""
        config = AnalysisDialog.ANALYSIS_CONFIGS["Noise"]
        tooltips = config.get("tooltips", {})
        field_keys = {f[1] for f in config["fields"]}
        assert field_keys == set(tooltips.keys())


class TestNoiseNgspiceCommand:
    """Test NGSPICE command generation for noise analysis."""

    def test_noise_generates_dot_noise_command(self, qtbot):
        """get_ngspice_command() should produce a .noise directive."""
        dialog = AnalysisDialog(analysis_type="Noise")
        qtbot.addWidget(dialog)
        cmd = dialog.get_ngspice_command()
        assert cmd is not None
        assert cmd.startswith(".noise")

    def test_noise_command_contains_output_node(self, qtbot):
        """Command should reference the output node."""
        dialog = AnalysisDialog(analysis_type="Noise")
        qtbot.addWidget(dialog)
        cmd = dialog.get_ngspice_command()
        assert "v(out)" in cmd

    def test_noise_command_contains_source(self, qtbot):
        """Command should reference the input source."""
        dialog = AnalysisDialog(analysis_type="Noise")
        qtbot.addWidget(dialog)
        cmd = dialog.get_ngspice_command()
        assert "V1" in cmd

    def test_noise_command_contains_sweep_params(self, qtbot):
        """Command should include sweep type and frequency range."""
        dialog = AnalysisDialog(analysis_type="Noise")
        qtbot.addWidget(dialog)
        cmd = dialog.get_ngspice_command()
        assert "dec" in cmd
        assert "100" in cmd


class TestNoiseNetlistGeneration:
    """Test netlist generation for noise analysis."""

    def _make_circuit(self):
        """Build a simple circuit with voltage source and resistor."""
        model = CircuitModel()
        from controllers.circuit_controller import CircuitController

        ctrl = CircuitController(model)
        v1 = ctrl.add_component("Voltage Source", (0, 0))
        r1 = ctrl.add_component("Resistor", (100, 0))
        gnd = ctrl.add_component("Ground", (0, 100))
        ctrl.add_wire(v1.component_id, 0, r1.component_id, 0)
        ctrl.add_wire(r1.component_id, 1, gnd.component_id, 0)
        ctrl.add_wire(v1.component_id, 1, gnd.component_id, 0)
        return model, ctrl

    def test_noise_netlist_contains_dot_noise(self):
        """Generated netlist should contain .noise directive."""
        model, ctrl = self._make_circuit()
        sim = SimulationController(model, circuit_ctrl=ctrl)
        sim.set_analysis(
            "Noise",
            {
                "output_node": "1",
                "source": "V1",
                "fStart": 1,
                "fStop": 1e6,
                "points": 100,
                "sweepType": "dec",
            },
        )
        netlist = sim.generate_netlist()
        assert ".noise" in netlist.lower()

    def test_noise_netlist_contains_output_node(self):
        """Netlist .noise line should reference the output node."""
        model, ctrl = self._make_circuit()
        sim = SimulationController(model, circuit_ctrl=ctrl)
        sim.set_analysis(
            "Noise",
            {
                "output_node": "2",
                "source": "V1",
                "fStart": 10,
                "fStop": 100000,
                "points": 50,
                "sweepType": "dec",
            },
        )
        netlist = sim.generate_netlist()
        assert "v(2)" in netlist.lower()

    def test_noise_netlist_prints_onoise_inoise(self):
        """Noise netlist control block should print onoise_spectrum and inoise_spectrum."""
        model, ctrl = self._make_circuit()
        sim = SimulationController(model, circuit_ctrl=ctrl)
        sim.set_analysis(
            "Noise",
            {
                "output_node": "1",
                "source": "V1",
                "fStart": 1,
                "fStop": 1e6,
                "points": 100,
                "sweepType": "dec",
            },
        )
        netlist = sim.generate_netlist()
        assert "onoise_spectrum" in netlist
        assert "inoise_spectrum" in netlist

    def test_noise_netlist_uses_setplot(self):
        """Noise control block should switch to noise1 plot."""
        model, ctrl = self._make_circuit()
        sim = SimulationController(model, circuit_ctrl=ctrl)
        sim.set_analysis(
            "Noise",
            {
                "output_node": "1",
                "source": "V1",
                "fStart": 1,
                "fStop": 1e6,
                "points": 100,
                "sweepType": "dec",
            },
        )
        netlist = sim.generate_netlist()
        assert "setplot noise1" in netlist


class TestNoiseResultParser:
    """Test noise result parsing."""

    def test_parse_noise_empty_output(self):
        """Parsing empty output should return None."""
        from simulation.result_parser import ResultParser

        result = ResultParser.parse_noise_results("")
        assert result is None

    def test_parse_noise_valid_output(self):
        """Parser should extract frequencies and spectral densities."""
        from simulation.result_parser import ResultParser

        output = (
            "Index   frequency       onoise_spectrum inoise_spectrum\n"
            "0       1.000000e+00    3.200000e-09    1.600000e-09\n"
            "1       1.000000e+01    3.100000e-09    1.550000e-09\n"
            "2       1.000000e+02    3.000000e-09    1.500000e-09\n"
        )
        result = ResultParser.parse_noise_results(output)
        assert result is not None
        assert len(result["frequencies"]) == 3
        assert len(result["onoise_spectrum"]) == 3
        assert len(result["inoise_spectrum"]) == 3
        assert result["frequencies"][0] == pytest.approx(1.0)
        assert result["frequencies"][2] == pytest.approx(100.0)

    def test_parse_noise_onoise_values(self):
        """Output noise values should be parsed correctly."""
        from simulation.result_parser import ResultParser

        output = (
            "Index   frequency       onoise_spectrum inoise_spectrum\n"
            "0       1.000000e+00    5.000000e-08    2.500000e-08\n"
        )
        result = ResultParser.parse_noise_results(output)
        assert result is not None
        assert result["onoise_spectrum"][0] == pytest.approx(5e-8)
        assert result["inoise_spectrum"][0] == pytest.approx(2.5e-8)

    def test_parse_noise_no_matching_header(self):
        """Output without noise headers should return None."""
        from simulation.result_parser import ResultParser

        output = "some random text\nwithout noise data\n"
        result = ResultParser.parse_noise_results(output)
        assert result is None


class TestNoiseSimulationController:
    """Test simulation controller handles noise analysis type."""

    def test_set_analysis_noise(self):
        """set_analysis should store Noise type."""
        model = CircuitModel()
        sim = SimulationController(model)
        sim.set_analysis("Noise", {"output_node": "out", "source": "V1"})
        assert model.analysis_type == "Noise"
        assert model.analysis_params["output_node"] == "out"

    def test_parse_results_has_noise_branch(self):
        """_parse_results should handle 'Noise' analysis type."""
        source = inspect.getsource(SimulationController._parse_results)
        assert '"Noise"' in source


class TestNoiseMenuIntegration:
    """Test menu infrastructure for noise analysis."""

    def test_analysis_menu_has_noise_action(self):
        """MenuBarMixin should create a noise_action."""
        from GUI.main_window_menus import MenuBarMixin

        source = inspect.getsource(MenuBarMixin.create_menu_bar)
        assert "noise_action" in source
        assert "set_analysis_noise" in source

    def test_analysis_settings_has_noise_method(self):
        """AnalysisSettingsMixin should have set_analysis_noise."""
        from GUI.main_window_analysis import AnalysisSettingsMixin

        assert hasattr(AnalysisSettingsMixin, "set_analysis_noise")

    def test_sync_analysis_menu_handles_noise(self):
        """_sync_analysis_menu should check for 'Noise' type."""
        from GUI.main_window_analysis import AnalysisSettingsMixin

        source = inspect.getsource(AnalysisSettingsMixin._sync_analysis_menu)
        assert '"Noise"' in source

    def test_display_handlers_include_noise(self):
        """SimulationMixin handlers dict should include Noise."""
        from GUI.main_window_simulation import SimulationMixin

        source = inspect.getsource(SimulationMixin._display_simulation_results)
        assert '"Noise"' in source
        assert "_display_noise_results" in source

    def test_display_noise_results_method_exists(self):
        """SimulationMixin should have _display_noise_results method."""
        from GUI.main_window_simulation import SimulationMixin

        assert hasattr(SimulationMixin, "_display_noise_results")


class TestNoisePresets:
    """Test noise analysis presets."""

    def test_builtin_noise_presets_exist(self):
        """There should be at least one built-in Noise preset."""
        from simulation.preset_manager import BUILTIN_PRESETS

        noise_presets = [p for p in BUILTIN_PRESETS if p["analysis_type"] == "Noise"]
        assert len(noise_presets) >= 1

    def test_audio_band_noise_preset_params(self):
        """Audio Band Noise preset should have correct frequency range."""
        from simulation.preset_manager import BUILTIN_PRESETS

        audio = next(p for p in BUILTIN_PRESETS if p["name"] == "Audio Band Noise")
        assert audio["params"]["fStart"] == 20
        assert audio["params"]["fStop"] == 20000

    def test_noise_preset_has_required_keys(self):
        """All noise presets should have required parameter keys."""
        from simulation.preset_manager import BUILTIN_PRESETS

        required = {"output_node", "source", "fStart", "fStop", "points", "sweepType"}
        for preset in BUILTIN_PRESETS:
            if preset["analysis_type"] == "Noise":
                assert required <= set(preset["params"].keys()), f"Preset {preset['name']} missing keys"


class TestNoiseCSVExport:
    """Test noise CSV export."""

    def test_export_noise_results_function_exists(self):
        """csv_exporter should have export_noise_results."""
        from simulation.csv_exporter import export_noise_results

        assert callable(export_noise_results)

    def test_export_noise_csv_content(self):
        """Noise CSV export should contain frequency and noise columns."""
        from simulation.csv_exporter import export_noise_results

        data = {
            "frequencies": [1.0, 10.0, 100.0],
            "onoise_spectrum": [3.2e-9, 3.1e-9, 3.0e-9],
            "inoise_spectrum": [1.6e-9, 1.5e-9, 1.4e-9],
        }
        csv = export_noise_results(data, "test_circuit")
        assert "Noise" in csv
        assert "Frequency" in csv
        assert "Output Noise" in csv
        assert "Input Noise" in csv

    def test_csv_export_handles_noise_type(self):
        """main_window_simulation CSV export should route noise results."""
        from GUI.main_window_simulation import SimulationMixin

        source = inspect.getsource(SimulationMixin.export_results_csv)
        assert "export_noise_results" in source
        assert '"Noise"' in source


class TestNoiseModelSerialization:
    """Test that Noise analysis type survives save/load."""

    def test_noise_analysis_roundtrip(self):
        """Circuit with Noise analysis should serialize and deserialize."""
        model = CircuitModel()
        model.analysis_type = "Noise"
        model.analysis_params = {
            "output_node": "out",
            "source": "V1",
            "fStart": 1,
            "fStop": 1e6,
            "points": 100,
            "sweepType": "dec",
        }
        data = model.to_dict()
        restored = CircuitModel.from_dict(data)
        assert restored.analysis_type == "Noise"
        assert restored.analysis_params["output_node"] == "out"
        assert restored.analysis_params["fStop"] == 1e6
