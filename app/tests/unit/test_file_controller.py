"""Tests for FileController."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from controllers.file_controller import FileController, validate_circuit_data
from models.circuit import CircuitModel
from models.component import ComponentData
from models.wire import WireData


def _build_simple_circuit():
    """Build a simple V1-R1-GND circuit model."""
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
    model.components["GND1"] = ComponentData(
        component_id="GND1",
        component_type="Ground",
        value="0V",
        position=(0.0, 100.0),
    )
    model.wires = [
        WireData(start_component_id="V1", start_terminal=1, end_component_id="R1", end_terminal=0),
        WireData(start_component_id="R1", start_terminal=1, end_component_id="GND1", end_terminal=0),
        WireData(start_component_id="V1", start_terminal=0, end_component_id="GND1", end_terminal=0),
    ]
    model.component_counter = {"V": 1, "R": 1, "GND": 1}
    model.rebuild_nodes()
    return model


class TestSaveLoad:
    def test_save_creates_file(self, tmp_path):
        model = _build_simple_circuit()
        ctrl = FileController(model)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)
        assert filepath.exists()

    def test_save_updates_current_file(self, tmp_path):
        ctrl = FileController(_build_simple_circuit())
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)
        assert ctrl.current_file == filepath

    def test_save_writes_valid_json(self, tmp_path):
        ctrl = FileController(_build_simple_circuit())
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)
        data = json.loads(filepath.read_text())
        assert "components" in data
        assert "wires" in data

    def test_load_restores_components(self, tmp_path):
        model = _build_simple_circuit()
        ctrl = FileController(model)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)

        # Load into a fresh controller
        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)
        assert "V1" in ctrl2.model.components
        assert "R1" in ctrl2.model.components
        assert "GND1" in ctrl2.model.components

    def test_load_restores_wires(self, tmp_path):
        model = _build_simple_circuit()
        ctrl = FileController(model)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)

        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)
        assert len(ctrl2.model.wires) == 3

    def test_load_rebuilds_nodes(self, tmp_path):
        model = _build_simple_circuit()
        ctrl = FileController(model)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)

        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)
        assert len(ctrl2.model.nodes) > 0

    def test_load_restores_counters(self, tmp_path):
        model = _build_simple_circuit()
        ctrl = FileController(model)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)

        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)
        assert ctrl2.model.component_counter.get("V") == 1
        assert ctrl2.model.component_counter.get("R") == 1

    def test_round_trip_preserves_data(self, tmp_path):
        model = _build_simple_circuit()
        ctrl = FileController(model)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)

        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)

        # Same components
        assert set(ctrl2.model.components.keys()) == set(model.components.keys())
        # Same wire count
        assert len(ctrl2.model.wires) == len(model.wires)

    def test_load_updates_model_in_place(self, tmp_path):
        """Loading should update the existing model reference, not replace it."""
        ctrl = FileController(_build_simple_circuit())
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)

        model_ref = ctrl.model
        ctrl.load_circuit(filepath)
        assert ctrl.model is model_ref

    def test_load_restores_analysis_settings(self, tmp_path):
        """Loading should restore analysis_type and analysis_params from JSON."""
        model = _build_simple_circuit()
        model.analysis_type = "Transient"
        model.analysis_params = {"duration": 0.01, "step": 1e-5, "startTime": 0.0}
        ctrl = FileController(model)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)

        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)
        assert ctrl2.model.analysis_type == "Transient"
        assert ctrl2.model.analysis_params["duration"] == 0.01
        assert ctrl2.model.analysis_params["step"] == 1e-5


class TestLoadErrors:
    def test_load_invalid_json_raises(self, tmp_path):
        filepath = tmp_path / "bad.json"
        filepath.write_text("not json at all")
        ctrl = FileController()
        with pytest.raises(json.JSONDecodeError):
            ctrl.load_circuit(filepath)

    def test_load_missing_components_raises(self, tmp_path):
        filepath = tmp_path / "bad.json"
        filepath.write_text(json.dumps({"wires": []}))
        ctrl = FileController()
        with pytest.raises(ValueError, match="components"):
            ctrl.load_circuit(filepath)

    def test_load_missing_wires_raises(self, tmp_path):
        filepath = tmp_path / "bad.json"
        filepath.write_text(json.dumps({"components": []}))
        ctrl = FileController()
        with pytest.raises(ValueError, match="wires"):
            ctrl.load_circuit(filepath)

    def test_load_nonexistent_file_raises(self):
        ctrl = FileController()
        with pytest.raises(OSError):
            ctrl.load_circuit("/nonexistent/path/file.json")


class TestNewCircuit:
    def test_new_clears_model(self):
        ctrl = FileController(_build_simple_circuit())
        ctrl.current_file = Path("some_file.json")
        ctrl.new_circuit()
        assert len(ctrl.model.components) == 0
        assert len(ctrl.model.wires) == 0
        assert ctrl.current_file is None


class TestSessionPersistence:
    def test_save_creates_session_file(self, tmp_path):
        session_file = str(tmp_path / "session.txt")
        ctrl = FileController(_build_simple_circuit(), session_file=session_file)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)
        assert Path(session_file).exists()

    def test_load_last_session_returns_path(self, tmp_path):
        session_file = str(tmp_path / "session.txt")
        ctrl = FileController(_build_simple_circuit(), session_file=session_file)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)

        ctrl2 = FileController(session_file=session_file)
        last = ctrl2.load_last_session()
        assert last is not None
        assert last.name == "test.json"

    def test_load_last_session_returns_none_when_no_session(self, tmp_path):
        session_file = str(tmp_path / "no_session.txt")
        ctrl = FileController(session_file=session_file)
        assert ctrl.load_last_session() is None

    def test_load_last_session_returns_none_when_file_deleted(self, tmp_path):
        session_file = str(tmp_path / "session.txt")
        ctrl = FileController(_build_simple_circuit(), session_file=session_file)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)
        filepath.unlink()  # Delete the circuit file

        ctrl2 = FileController(session_file=session_file)
        assert ctrl2.load_last_session() is None


class TestWindowTitle:
    def test_title_with_no_file(self):
        ctrl = FileController()
        assert ctrl.get_window_title() == "Circuit Design GUI"

    def test_title_with_file(self, tmp_path):
        ctrl = FileController(_build_simple_circuit())
        filepath = tmp_path / "my_circuit.json"
        ctrl.save_circuit(filepath)
        assert "my_circuit.json" in ctrl.get_window_title()

    def test_title_custom_base(self):
        ctrl = FileController()
        assert ctrl.get_window_title("SDM Spice") == "SDM Spice"


class TestHasFile:
    def test_has_file_false_initially(self):
        ctrl = FileController()
        assert not ctrl.has_file()

    def test_has_file_true_after_save(self, tmp_path):
        ctrl = FileController(_build_simple_circuit())
        ctrl.save_circuit(tmp_path / "test.json")
        assert ctrl.has_file()


class TestValidateCircuitData:
    def test_valid_data_passes(self):
        data = {"components": [{"id": "R1", "type": "Resistor", "value": "1k", "pos": {"x": 0, "y": 0}}], "wires": []}
        validate_circuit_data(data)  # Should not raise

    def test_not_a_dict_raises(self):
        with pytest.raises(ValueError, match="valid circuit"):
            validate_circuit_data([])

    def test_wire_references_unknown_component(self):
        data = {
            "components": [{"id": "R1", "type": "Resistor", "value": "1k", "pos": {"x": 0, "y": 0}}],
            "wires": [{"start_comp": "R1", "start_term": 0, "end_comp": "UNKNOWN", "end_term": 0}],
        }
        with pytest.raises(ValueError, match="unknown component"):
            validate_circuit_data(data)


class TestRecentFiles:
    """Test recent files functionality (Issue #101)."""

    @patch("controllers.file_controller.QSettings")
    def test_get_recent_files_returns_empty_list_initially(self, mock_qsettings):
        """get_recent_files should return empty list when no recent files."""
        mock_settings_instance = MagicMock()
        mock_settings_instance.value.return_value = []
        mock_qsettings.return_value = mock_settings_instance

        ctrl = FileController()
        recent = ctrl.get_recent_files()
        assert recent == []

    @patch("controllers.file_controller.QSettings")
    def test_add_recent_file_adds_to_list(self, mock_qsettings, tmp_path):
        """add_recent_file should add file to recent list."""
        mock_settings_instance = MagicMock()
        mock_settings_instance.value.return_value = []
        mock_qsettings.return_value = mock_settings_instance

        ctrl = FileController()
        filepath = tmp_path / "test.json"
        filepath.touch()  # Create file
        ctrl.add_recent_file(filepath)

        # Check that setValue was called with the file path
        mock_settings_instance.setValue.assert_called()
        call_args = mock_settings_instance.setValue.call_args
        assert call_args[0][0] == "file/recent_files"
        assert str(filepath.absolute()) in call_args[0][1]

    @patch("controllers.file_controller.os.path.exists")
    @patch("controllers.file_controller.QSettings")
    def test_add_recent_file_moves_to_front_if_exists(self, mock_qsettings, mock_exists, tmp_path):
        """add_recent_file should move existing file to front."""
        file1 = str((tmp_path / "file1.json").absolute())
        file2 = str((tmp_path / "file2.json").absolute())

        # Mock: all files exist
        mock_exists.return_value = True

        mock_settings_instance = MagicMock()
        mock_settings_instance.value.return_value = [file2, file1]
        mock_qsettings.return_value = mock_settings_instance

        ctrl = FileController()
        ctrl.add_recent_file(Path(file1))

        # file1 should now be at the front
        call_args = mock_settings_instance.setValue.call_args
        saved_list = call_args[0][1]
        assert saved_list[0] == file1
        assert saved_list[1] == file2

    @patch("controllers.file_controller.os.path.exists")
    @patch("controllers.file_controller.QSettings")
    def test_add_recent_file_maintains_max_limit(self, mock_qsettings, mock_exists, tmp_path):
        """add_recent_file should keep only MAX_RECENT_FILES (10) files."""
        # Create 11 file paths
        existing_files = [str((tmp_path / f"file{i}.json").absolute()) for i in range(10)]
        new_file = tmp_path / "file11.json"

        # Mock: all files exist
        mock_exists.return_value = True

        mock_settings_instance = MagicMock()
        mock_settings_instance.value.return_value = existing_files
        mock_qsettings.return_value = mock_settings_instance

        ctrl = FileController()
        ctrl.add_recent_file(new_file)

        # Should have exactly 10 files
        call_args = mock_settings_instance.setValue.call_args
        saved_list = call_args[0][1]
        assert len(saved_list) == 10
        assert saved_list[0] == str(new_file.absolute())

    @patch("controllers.file_controller.QSettings")
    @patch("controllers.file_controller.os.path.exists")
    def test_get_recent_files_filters_missing_files(self, mock_exists, mock_qsettings, tmp_path):
        """get_recent_files should filter out files that no longer exist."""
        file1 = str((tmp_path / "exists.json").absolute())
        file2 = str((tmp_path / "missing.json").absolute())

        # Mock: file1 exists, file2 doesn't
        mock_exists.side_effect = lambda f: f == file1

        mock_settings_instance = MagicMock()
        mock_settings_instance.value.return_value = [file1, file2]
        mock_qsettings.return_value = mock_settings_instance

        ctrl = FileController()
        recent = ctrl.get_recent_files()

        # Should only return existing file
        assert recent == [file1]

        # Should update settings to remove missing file
        assert mock_settings_instance.setValue.called

    @patch("controllers.file_controller.QSettings")
    def test_clear_recent_files(self, mock_qsettings):
        """clear_recent_files should empty the list."""
        mock_settings_instance = MagicMock()
        mock_qsettings.return_value = mock_settings_instance

        ctrl = FileController()
        ctrl.clear_recent_files()

        # Should save empty list
        mock_settings_instance.setValue.assert_called_with("file/recent_files", [])

    @patch("controllers.file_controller.QSettings")
    def test_save_circuit_updates_recent_files(self, mock_qsettings, tmp_path):
        """save_circuit should add file to recent files list."""
        mock_settings_instance = MagicMock()
        mock_settings_instance.value.return_value = []
        mock_qsettings.return_value = mock_settings_instance

        model = _build_simple_circuit()
        ctrl = FileController(model)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)

        # Should have called setValue to add to recent files
        calls = [call[0][0] for call in mock_settings_instance.setValue.call_args_list]
        assert "file/recent_files" in calls

    @patch("controllers.file_controller.QSettings")
    def test_load_circuit_updates_recent_files(self, mock_qsettings, tmp_path):
        """load_circuit should add file to recent files list."""
        # First save a circuit
        model = _build_simple_circuit()
        filepath = tmp_path / "test.json"

        mock_settings_instance = MagicMock()
        mock_settings_instance.value.return_value = []
        mock_qsettings.return_value = mock_settings_instance

        ctrl = FileController(model)
        ctrl.save_circuit(filepath)

        # Now load it with a new controller
        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)

        # Should have called setValue to add to recent files
        calls = [call[0][0] for call in mock_settings_instance.setValue.call_args_list]
        assert "file/recent_files" in calls


class TestQtDependencies:
    def test_qsettings_imported_for_recent_files(self):
        """FileController now uses QSettings for recent files (Issue #101)."""
        import controllers.file_controller as mod

        source = open(mod.__file__).read()
        # QSettings should be imported
        assert "QSettings" in source
        # But no QtWidgets (stays out of view layer)
        assert "QtWidgets" not in source
