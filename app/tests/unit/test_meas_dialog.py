"""Tests for the .meas directive GUI builder (meas_dialog.py)."""

import pytest
from GUI.meas_dialog import (ANALYSIS_DOMAIN_MAP, MeasurementDialog,
                             MeasurementEntryDialog, build_directive)

# ---------------------------------------------------------------------------
# build_directive unit tests
# ---------------------------------------------------------------------------


class TestBuildDirective:
    """Test the build_directive helper for all measurement types."""

    def test_avg(self):
        d = build_directive("tran", "avg_out", "AVG", {"variable": "v(out)"})
        assert d == ".meas tran avg_out AVG v(out)"

    def test_rms_with_range(self):
        d = build_directive(
            "tran",
            "rms_out",
            "RMS",
            {"variable": "v(out)", "from_val": "1m", "to_val": "10m"},
        )
        assert d == ".meas tran rms_out RMS v(out) FROM=1m TO=10m"

    def test_min_no_range(self):
        d = build_directive("ac", "min_gain", "MIN", {"variable": "vdb(out)"})
        assert d == ".meas ac min_gain MIN vdb(out)"

    def test_max_partial_range(self):
        d = build_directive(
            "dc", "peak", "MAX", {"variable": "v(2)", "from_val": "0", "to_val": ""}
        )
        assert d == ".meas dc peak MAX v(2) FROM=0"

    def test_pp(self):
        d = build_directive("tran", "swing", "PP", {"variable": "v(out)"})
        assert d == ".meas tran swing PP v(out)"

    def test_integ(self):
        d = build_directive(
            "tran",
            "charge",
            "INTEG",
            {"variable": "i(R1)", "from_val": "0", "to_val": "5m"},
        )
        assert d == ".meas tran charge INTEG i(R1) FROM=0 TO=5m"

    def test_find_at(self):
        d = build_directive(
            "tran", "val_at_1m", "FIND_AT", {"variable": "v(out)", "at_val": "1m"}
        )
        assert d == ".meas tran val_at_1m FIND v(out) AT=1m"

    def test_find_when(self):
        d = build_directive(
            "tran",
            "crossing",
            "FIND_WHEN",
            {
                "variable": "v(out)",
                "when_var": "v(in)",
                "when_val": "0.5",
                "cross": "RISE=1",
            },
        )
        assert d == ".meas tran crossing FIND v(out) WHEN v(in)=0.5 RISE=1"

    def test_find_when_no_cross(self):
        d = build_directive(
            "tran",
            "thresh",
            "FIND_WHEN",
            {"variable": "v(out)", "when_var": "v(in)", "when_val": "2.5", "cross": ""},
        )
        assert d == ".meas tran thresh FIND v(out) WHEN v(in)=2.5"

    def test_trig_targ(self):
        d = build_directive(
            "tran",
            "rise_time",
            "TRIG_TARG",
            {
                "variable": "v(out)",
                "trig_var": "v(out)",
                "trig_val": "0.1",
                "trig_edge": "RISE=1",
                "targ_var": "v(out)",
                "targ_val": "0.9",
                "targ_edge": "RISE=1",
            },
        )
        assert (
            d
            == ".meas tran rise_time TRIG v(out) VAL=0.1 RISE=1 TARG v(out) VAL=0.9 RISE=1"
        )

    def test_domain_ac(self):
        d = build_directive("ac", "bw3db", "MAX", {"variable": "vdb(out)"})
        assert d.startswith(".meas ac")

    def test_domain_dc(self):
        d = build_directive(
            "dc", "gain", "FIND_AT", {"variable": "v(out)", "at_val": "5"}
        )
        assert d.startswith(".meas dc")


# ---------------------------------------------------------------------------
# ANALYSIS_DOMAIN_MAP tests
# ---------------------------------------------------------------------------


class TestAnalysisDomainMap:
    def test_transient_maps_to_tran(self):
        assert ANALYSIS_DOMAIN_MAP["Transient"] == "tran"

    def test_ac_sweep_maps_to_ac(self):
        assert ANALYSIS_DOMAIN_MAP["AC Sweep"] == "ac"

    def test_dc_sweep_maps_to_dc(self):
        assert ANALYSIS_DOMAIN_MAP["DC Sweep"] == "dc"


# ---------------------------------------------------------------------------
# MeasurementEntryDialog tests (qtbot)
# ---------------------------------------------------------------------------


class TestMeasurementEntryDialog:
    def test_default_data(self, qtbot):
        dialog = MeasurementEntryDialog(domain="tran")
        qtbot.addWidget(dialog)
        data = dialog.get_data()
        assert data is not None
        assert data["name"] == "meas1"
        assert data["meas_type"] == "AVG"
        assert "directive" in data
        assert data["directive"].startswith(".meas tran meas1 AVG")

    def test_empty_name_returns_none(self, qtbot):
        dialog = MeasurementEntryDialog(domain="tran")
        qtbot.addWidget(dialog)
        dialog.name_edit.setText("")
        assert dialog.get_data() is None

    def test_load_initial(self, qtbot):
        initial = {
            "name": "my_rms",
            "meas_type": "RMS",
            "params": {"variable": "v(2)", "from_val": "0", "to_val": "5m"},
        }
        dialog = MeasurementEntryDialog(domain="tran", initial=initial)
        qtbot.addWidget(dialog)
        data = dialog.get_data()
        assert data["name"] == "my_rms"
        assert data["meas_type"] == "RMS"
        assert "FROM=0" in data["directive"]
        assert "TO=5m" in data["directive"]

    def test_find_at_fields(self, qtbot):
        dialog = MeasurementEntryDialog(domain="ac")
        qtbot.addWidget(dialog)
        # Switch to FIND_AT type
        for i in range(dialog.type_combo.count()):
            if dialog.type_combo.itemData(i) == "FIND_AT":
                dialog.type_combo.setCurrentIndex(i)
                break
        dialog.name_edit.setText("val_at_1k")
        dialog.var_edit.setText("vdb(out)")
        dialog.at_edit.setText("1k")
        data = dialog.get_data()
        assert data["directive"] == ".meas ac val_at_1k FIND vdb(out) AT=1k"

    def test_trig_targ_fields(self, qtbot):
        dialog = MeasurementEntryDialog(domain="tran")
        qtbot.addWidget(dialog)
        # Switch to TRIG_TARG
        for i in range(dialog.type_combo.count()):
            if dialog.type_combo.itemData(i) == "TRIG_TARG":
                dialog.type_combo.setCurrentIndex(i)
                break
        dialog.name_edit.setText("delay")
        data = dialog.get_data()
        assert data["meas_type"] == "TRIG_TARG"
        assert "TRIG" in data["directive"]
        assert "TARG" in data["directive"]


# ---------------------------------------------------------------------------
# MeasurementDialog tests (qtbot)
# ---------------------------------------------------------------------------


class TestMeasurementDialog:
    def test_empty_dialog(self, qtbot):
        dialog = MeasurementDialog(domain="tran")
        qtbot.addWidget(dialog)
        assert dialog.get_directives() == []
        assert dialog.get_entries() == []

    def test_prepopulated(self, qtbot):
        entries = [
            {
                "name": "m1",
                "meas_type": "AVG",
                "params": {"variable": "v(out)"},
                "directive": ".meas tran m1 AVG v(out)",
            },
            {
                "name": "m2",
                "meas_type": "MAX",
                "params": {"variable": "v(out)"},
                "directive": ".meas tran m2 MAX v(out)",
            },
        ]
        dialog = MeasurementDialog(domain="tran", measurements=entries)
        qtbot.addWidget(dialog)
        assert len(dialog.get_directives()) == 2
        assert dialog.table.rowCount() == 2

    def test_remove_measurement(self, qtbot):
        entries = [
            {
                "name": "m1",
                "meas_type": "AVG",
                "params": {"variable": "v(out)"},
                "directive": ".meas tran m1 AVG v(out)",
            },
        ]
        dialog = MeasurementDialog(domain="tran", measurements=entries)
        qtbot.addWidget(dialog)
        dialog.table.selectRow(0)
        dialog._remove_measurement()
        assert dialog.get_directives() == []
        assert dialog.table.rowCount() == 0


# ---------------------------------------------------------------------------
# AnalysisDialog integration tests
# ---------------------------------------------------------------------------


class TestAnalysisDialogMeasIntegration:
    """Test that measurements are included in AnalysisDialog.get_parameters()."""

    def test_meas_button_visible_for_transient(self, qtbot):
        from GUI.analysis_dialog import AnalysisDialog

        dialog = AnalysisDialog("Transient")
        qtbot.addWidget(dialog)
        assert not dialog.meas_btn.isHidden()

    def test_meas_button_visible_for_ac(self, qtbot):
        from GUI.analysis_dialog import AnalysisDialog

        dialog = AnalysisDialog("AC Sweep")
        qtbot.addWidget(dialog)
        assert not dialog.meas_btn.isHidden()

    def test_meas_button_visible_for_dc_sweep(self, qtbot):
        from GUI.analysis_dialog import AnalysisDialog

        dialog = AnalysisDialog("DC Sweep")
        qtbot.addWidget(dialog)
        assert not dialog.meas_btn.isHidden()

    def test_meas_button_hidden_for_op(self, qtbot):
        from GUI.analysis_dialog import AnalysisDialog

        dialog = AnalysisDialog("DC Operating Point")
        qtbot.addWidget(dialog)
        assert dialog.meas_btn.isHidden()

    def test_meas_button_hidden_for_sensitivity(self, qtbot):
        from GUI.analysis_dialog import AnalysisDialog

        dialog = AnalysisDialog("Sensitivity")
        qtbot.addWidget(dialog)
        assert dialog.meas_btn.isHidden()

    def test_params_include_measurements(self, qtbot):
        from GUI.analysis_dialog import AnalysisDialog

        dialog = AnalysisDialog("Transient")
        qtbot.addWidget(dialog)
        dialog._measurements = [
            {
                "name": "m1",
                "meas_type": "AVG",
                "params": {"variable": "v(out)"},
                "directive": ".meas tran m1 AVG v(out)",
            },
        ]
        params = dialog.get_parameters()
        assert params is not None
        assert "measurements" in params
        assert params["measurements"] == [".meas tran m1 AVG v(out)"]

    def test_params_no_measurements_key_when_empty(self, qtbot):
        from GUI.analysis_dialog import AnalysisDialog

        dialog = AnalysisDialog("Transient")
        qtbot.addWidget(dialog)
        params = dialog.get_parameters()
        assert params is not None
        assert "measurements" not in params

    def test_meas_label_updates(self, qtbot):
        from GUI.analysis_dialog import AnalysisDialog

        dialog = AnalysisDialog("Transient")
        qtbot.addWidget(dialog)
        assert "No measurements" in dialog.meas_label.text()

        dialog._measurements = [
            {
                "name": "m1",
                "meas_type": "AVG",
                "params": {},
                "directive": ".meas tran m1 AVG v(out)",
            },
        ]
        dialog._update_meas_label()
        assert "1 measurement" in dialog.meas_label.text()

        dialog._measurements.append(
            {
                "name": "m2",
                "meas_type": "MAX",
                "params": {},
                "directive": ".meas tran m2 MAX v(out)",
            },
        )
        dialog._update_meas_label()
        assert "2 measurements" in dialog.meas_label.text()
