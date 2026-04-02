"""Tests for FileController."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from controllers.file_controller import FileController, validate_circuit_data
from models.circuit import CircuitModel
from models.wire import WireData
from tests.conftest import build_simple_circuit


class TestSaveLoad:
    def test_save_creates_file(self, tmp_path):
        model = build_simple_circuit()
        ctrl = FileController(model)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)
        assert filepath.exists()

    def test_save_updates_current_file(self, tmp_path):
        ctrl = FileController(build_simple_circuit())
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)
        assert ctrl.current_file == filepath

    def test_save_writes_valid_json(self, tmp_path):
        ctrl = FileController(build_simple_circuit())
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)
        data = json.loads(filepath.read_text())
        assert "components" in data
        assert "wires" in data

    def test_save_includes_schema_version(self, tmp_path):
        from models.circuit import SCHEMA_VERSION

        ctrl = FileController(build_simple_circuit())
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)
        data = json.loads(filepath.read_text())
        assert data["schema_version"] == SCHEMA_VERSION

    def test_load_file_without_schema_version(self, tmp_path):
        """Files saved before schema_version was added should still load."""
        data = {
            "components": [
                {"id": "R1", "type": "Resistor", "value": "1k", "pos": {"x": 0, "y": 0}},
            ],
            "wires": [],
            "counters": {"Resistor": 1},
        }
        filepath = tmp_path / "legacy.json"
        filepath.write_text(json.dumps(data))
        ctrl = FileController()
        ctrl.load_circuit(filepath)
        assert "R1" in ctrl.model.components

    def test_load_restores_components(self, tmp_path):
        model = build_simple_circuit()
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
        model = build_simple_circuit()
        ctrl = FileController(model)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)

        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)
        assert len(ctrl2.model.wires) == 3

    def test_load_rebuilds_nodes(self, tmp_path):
        model = build_simple_circuit()
        ctrl = FileController(model)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)

        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)
        assert len(ctrl2.model.nodes) > 0

    def test_load_restores_counters(self, tmp_path):
        model = build_simple_circuit()
        ctrl = FileController(model)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)

        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)
        assert ctrl2.model.component_counter.get("V") == 1
        assert ctrl2.model.component_counter.get("R") == 1

    def test_round_trip_preserves_data(self, tmp_path):
        model = build_simple_circuit()
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
        ctrl = FileController(build_simple_circuit())
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)

        model_ref = ctrl.model
        ctrl.load_circuit(filepath)
        assert ctrl.model is model_ref

    def test_load_restores_analysis_settings(self, tmp_path):
        """Loading should restore analysis_type and analysis_params from JSON."""
        model = build_simple_circuit()
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
        ctrl = FileController(build_simple_circuit())
        ctrl.current_file = Path("some_file.json")
        ctrl.new_circuit()
        assert len(ctrl.model.components) == 0
        assert len(ctrl.model.wires) == 0
        assert ctrl.current_file is None


class TestSessionPersistence:
    def test_save_creates_session_file(self, tmp_path):
        session_file = str(tmp_path / "session.txt")
        ctrl = FileController(build_simple_circuit(), session_file=session_file)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)
        assert Path(session_file).exists()

    def test_load_last_session_returns_path(self, tmp_path):
        session_file = str(tmp_path / "session.txt")
        ctrl = FileController(build_simple_circuit(), session_file=session_file)
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
        ctrl = FileController(build_simple_circuit(), session_file=session_file)
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
        ctrl = FileController(build_simple_circuit())
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
        ctrl = FileController(build_simple_circuit())
        ctrl.save_circuit(tmp_path / "test.json")
        assert ctrl.has_file()


class TestValidateCircuitData:
    def test_valid_data_passes(self):
        data = {
            "components": [{"id": "R1", "type": "Resistor", "value": "1k", "pos": {"x": 0, "y": 0}}],
            "wires": [],
        }
        validate_circuit_data(data)  # Should not raise

    def test_not_a_dict_raises(self):
        with pytest.raises(ValueError, match="valid circuit"):
            validate_circuit_data([])

    def test_wire_references_unknown_component(self):
        data = {
            "components": [{"id": "R1", "type": "Resistor", "value": "1k", "pos": {"x": 0, "y": 0}}],
            "wires": [
                {
                    "start_comp": "R1",
                    "start_term": 0,
                    "end_comp": "UNKNOWN",
                    "end_term": 0,
                }
            ],
        }
        with pytest.raises(ValueError, match="unknown component"):
            validate_circuit_data(data)


class TestRecentFiles:
    """Test recent files functionality (Issue #101)."""

    @patch("controllers.file_controller.settings")
    def test_get_recent_files_returns_empty_list_initially(self, mock_settings):
        """get_recent_files should return empty list when no recent files."""
        mock_settings.get_list.return_value = []

        ctrl = FileController()
        recent = ctrl.get_recent_files()
        assert recent == []

    @patch("controllers.file_controller.settings")
    def test_add_recent_file_adds_to_list(self, mock_settings, tmp_path):
        """add_recent_file should add file to recent list."""
        mock_settings.get_list.return_value = []

        ctrl = FileController()
        filepath = tmp_path / "test.json"
        filepath.touch()  # Create file
        ctrl.add_recent_file(filepath)

        # Check that set was called with the file path
        mock_settings.set.assert_called()
        call_args = mock_settings.set.call_args
        assert call_args[0][0] == "file/recent_files"
        assert str(filepath.absolute()) in call_args[0][1]

    @patch("controllers.file_controller.os.path.exists")
    @patch("controllers.file_controller.settings")
    def test_add_recent_file_moves_to_front_if_exists(self, mock_settings, mock_exists, tmp_path):
        """add_recent_file should move existing file to front."""
        file1 = str((tmp_path / "file1.json").absolute())
        file2 = str((tmp_path / "file2.json").absolute())

        # Mock: all files exist
        mock_exists.return_value = True

        mock_settings.get_list.return_value = [file2, file1]

        ctrl = FileController()
        ctrl.add_recent_file(Path(file1))

        # file1 should now be at the front
        call_args = mock_settings.set.call_args
        saved_list = call_args[0][1]
        assert saved_list[0] == file1
        assert saved_list[1] == file2

    @patch("controllers.file_controller.os.path.exists")
    @patch("controllers.file_controller.settings")
    def test_add_recent_file_maintains_max_limit(self, mock_settings, mock_exists, tmp_path):
        """add_recent_file should keep only MAX_RECENT_FILES (10) files."""
        # Create 11 file paths
        existing_files = [str((tmp_path / f"file{i}.json").absolute()) for i in range(10)]
        new_file = tmp_path / "file11.json"

        # Mock: all files exist
        mock_exists.return_value = True

        mock_settings.get_list.return_value = existing_files

        ctrl = FileController()
        ctrl.add_recent_file(new_file)

        # Should have exactly 10 files
        call_args = mock_settings.set.call_args
        saved_list = call_args[0][1]
        assert len(saved_list) == 10
        assert saved_list[0] == str(new_file.absolute())

    @patch("controllers.file_controller.settings")
    @patch("controllers.file_controller.os.path.exists")
    def test_get_recent_files_filters_missing_files(self, mock_exists, mock_settings, tmp_path):
        """get_recent_files should filter out files that no longer exist."""
        file1 = str((tmp_path / "exists.json").absolute())
        file2 = str((tmp_path / "missing.json").absolute())

        # Mock: file1 exists, file2 doesn't
        mock_exists.side_effect = lambda f: f == file1

        mock_settings.get_list.return_value = [file1, file2]

        ctrl = FileController()
        recent = ctrl.get_recent_files()

        # Should only return existing file
        assert recent == [file1]

        # Should update settings to remove missing file
        assert mock_settings.set.called

    @patch("controllers.file_controller.settings")
    def test_clear_recent_files(self, mock_settings):
        """clear_recent_files should empty the list."""
        ctrl = FileController()
        ctrl.clear_recent_files()

        # Should save empty list
        mock_settings.set.assert_called_with("file/recent_files", [])

    @patch("controllers.file_controller.settings")
    def test_save_circuit_updates_recent_files(self, mock_settings, tmp_path):
        """save_circuit should add file to recent files list."""
        mock_settings.get_list.return_value = []

        model = build_simple_circuit()
        ctrl = FileController(model)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)

        # Should have called set to add to recent files
        calls = [call[0][0] for call in mock_settings.set.call_args_list]
        assert "file/recent_files" in calls

    @patch("controllers.file_controller.settings")
    def test_load_circuit_updates_recent_files(self, mock_settings, tmp_path):
        """load_circuit should add file to recent files list."""
        # First save a circuit
        model = build_simple_circuit()
        filepath = tmp_path / "test.json"

        mock_settings.get_list.return_value = []

        ctrl = FileController(model)
        ctrl.save_circuit(filepath)

        # Now load it with a new controller
        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)

        # Should have called set to add to recent files
        calls = [call[0][0] for call in mock_settings.set.call_args_list]
        assert "file/recent_files" in calls


class TestImportPreservesCircuitOnFailure:
    """Issue #489: import must not clear the circuit before validating parsed data."""

    def test_load_circuit_with_valid_data_succeeds(self, tmp_path):
        """A structurally valid JSON file should load without error."""
        bad_data = {
            "components": [
                {
                    "id": "R1",
                    "type": "Resistor",
                    "value": "1k",
                    "pos": {"x": 0, "y": 0},
                },
            ],
            "wires": [
                {"start_comp": "R1", "start_term": 0, "end_comp": "R1", "end_term": 1},
            ],
        }
        filepath = tmp_path / "valid.json"
        filepath.write_text(json.dumps(bad_data))

        ctrl = FileController(build_simple_circuit())
        ctrl.load_circuit(filepath)
        assert "R1" in ctrl.model.components

    def test_import_netlist_preserves_model_on_parse_error(self, tmp_path):
        """If the parser raises, the original circuit must survive."""
        model = build_simple_circuit()
        ctrl = FileController(model)
        original_ids = set(model.components.keys())

        filepath = tmp_path / "bad.cir"
        filepath.write_text("this is not a valid netlist")

        with pytest.raises(Exception):
            ctrl.import_netlist(filepath)

        # Original circuit must still be intact
        assert set(ctrl.model.components.keys()) == original_ids

    def test_load_from_dict_skips_corrupt_components(self):
        """load_from_dict must skip corrupt components gracefully (issue #488)."""
        model = build_simple_circuit()
        ctrl = FileController(model)

        # A corrupt component dict (missing 'pos') is silently skipped
        # by the resilient from_dict.
        bad_data = {
            "components": [{"id": "X1", "type": "Resistor", "value": "1k"}],
            "wires": [],
        }
        ctrl.load_from_dict(bad_data)

        # The corrupt component was skipped, so the model has no components
        assert "X1" not in ctrl.model.components

    def test_replace_model_validates_before_clearing(self):
        """_replace_model must validate the new model before touching the old one."""
        model = build_simple_circuit()
        ctrl = FileController(model)
        original_ids = set(model.components.keys())

        # Build a model with a wire pointing at a non-existent component
        bad_model = CircuitModel()
        bad_model.wires = [
            WireData(
                start_component_id="GHOST",
                start_terminal=0,
                end_component_id="PHANTOM",
                end_terminal=1,
            )
        ]

        with pytest.raises(ValueError):
            ctrl._replace_model(bad_model)

        # Original circuit untouched
        assert set(ctrl.model.components.keys()) == original_ids


class TestAnnotationsAndRecommendedComponents:
    """Issue #498: FileController load methods silently drop annotations and recommended_components."""

    def _build_circuit_with_extras(self):
        """Build a circuit with annotations and recommended_components."""
        from models.annotation import AnnotationData

        model = build_simple_circuit()
        model.annotations = [
            AnnotationData(
                text="Test note",
                x=50.0,
                y=50.0,
                font_size=12,
                bold=True,
                color="#FF0000",
            ),
        ]
        model.recommended_components = ["Resistor", "Capacitor", "Op-Amp"]
        return model

    def test_load_circuit_preserves_annotations(self, tmp_path):
        model = self._build_circuit_with_extras()
        ctrl = FileController(model)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)

        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)
        assert len(ctrl2.model.annotations) == 1
        assert ctrl2.model.annotations[0].text == "Test note"
        assert ctrl2.model.annotations[0].bold is True

    def test_load_circuit_preserves_recommended_components(self, tmp_path):
        model = self._build_circuit_with_extras()
        ctrl = FileController(model)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)

        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)
        assert ctrl2.model.recommended_components == ["Resistor", "Capacitor", "Op-Amp"]

    def test_load_from_dict_preserves_recommended_components(self):
        model = self._build_circuit_with_extras()
        data = model.to_dict()

        ctrl = FileController()
        ctrl.load_from_dict(data)
        assert ctrl.model.recommended_components == ["Resistor", "Capacitor", "Op-Amp"]
        assert len(ctrl.model.annotations) == 1

    def test_autosave_preserves_annotations_and_recommended(self, tmp_path):
        model = self._build_circuit_with_extras()
        autosave_file = str(tmp_path / ".autosave_recovery.json")
        ctrl = FileController(model, autosave_file=autosave_file)
        ctrl.auto_save()

        ctrl2 = FileController(autosave_file=autosave_file)
        ctrl2.load_auto_save()
        assert len(ctrl2.model.annotations) == 1
        assert ctrl2.model.annotations[0].text == "Test note"
        assert ctrl2.model.recommended_components == ["Resistor", "Capacitor", "Op-Amp"]

    def test_round_trip_full_model(self, tmp_path):
        """Save and load a model with all fields — nothing should be lost."""
        from models.annotation import AnnotationData

        model = build_simple_circuit()
        model.annotations = [
            AnnotationData(text="A", x=10, y=20),
            AnnotationData(text="B", x=30, y=40, bold=True),
        ]
        model.recommended_components = ["Inductor"]
        model.analysis_type = "AC Sweep"
        model.analysis_params = {"fstart": "1", "fstop": "1Meg"}

        ctrl = FileController(model)
        filepath = tmp_path / "full.json"
        ctrl.save_circuit(filepath)

        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)
        assert len(ctrl2.model.annotations) == 2
        assert ctrl2.model.annotations[1].bold is True
        assert ctrl2.model.recommended_components == ["Inductor"]
        assert ctrl2.model.analysis_type == "AC Sweep"


class TestReplaceModelDeepCopy:
    """Issue #532: _replace_model must produce an independent copy, not share references."""

    def test_replace_model_does_not_share_component_dict(self):
        """Mutating components after replace must not affect the source model."""
        source = build_simple_circuit()
        ctrl = FileController(CircuitModel())
        ctrl._replace_model(source)

        # Mutate the loaded model
        ctrl.model.components["R1"].value = "CHANGED"

        # Source model must be unaffected
        assert source.components["R1"].value != "CHANGED"

    def test_replace_model_does_not_share_wire_list(self):
        """Appending to wires after replace must not affect the source model."""
        source = build_simple_circuit()
        original_wire_count = len(source.wires)
        ctrl = FileController(CircuitModel())
        ctrl._replace_model(source)

        ctrl.model.wires.clear()
        assert len(source.wires) == original_wire_count

    def test_replace_model_copies_all_dataclass_fields(self):
        """Every field on CircuitModel must be transferred by _replace_model."""
        from dataclasses import fields

        source = build_simple_circuit()
        source.analysis_type = "AC Sweep"
        source.analysis_params = {"fstart": "1", "fstop": "1Meg"}
        source.recommended_components = ["Inductor"]

        ctrl = FileController(CircuitModel())
        ctrl._replace_model(source)

        for f in fields(CircuitModel):
            assert getattr(ctrl.model, f.name) is not None, f"Field {f.name!r} was not copied"

    def test_replace_model_preserves_identity(self):
        """_replace_model must update the existing model object, not replace it."""
        ctrl = FileController()
        original_model = ctrl.model
        ctrl._replace_model(build_simple_circuit())
        assert ctrl.model is original_model


class TestExportBom:
    """Tests for FileController.export_bom (Issue #570)."""

    @patch("controllers.file_controller.settings")
    def test_export_bom_csv(self, mock_settings, tmp_path):
        model = build_simple_circuit()
        ctrl = FileController(model)
        filepath = tmp_path / "bom.csv"
        ctrl.export_bom(str(filepath), circuit_name="test")
        assert filepath.exists()
        content = filepath.read_text()
        assert "R1" in content or "Resistor" in content

    @patch("controllers.file_controller.settings")
    def test_export_bom_excel(self, mock_settings, tmp_path):
        model = build_simple_circuit()
        ctrl = FileController(model)
        filepath = tmp_path / "bom.xlsx"
        ctrl.export_bom(str(filepath), circuit_name="test")
        assert filepath.exists()


class TestExportAsc:
    """Tests for FileController.export_asc (Issue #570)."""

    @patch("controllers.file_controller.settings")
    def test_export_asc_writes_file(self, mock_settings, tmp_path):
        model = build_simple_circuit()
        ctrl = FileController(model)
        filepath = tmp_path / "circuit.asc"
        ctrl.export_asc(str(filepath))
        assert filepath.exists()
        content = filepath.read_text()
        assert len(content) > 0


class TestImportNetlist:
    """Tests for FileController.import_netlist (#502)."""

    @patch("controllers.file_controller.settings")
    def test_import_simple_netlist(self, mock_settings, tmp_path):
        """A valid SPICE netlist should populate the model."""
        mock_settings.get_list.return_value = []
        netlist = tmp_path / "circuit.cir"
        netlist.write_text("Test Circuit\nV1 1 0 DC 5V\nR1 1 0 1k\n.op\n.end\n")
        model = CircuitModel()
        ctrl = FileController(model)
        ctrl.import_netlist(netlist)
        assert len(ctrl.model.components) > 0
        assert ctrl.current_file is None  # import clears current_file

    @patch("controllers.file_controller.settings")
    def test_import_netlist_file_not_found(self, mock_settings, tmp_path):
        """Missing file should raise OSError."""
        ctrl = FileController(CircuitModel())
        with pytest.raises(OSError):
            ctrl.import_netlist(tmp_path / "nonexistent.cir")

    @patch("controllers.file_controller.settings")
    def test_import_netlist_sets_analysis(self, mock_settings, tmp_path):
        """Analysis directives should be extracted from the netlist."""
        mock_settings.get_list.return_value = []
        netlist = tmp_path / "tran.cir"
        netlist.write_text("Transient Test\nV1 1 0 DC 5V\nR1 1 0 1k\n.tran 1u 1m\n.end\n")
        ctrl = FileController(CircuitModel())
        ctrl.import_netlist(netlist)
        assert ctrl.model.analysis_type == "Transient"


class TestImportAsc:
    """Tests for FileController.import_asc (#502)."""

    @patch("controllers.file_controller.settings")
    def test_import_simple_asc(self, mock_settings, tmp_path):
        """A valid ASC file should populate the model."""
        mock_settings.get_list.return_value = []
        asc = tmp_path / "circuit.asc"
        asc.write_text(
            "Version 4\nSHEET 1 880 680\n"
            "SYMBOL res 160 128 R0\n"
            "SYMATTR InstName R1\nSYMATTR Value 1k\n"
            "SYMBOL voltage 48 128 R0\n"
            "SYMATTR InstName V1\nSYMATTR Value 5\n"
            "WIRE 160 128 48 128\n"
        )
        ctrl = FileController(CircuitModel())
        warnings = ctrl.import_asc(asc)
        assert isinstance(warnings, list)
        assert len(ctrl.model.components) > 0

    @patch("controllers.file_controller.settings")
    def test_import_asc_file_not_found(self, mock_settings, tmp_path):
        """Missing file should raise OSError."""
        ctrl = FileController(CircuitModel())
        with pytest.raises(OSError):
            ctrl.import_asc(tmp_path / "nonexistent.asc")


class TestImportCircuitikz:
    """Tests for FileController.import_circuitikz (#502)."""

    @patch("controllers.file_controller.settings")
    def test_import_circuitikz_file_not_found(self, mock_settings, tmp_path):
        """Missing file should raise OSError."""
        ctrl = FileController(CircuitModel())
        with pytest.raises(OSError):
            ctrl.import_circuitikz(tmp_path / "nonexistent.tex")


class TestQtDependencies:
    def test_settings_service_used_for_recent_files(self):
        """FileController uses centralized SettingsService for persistence (#598)."""
        import controllers.file_controller as mod

        source = Path(mod.__file__).read_text(encoding="utf-8")
        # Should use centralized settings service, not QSettings directly
        assert "settings_service" in source
        assert "QSettings" not in source
        # But no QtWidgets (stays out of view layer)
        assert "QtWidgets" not in source


class TestAtomicWrites:
    """Issue #765: file writes should be atomic (write-to-temp-then-rename)."""

    def test_save_circuit_atomic_no_corruption_on_error(self, tmp_path):
        """If json.dump raises, the original file must remain intact."""
        model = build_simple_circuit()
        ctrl = FileController(model)
        filepath = tmp_path / "circuit.json"

        # Save a valid circuit first
        ctrl.save_circuit(filepath)
        original_content = filepath.read_text()

        # Now make json.dump raise mid-write
        with patch("controllers.file_controller.json.dump", side_effect=OSError("disk full")):
            with pytest.raises(OSError, match="disk full"):
                ctrl.save_circuit(filepath)

        # Original file must still be intact
        assert filepath.read_text() == original_content

    def test_save_circuit_no_temp_files_left(self, tmp_path):
        """After a successful save, no temp files should remain."""
        model = build_simple_circuit()
        ctrl = FileController(model)
        filepath = tmp_path / "circuit.json"

        ctrl.save_circuit(filepath)

        # Only the target file should exist
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        assert files[0].name == "circuit.json"

    def test_auto_save_atomic_no_corruption_on_error(self, tmp_path):
        """If auto_save fails mid-write, the previous auto-save stays intact."""
        model = build_simple_circuit()
        autosave_file = str(tmp_path / ".autosave_recovery.json")
        ctrl = FileController(model, autosave_file=autosave_file)

        # First auto-save succeeds
        ctrl.auto_save()
        original_content = Path(autosave_file).read_text()

        # Second auto-save fails mid-write — file should not be corrupted
        with patch("controllers.file_controller.json.dump", side_effect=OSError("disk full")):
            ctrl.auto_save()  # Swallows the error internally

        # Original auto-save file must still be intact
        assert Path(autosave_file).read_text() == original_content


class TestFileSizeValidation:
    """Issue #766: reject oversized files before loading."""

    def test_load_circuit_rejects_oversized_file(self, tmp_path):
        """load_circuit should raise ValueError for files exceeding MAX_FILE_SIZE."""
        from controllers.file_controller import check_file_size

        filepath = tmp_path / "huge.json"
        filepath.write_text("{}")

        # Patch getsize to report a huge file
        with patch(
            "controllers.file_controller.os.path.getsize",
            return_value=100 * 1024 * 1024,
        ):
            with pytest.raises(ValueError, match="too large"):
                check_file_size(filepath)

    def test_load_circuit_accepts_normal_file(self, tmp_path):
        """load_circuit should accept files within the size limit."""
        from controllers.file_controller import check_file_size

        filepath = tmp_path / "normal.json"
        filepath.write_text("{}")

        # Should not raise
        check_file_size(filepath)

    def test_load_circuit_error_message_includes_size(self, tmp_path):
        """Error message should include the actual and maximum file size."""
        from controllers.file_controller import check_file_size

        filepath = tmp_path / "big.json"
        filepath.write_text("{}")

        with patch("controllers.file_controller.os.path.getsize", return_value=60 * 1024 * 1024):
            with pytest.raises(ValueError, match="60.0 MB.*50 MB"):
                check_file_size(filepath)

    def test_load_circuit_with_oversized_file_preserves_model(self, tmp_path):
        """Model should remain intact when oversized file is rejected."""
        model = build_simple_circuit()
        ctrl = FileController(model)
        original_ids = set(model.components.keys())

        filepath = tmp_path / "huge.json"
        filepath.write_text('{"components": [], "wires": []}')

        with patch(
            "controllers.file_controller.os.path.getsize",
            return_value=100 * 1024 * 1024,
        ):
            with pytest.raises(ValueError, match="too large"):
                ctrl.load_circuit(filepath)

        # Original circuit must still be intact
        assert set(ctrl.model.components.keys()) == original_ids


class TestLoadFromModelClearsUndo:
    """Issue #820: load_from_model() must clear undo history."""

    def test_load_from_model_clears_undo_history(self):
        """Undo stack is empty after load_from_model()."""
        from controllers.circuit_controller import CircuitController
        from controllers.commands import AddComponentCommand

        model = CircuitModel()
        circuit_ctrl = CircuitController(model)
        file_ctrl = FileController(model, circuit_ctrl=circuit_ctrl)

        # Perform an undoable operation
        cmd = AddComponentCommand(circuit_ctrl, "Resistor", (0, 0))
        circuit_ctrl.execute_command(cmd)
        assert circuit_ctrl.can_undo()

        # Load a new model
        new_model = build_simple_circuit()
        file_ctrl.load_from_model(new_model)

        # Undo stack must be cleared
        assert not circuit_ctrl.can_undo()
        assert not circuit_ctrl.can_redo()

    def test_load_from_model_without_circuit_ctrl(self):
        """load_from_model() works without a circuit controller."""
        model = CircuitModel()
        file_ctrl = FileController(model, circuit_ctrl=None)
        new_model = build_simple_circuit()
        file_ctrl.load_from_model(new_model)
        assert len(file_ctrl.model.components) > 0
