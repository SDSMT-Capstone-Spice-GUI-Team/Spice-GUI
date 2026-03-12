"""Tests for drag-and-drop file import routing logic."""

from pathlib import Path

import pytest
from utils.drag_drop_router import EXTENSION_ROUTES, route_dropped_file


class TestRouteDroppedFile:
    """Extension routing returns the correct handler name."""

    def test_json_routes_to_load_circuit(self):
        assert route_dropped_file(".json") == "load_circuit"

    def test_asc_routes_to_import_asc(self):
        assert route_dropped_file(".asc") == "import_asc"

    def test_cir_routes_to_import_netlist(self):
        assert route_dropped_file(".cir") == "import_netlist"

    def test_spice_routes_to_import_netlist(self):
        assert route_dropped_file(".spice") == "import_netlist"

    def test_sp_routes_to_import_netlist(self):
        assert route_dropped_file(".sp") == "import_netlist"

    def test_net_routes_to_import_netlist(self):
        assert route_dropped_file(".net") == "import_netlist"

    def test_unsupported_extension_returns_none(self):
        assert route_dropped_file(".pdf") is None
        assert route_dropped_file(".txt") is None
        assert route_dropped_file(".png") is None

    def test_case_insensitive(self):
        assert route_dropped_file(".JSON") == "load_circuit"
        assert route_dropped_file(".ASC") == "import_asc"
        assert route_dropped_file(".CIR") == "import_netlist"

    def test_empty_extension_returns_none(self):
        assert route_dropped_file("") is None


class TestExtensionRoutes:
    """The EXTENSION_ROUTES mapping is complete."""

    def test_all_netlist_extensions_present(self):
        for ext in (".cir", ".spice", ".sp", ".net"):
            assert ext in EXTENSION_ROUTES

    def test_json_present(self):
        assert ".json" in EXTENSION_ROUTES

    def test_asc_present(self):
        assert ".asc" in EXTENSION_ROUTES


class TestNoQtDependencies:
    def test_no_pyqt_imports(self):
        import utils.drag_drop_router as mod

        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "PyQt" not in source
        assert "QtCore" not in source
        assert "QtWidgets" not in source
