"""Tests to increase file_controller.py coverage to 95%+.

Covers:
- load_from_model with and without circuit_ctrl (lines 78-80)
- save_circuit / load_circuit circuit_ctrl notifications (lines 108, 139)
- load_from_dict circuit_ctrl notification (line 151)
- _save_session OSError branch (lines 168-169)
- load_last_session OSError branch (lines 187-188)
- auto_save file writing (lines 249-250)
- auto_save OSError/TypeError branch (lines 251-252)
- has_auto_save (line 256)
- load_auto_save source_path + circuit_ctrl (lines 277, 280)
- load_auto_save failure branch (lines 283-285)
- import_netlist circuit_ctrl notification (line 317)
- import_asc analysis + circuit_ctrl (lines 345-346, 354)
- import_circuitikz full body (lines 379-390)
- clear_auto_save try block (lines 423-424)
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from controllers.file_controller import FileController
from models.circuit import CircuitModel
from tests.conftest import build_simple_circuit


class TestLoadFromModel:
    """Cover lines 78-80: load_from_model body + circuit_ctrl notification."""

    def test_load_from_model_replaces_data(self):
        """load_from_model should replace the model data in place."""
        ctrl = FileController(CircuitModel())
        new_model = build_simple_circuit()
        ctrl.load_from_model(new_model)
        assert "V1" in ctrl.model.components
        assert "R1" in ctrl.model.components

    def test_load_from_model_notifies_circuit_ctrl(self):
        """load_from_model should notify circuit_ctrl when present."""
        mock_ctrl = MagicMock()
        ctrl = FileController(CircuitModel(), circuit_ctrl=mock_ctrl)
        new_model = build_simple_circuit()
        ctrl.load_from_model(new_model)
        mock_ctrl.notify.assert_called_once_with("model_loaded", None)

    def test_load_from_model_without_circuit_ctrl(self):
        """load_from_model should work without circuit_ctrl."""
        ctrl = FileController(CircuitModel())
        new_model = build_simple_circuit()
        ctrl.load_from_model(new_model)
        assert "V1" in ctrl.model.components


class TestCircuitCtrlNotifications:
    """Cover lines 108, 139: save/load circuit_ctrl notifications."""

    @patch("controllers.file_controller.settings")
    def test_save_circuit_notifies_circuit_ctrl(self, mock_settings, tmp_path):
        """save_circuit should notify circuit_ctrl with 'model_saved'."""
        mock_settings.get_list.return_value = []
        mock_ctrl = MagicMock()
        model = build_simple_circuit()
        ctrl = FileController(model, circuit_ctrl=mock_ctrl)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)
        mock_ctrl.notify.assert_called_with("model_saved", None)

    @patch("controllers.file_controller.settings")
    def test_load_circuit_notifies_circuit_ctrl(self, mock_settings, tmp_path):
        """load_circuit should notify circuit_ctrl with 'model_loaded'."""
        mock_settings.get_list.return_value = []
        model = build_simple_circuit()
        ctrl = FileController(model)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)

        mock_ctrl = MagicMock()
        ctrl2 = FileController(circuit_ctrl=mock_ctrl)
        ctrl2.load_circuit(filepath)
        mock_ctrl.notify.assert_called_with("model_loaded", None)


class TestSaveSessionOSError:
    """Cover lines 168-169: _save_session OSError branch."""

    def test_save_session_oserror_is_logged(self, tmp_path):
        """_save_session should log a warning on OSError, not raise."""
        # Use a session file path in a non-existent directory
        session_file = str(tmp_path / "nonexistent_dir" / "deep" / "session.txt")
        ctrl = FileController(
            build_simple_circuit(),
            session_file=session_file,
        )
        ctrl.current_file = Path("/some/file.json")
        # Should not raise
        ctrl._save_session()

    @patch("controllers.file_controller.settings")
    def test_save_circuit_survives_session_oserror(self, mock_settings, tmp_path):
        """save_circuit should not fail if session file write raises OSError."""
        mock_settings.get_list.return_value = []
        session_file = str(tmp_path / "no_dir" / "session.txt")
        model = build_simple_circuit()
        filepath = tmp_path / "test.json"
        ctrl = FileController(model, session_file=session_file)
        # Should not raise despite session file being unwritable
        ctrl.save_circuit(filepath)
        assert filepath.exists()


class TestAutoSaveWriting:
    """Cover lines 249-250: auto_save writing to file."""

    def test_auto_save_writes_file(self, tmp_path):
        """auto_save should write model data to the autosave file."""
        autosave_file = str(tmp_path / ".autosave_recovery.json")
        model = build_simple_circuit()
        ctrl = FileController(model, autosave_file=autosave_file)
        ctrl.auto_save()
        autosave_path = ctrl._autosave_file
        assert autosave_path.exists()
        data = json.loads(autosave_path.read_text())
        assert "components" in data
        assert "_autosave_source" in data

    def test_auto_save_includes_source_path(self, tmp_path):
        """auto_save should store the current_file as _autosave_source."""
        autosave_file = str(tmp_path / ".autosave_recovery.json")
        model = build_simple_circuit()
        ctrl = FileController(model, autosave_file=autosave_file)
        source = tmp_path / "circuit.json"
        ctrl.current_file = source
        ctrl.auto_save()
        data = json.loads(ctrl._autosave_file.read_text())
        assert data["_autosave_source"] == str(source)

    def test_auto_save_empty_source_when_no_current_file(self, tmp_path):
        """auto_save should store empty string when no current_file."""
        autosave_file = str(tmp_path / ".autosave_recovery.json")
        model = build_simple_circuit()
        ctrl = FileController(model, autosave_file=autosave_file)
        ctrl.auto_save()
        data = json.loads(ctrl._autosave_file.read_text())
        assert data["_autosave_source"] == ""


class TestClearAutoSave:
    """Cover lines 423-424: clear_auto_save try block."""

    def test_clear_auto_save_deletes_file(self, tmp_path):
        """clear_auto_save should delete the autosave file."""
        autosave_file = str(tmp_path / ".autosave_recovery.json")
        model = build_simple_circuit()
        ctrl = FileController(model, autosave_file=autosave_file)
        ctrl.auto_save()
        assert ctrl._autosave_file.exists()
        ctrl.clear_auto_save()
        assert not ctrl._autosave_file.exists()

    def test_clear_auto_save_no_file_exists(self, tmp_path):
        """clear_auto_save should not raise when file doesn't exist."""
        autosave_file = str(tmp_path / ".autosave_recovery.json")
        ctrl = FileController(autosave_file=autosave_file)
        # Should not raise
        ctrl.clear_auto_save()

    def test_clear_auto_save_oserror_is_logged(self, tmp_path):
        """clear_auto_save should log a warning on OSError, not raise."""
        autosave_file = str(tmp_path / ".autosave_recovery.json")
        ctrl = FileController(autosave_file=autosave_file)
        with patch("pathlib.Path.unlink", side_effect=OSError("perm")):
            # Should not raise
            ctrl.clear_auto_save()


class TestImportNetlistCtrlNotification:
    """Cover line 317: import_netlist circuit_ctrl notification."""

    @patch("controllers.file_controller.settings")
    def test_import_netlist_notifies_circuit_ctrl(self, mock_settings, tmp_path):
        """import_netlist should notify circuit_ctrl with 'model_loaded'."""
        mock_settings.get_list.return_value = []
        mock_ctrl = MagicMock()
        netlist = tmp_path / "circuit.cir"
        netlist.write_text("Test Circuit\nV1 1 0 DC 5V\nR1 1 0 1k\n.op\n.end\n")
        ctrl = FileController(CircuitModel(), circuit_ctrl=mock_ctrl)
        ctrl.import_netlist(netlist)
        mock_ctrl.notify.assert_called_with("model_loaded", None)


class TestImportAscAnalysisAndNotification:
    """Cover lines 345-346 (analysis branch) and 354 (circuit_ctrl notification)."""

    @patch("controllers.file_controller.settings")
    def test_import_asc_with_analysis_sets_params(self, mock_settings, tmp_path):
        """import_asc should set analysis_type and analysis_params when present."""
        mock_settings.get_list.return_value = []
        asc = tmp_path / "circuit.asc"
        # Include a .tran directive so the parser extracts analysis info
        asc.write_text(
            "Version 4\nSHEET 1 880 680\n"
            "SYMBOL res 160 128 R0\n"
            "SYMATTR InstName R1\nSYMATTR Value 1k\n"
            "SYMBOL voltage 48 128 R0\n"
            "SYMATTR InstName V1\nSYMATTR Value 5\n"
            "WIRE 160 128 48 128\n"
            "TEXT -32 300 Left 2 !.tran 1m\n"
        )
        ctrl = FileController(CircuitModel())
        ctrl.import_asc(asc)
        assert ctrl.model.analysis_type == "Transient"

    @patch("controllers.file_controller.settings")
    def test_import_asc_notifies_circuit_ctrl(self, mock_settings, tmp_path):
        """import_asc should notify circuit_ctrl with 'model_loaded'."""
        mock_settings.get_list.return_value = []
        mock_ctrl = MagicMock()
        asc = tmp_path / "circuit.asc"
        asc.write_text(
            "Version 4\nSHEET 1 880 680\n"
            "SYMBOL res 160 128 R0\n"
            "SYMATTR InstName R1\nSYMATTR Value 1k\n"
            "SYMBOL voltage 48 128 R0\n"
            "SYMATTR InstName V1\nSYMATTR Value 5\n"
            "WIRE 160 128 48 128\n"
        )
        ctrl = FileController(CircuitModel(), circuit_ctrl=mock_ctrl)
        ctrl.import_asc(asc)
        mock_ctrl.notify.assert_called_with("model_loaded", None)


class TestImportCircuitikzCoverage:
    """Cover lines 379-390: import_circuitikz full body."""

    @patch("controllers.file_controller.settings")
    def test_import_circuitikz_populates_model(self, mock_settings, tmp_path):
        """import_circuitikz should parse a .tex file and populate the model."""
        mock_settings.get_list.return_value = []
        tex = tmp_path / "circuit.tex"
        tex.write_text("\\begin{circuitikz}\n\\draw (0,0) to[R, l=$R_1$] (2,0);\n\\end{circuitikz}\n")
        ctrl = FileController(CircuitModel())
        warnings = ctrl.import_circuitikz(tex)
        assert isinstance(warnings, list)
        assert ctrl.current_file is None

    @patch("controllers.file_controller.settings")
    def test_import_circuitikz_notifies_circuit_ctrl(self, mock_settings, tmp_path):
        """import_circuitikz should notify circuit_ctrl with 'model_loaded'."""
        mock_settings.get_list.return_value = []
        mock_ctrl = MagicMock()
        tex = tmp_path / "circuit.tex"
        tex.write_text("\\begin{circuitikz}\n\\draw (0,0) to[R, l=$R_1$] (2,0);\n\\end{circuitikz}\n")
        ctrl = FileController(CircuitModel(), circuit_ctrl=mock_ctrl)
        ctrl.import_circuitikz(tex)
        mock_ctrl.notify.assert_called_with("model_loaded", None)

    @patch("controllers.file_controller.settings")
    def test_import_circuitikz_adds_to_recent(self, mock_settings, tmp_path):
        """import_circuitikz should add the file to recent files."""
        mock_settings.get_list.return_value = []
        tex = tmp_path / "circuit.tex"
        tex.write_text("\\begin{circuitikz}\n\\draw (0,0) to[R, l=$R_1$] (2,0);\n\\end{circuitikz}\n")
        ctrl = FileController(CircuitModel())
        ctrl.import_circuitikz(tex)
        calls = [call[0][0] for call in mock_settings.set.call_args_list]
        assert "file/recent_files" in calls


class TestLoadFromDictCtrlNotification:
    """Cover line 151: load_from_dict circuit_ctrl notification."""

    def test_load_from_dict_notifies_circuit_ctrl(self):
        """load_from_dict should notify circuit_ctrl with 'model_loaded'."""
        mock_ctrl = MagicMock()
        model = build_simple_circuit()
        ctrl = FileController(model, circuit_ctrl=mock_ctrl)
        data = model.to_dict()
        ctrl.load_from_dict(data)
        mock_ctrl.notify.assert_called_with("model_loaded", None)


class TestLoadLastSessionOSError:
    """Cover lines 187-188: load_last_session OSError branch."""

    def test_load_last_session_oserror_returns_none(self, tmp_path):
        """load_last_session should return None on OSError, not raise."""
        session_file = str(tmp_path / "session.txt")
        # Create the session file so os.path.exists returns True
        Path(session_file).write_text("/some/path")
        ctrl = FileController(session_file=session_file)
        with patch("builtins.open", side_effect=OSError("disk error")):
            result = ctrl.load_last_session()
        assert result is None


class TestAutoSaveErrorBranch:
    """Cover lines 251-252: auto_save OSError/TypeError branch."""

    def test_auto_save_oserror_is_logged(self, tmp_path):
        """auto_save should log a warning on OSError, not raise."""
        autosave_file = str(tmp_path / ".autosave_recovery.json")
        model = build_simple_circuit()
        ctrl = FileController(model, autosave_file=autosave_file)
        with patch("builtins.open", side_effect=OSError("disk full")):
            # Should not raise
            ctrl.auto_save()


class TestHasAutoSave:
    """Cover line 256: has_auto_save."""

    def test_has_auto_save_true(self, tmp_path):
        """has_auto_save should return True when file exists."""
        autosave_file = str(tmp_path / ".autosave_recovery.json")
        model = build_simple_circuit()
        ctrl = FileController(model, autosave_file=autosave_file)
        ctrl.auto_save()
        assert ctrl.has_auto_save() is True

    def test_has_auto_save_false(self, tmp_path):
        """has_auto_save should return False when file doesn't exist."""
        autosave_file = str(tmp_path / ".autosave_recovery.json")
        ctrl = FileController(autosave_file=autosave_file)
        assert ctrl.has_auto_save() is False


class TestLoadAutoSaveBranches:
    """Cover lines 277, 280, 283-285: load_auto_save branches."""

    def test_load_auto_save_restores_source_path(self, tmp_path):
        """load_auto_save should restore current_file from _autosave_source."""
        autosave_file = str(tmp_path / ".autosave_recovery.json")
        model = build_simple_circuit()
        ctrl = FileController(model, autosave_file=autosave_file)
        original_path = tmp_path / "circuit.json"
        ctrl.current_file = original_path
        ctrl.auto_save()

        ctrl2 = FileController(autosave_file=autosave_file)
        source = ctrl2.load_auto_save()
        assert source == str(original_path)
        assert ctrl2.current_file == original_path

    def test_load_auto_save_notifies_circuit_ctrl(self, tmp_path):
        """load_auto_save should notify circuit_ctrl with 'model_loaded'."""
        autosave_file = str(tmp_path / ".autosave_recovery.json")
        model = build_simple_circuit()
        ctrl = FileController(model, autosave_file=autosave_file)
        ctrl.auto_save()

        mock_ctrl = MagicMock()
        ctrl2 = FileController(autosave_file=autosave_file, circuit_ctrl=mock_ctrl)
        ctrl2.load_auto_save()
        mock_ctrl.notify.assert_called_with("model_loaded", None)

    def test_load_auto_save_returns_none_on_oserror(self, tmp_path):
        """load_auto_save should return None on OSError."""
        autosave_file = str(tmp_path / ".autosave_recovery.json")
        ctrl = FileController(autosave_file=autosave_file)
        with patch("builtins.open", side_effect=OSError("disk error")):
            result = ctrl.load_auto_save()
        assert result is None

    def test_load_auto_save_returns_none_on_invalid_json(self, tmp_path):
        """load_auto_save should return None on JSONDecodeError."""
        autosave_file = str(tmp_path / ".autosave_recovery.json")
        ctrl = FileController(autosave_file=autosave_file)
        ctrl._autosave_file.write_text("not valid json{{{")
        result = ctrl.load_auto_save()
        assert result is None
