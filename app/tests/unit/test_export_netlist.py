"""Tests for netlist export to .cir file (issue #228).

Verifies that the generated netlist can be written to a file and
that the menu infrastructure exists.
"""

import inspect

import pytest
from controllers.circuit_controller import CircuitController
from controllers.simulation_controller import SimulationController
from models.circuit import CircuitModel


class TestNetlistGeneration:
    """Test that netlists can be generated from circuits."""

    def test_generate_netlist_simple_circuit(self):
        """Generate a netlist from a simple resistor circuit."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        sim = SimulationController(model, circuit_ctrl=ctrl)

        v1 = ctrl.add_component("Voltage Source", (0, 0))
        r1 = ctrl.add_component("Resistor", (100, 0))
        gnd = ctrl.add_component("Ground", (0, 100))

        ctrl.add_wire(v1.component_id, 0, r1.component_id, 0)
        ctrl.add_wire(r1.component_id, 1, gnd.component_id, 0)
        ctrl.add_wire(v1.component_id, 1, gnd.component_id, 0)

        netlist = sim.generate_netlist()
        assert isinstance(netlist, str)
        assert len(netlist) > 0

    def test_generate_netlist_contains_components(self):
        """Netlist should reference the components in the circuit."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        sim = SimulationController(model, circuit_ctrl=ctrl)

        v1 = ctrl.add_component("Voltage Source", (0, 0))
        r1 = ctrl.add_component("Resistor", (100, 0))
        gnd = ctrl.add_component("Ground", (0, 100))

        ctrl.add_wire(v1.component_id, 0, r1.component_id, 0)
        ctrl.add_wire(r1.component_id, 1, gnd.component_id, 0)
        ctrl.add_wire(v1.component_id, 1, gnd.component_id, 0)

        netlist = sim.generate_netlist()
        # Netlist should contain resistor and voltage source references
        assert "R" in netlist or "r" in netlist
        assert "V" in netlist or "v" in netlist

    def test_generate_netlist_contains_end(self):
        """SPICE netlist should end with .end directive."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        sim = SimulationController(model, circuit_ctrl=ctrl)

        v1 = ctrl.add_component("Voltage Source", (0, 0))
        gnd = ctrl.add_component("Ground", (0, 100))
        ctrl.add_wire(v1.component_id, 1, gnd.component_id, 0)

        netlist = sim.generate_netlist()
        assert ".end" in netlist.lower()


class TestNetlistFileExport:
    """Test writing netlist to file."""

    def test_write_netlist_to_file(self, tmp_path):
        """Write a generated netlist to a .cir file."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        sim = SimulationController(model, circuit_ctrl=ctrl)

        v1 = ctrl.add_component("Voltage Source", (0, 0))
        r1 = ctrl.add_component("Resistor", (100, 0))
        gnd = ctrl.add_component("Ground", (0, 100))
        ctrl.add_wire(v1.component_id, 0, r1.component_id, 0)
        ctrl.add_wire(r1.component_id, 1, gnd.component_id, 0)
        ctrl.add_wire(v1.component_id, 1, gnd.component_id, 0)

        netlist = sim.generate_netlist()

        outfile = tmp_path / "test_circuit.cir"
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(netlist)

        assert outfile.exists()
        content = outfile.read_text(encoding="utf-8")
        assert content == netlist
        assert len(content) > 0

    def test_write_netlist_utf8_encoding(self, tmp_path):
        """Netlist file should use UTF-8 encoding."""
        model = CircuitModel()
        ctrl = CircuitController(model)
        sim = SimulationController(model, circuit_ctrl=ctrl)

        ctrl.add_component("Voltage Source", (0, 0))
        gnd = ctrl.add_component("Ground", (0, 100))
        ctrl.add_wire("V1", 1, gnd.component_id, 0)

        netlist = sim.generate_netlist()

        outfile = tmp_path / "test.cir"
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(netlist)

        # Read back with explicit encoding
        content = outfile.read_text(encoding="utf-8")
        assert content == netlist


class TestExportNetlistMenuInfrastructure:
    """Verify menu and method infrastructure for netlist export."""

    def test_simulation_mixin_has_export_netlist(self):
        """SimulationMixin should have an export_netlist method."""
        from GUI.main_window_simulation import SimulationMixin

        assert hasattr(SimulationMixin, "export_netlist")

    def test_export_netlist_uses_file_dialog(self):
        """export_netlist should use QFileDialog for file selection."""
        from GUI.main_window_simulation import SimulationMixin

        source = inspect.getsource(SimulationMixin.export_netlist)
        assert "QFileDialog" in source
        assert "getSaveFileName" in source

    def test_export_netlist_writes_cir_extension(self):
        """export_netlist should default to .cir extension."""
        from GUI.main_window_simulation import SimulationMixin

        source = inspect.getsource(SimulationMixin.export_netlist)
        assert ".cir" in source

    def test_menu_has_export_netlist_action(self):
        """MenuBarMixin should include an Export Netlist action."""
        from GUI.main_window_menus import MenuBarMixin

        source = inspect.getsource(MenuBarMixin.create_menu_bar)
        assert "export_netlist" in source
        assert "Export" in source

    def test_export_handles_os_error(self):
        """export_netlist should handle OSError when writing."""
        from GUI.main_window_simulation import SimulationMixin

        source = inspect.getsource(SimulationMixin.export_netlist)
        assert "OSError" in source
