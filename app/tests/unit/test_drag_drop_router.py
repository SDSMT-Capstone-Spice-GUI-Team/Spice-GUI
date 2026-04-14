"""Tests for utils.drag_drop_router.route_dropped_file."""

import pytest
from utils.drag_drop_router import EXTENSION_ROUTES, route_dropped_file


class TestExtensionRoutes:
    def test_json_maps_to_load_circuit(self):
        assert EXTENSION_ROUTES[".json"] == "load_circuit"

    def test_asc_maps_to_import_asc(self):
        assert EXTENSION_ROUTES[".asc"] == "import_asc"

    def test_netlist_extensions_map_to_import_netlist(self):
        for ext in (".cir", ".spice", ".sp", ".net"):
            assert EXTENSION_ROUTES[ext] == "import_netlist"


class TestRouteDroppedFile:
    def test_json_extension(self):
        assert route_dropped_file(".json") == "load_circuit"

    def test_asc_extension(self):
        assert route_dropped_file(".asc") == "import_asc"

    def test_cir_extension(self):
        assert route_dropped_file(".cir") == "import_netlist"

    def test_spice_extension(self):
        assert route_dropped_file(".spice") == "import_netlist"

    def test_sp_extension(self):
        assert route_dropped_file(".sp") == "import_netlist"

    def test_net_extension(self):
        assert route_dropped_file(".net") == "import_netlist"

    def test_unknown_extension_returns_none(self):
        assert route_dropped_file(".xyz") is None

    def test_empty_extension_returns_none(self):
        assert route_dropped_file("") is None

    def test_case_insensitive_json(self):
        assert route_dropped_file(".JSON") == "load_circuit"

    def test_case_insensitive_asc(self):
        assert route_dropped_file(".ASC") == "import_asc"

    def test_case_insensitive_cir(self):
        assert route_dropped_file(".CIR") == "import_netlist"

    def test_mixed_case(self):
        assert route_dropped_file(".SpIcE") == "import_netlist"
