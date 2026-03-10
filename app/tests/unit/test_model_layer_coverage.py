"""Tests closing remaining model-layer coverage gaps.

Covers missing lines in circuit_controller.py, node.py, wire.py,
keybindings.py, and recent_exports.py.
"""

import json
from unittest.mock import MagicMock

import pytest
from controllers.circuit_controller import CircuitController
from controllers.keybindings import KeybindingsRegistry
from controllers.recent_exports import SETTINGS_KEY, get_recent_exports
from controllers.settings_service import settings as app_settings
from models.node import NodeData
from models.wire import WireData

# ---------------------------------------------------------------------------
# circuit_controller.py
# ---------------------------------------------------------------------------


class TestCircuitControllerObserverError:
    """Cover lines 68-69: observer error logging."""

    def test_observer_exception_does_not_propagate(self):
        ctrl = CircuitController()

        def bad_observer(event, data):
            raise TypeError("boom")

        ctrl.add_observer(bad_observer)
        # _notify should catch the TypeError and log, not propagate
        ctrl.clear_circuit()


class TestCircuitControllerLockedComponents:
    """Cover locked-component early returns on missing components."""

    def test_set_component_rotation_locked(self):
        """Line 127: early return when component is locked."""
        ctrl = CircuitController()
        comp = ctrl.add_component("Resistor", (0.0, 0.0))
        ctrl.set_locked_components([comp.component_id])
        ctrl.set_component_rotation(comp.component_id, 180)
        assert comp.rotation == 0  # unchanged

    def test_set_component_rotation_nonexistent(self):
        """Line 130: early return when component doesn't exist."""
        ctrl = CircuitController()
        ctrl.set_component_rotation("NONEXISTENT", 90)  # should not raise

    def test_update_component_value_nonexistent(self):
        """Line 153: early return when component doesn't exist."""
        ctrl = CircuitController()
        ctrl.update_component_value("NONEXISTENT", "10k")  # should not raise

    def test_update_component_waveform_nonexistent(self):
        """Line 163: early return when component doesn't exist."""
        ctrl = CircuitController()
        ctrl.update_component_waveform("NONEXISTENT", "SINE", {})  # should not raise

    def test_update_component_waveform_initializes_params(self):
        """Line 166: waveform_params initialized to {} when None."""
        ctrl = CircuitController()
        comp = ctrl.add_component("Voltage Source", (0.0, 0.0))
        assert comp.waveform_params is None
        ctrl.update_component_waveform(comp.component_id, "SINE", {"freq": 1000})
        assert comp.waveform_params is not None
        assert "SINE" in comp.waveform_params

    def test_move_component_nonexistent(self):
        """Line 187: early return when component doesn't exist."""
        ctrl = CircuitController()
        ctrl.move_component("NONEXISTENT", (50.0, 50.0))  # should not raise


class TestCircuitControllerRecommendedComponents:
    """Cover lines 352-353: set_recommended_components."""

    def test_set_recommended_components(self):
        ctrl = CircuitController()
        recorded = []
        ctrl.add_observer(lambda event, data: recorded.append((event, data)))
        ctrl.set_recommended_components(["Resistor", "Capacitor"])
        assert ctrl.model.recommended_components == ["Resistor", "Capacitor"]
        assert recorded[-1][0] == "recommended_components_changed"


class TestCircuitControllerPasteSkipsMissingWireEndpoints:
    """Cover line 469: paste skips wire when endpoint not in id_map."""

    def test_paste_skips_wire_with_missing_endpoint(self):
        from models.clipboard import ClipboardData
        from models.component import ComponentData

        ctrl = CircuitController()
        comp = ComponentData(
            component_id="R1",
            component_type="Resistor",
            value="1k",
            position=(0, 0),
        )
        # Wire references a component not in the clipboard
        wire_dict = {
            "start_comp": "R1",
            "start_term": 0,
            "end_comp": "R_MISSING",
            "end_term": 0,
        }
        cb = ClipboardData(
            components=[comp.to_dict()],
            wires=[wire_dict],
            paste_count=0,
        )
        ctrl.set_clipboard(cb)
        new_comps, new_wires = ctrl.paste_components()
        assert len(new_comps) == 1
        assert len(new_wires) == 0  # wire skipped


class TestCircuitControllerAccessors:
    """Cover lines 559, 578, 586, 590, 598, 602."""

    def test_get_redo_description_empty(self):
        """Line 559: get_redo_description with nothing to redo."""
        ctrl = CircuitController()
        assert ctrl.get_redo_description() is None

    def test_get_component_count(self):
        """Line 578."""
        ctrl = CircuitController()
        assert ctrl.get_component_count() == 0
        ctrl.add_component("Resistor", (0, 0))
        assert ctrl.get_component_count() == 1

    def test_get_wire_count(self):
        """Line 586."""
        ctrl = CircuitController()
        assert ctrl.get_wire_count() == 0
        ctrl.add_component("Resistor", (0, 0))
        ctrl.add_component("Resistor", (100, 0))
        ctrl.add_wire("R1", 0, "R2", 0)
        assert ctrl.get_wire_count() == 1

    def test_get_nodes(self):
        """Line 590."""
        ctrl = CircuitController()
        assert ctrl.get_nodes() == []
        ctrl.add_component("Resistor", (0, 0))
        ctrl.add_component("Resistor", (100, 0))
        ctrl.add_wire("R1", 0, "R2", 0)
        nodes = ctrl.get_nodes()
        assert len(nodes) == 1
        # Returns a copy
        nodes.clear()
        assert len(ctrl.model.nodes) == 1

    def test_has_ground(self):
        """Line 598."""
        ctrl = CircuitController()
        assert ctrl.has_ground() is False
        ctrl.add_component("Ground", (0, 0))
        assert ctrl.has_ground() is True

    def test_get_terminal_to_node(self):
        """Line 602."""
        ctrl = CircuitController()
        assert ctrl.get_terminal_to_node() == {}
        ctrl.add_component("Resistor", (0, 0))
        ctrl.add_component("Resistor", (100, 0))
        ctrl.add_wire("R1", 0, "R2", 0)
        t2n = ctrl.get_terminal_to_node()
        assert ("R1", 0) in t2n
        # Returns a copy
        t2n.clear()
        assert len(ctrl.model.terminal_to_node) > 0


# ---------------------------------------------------------------------------
# node.py
# ---------------------------------------------------------------------------


class TestNodeDataCoverage:
    """Cover lines 120, 128, 188, 191-192."""

    def test_remove_terminal(self):
        """Line 120."""
        node = NodeData(auto_label="nodeA")
        node.add_terminal("R1", 0)
        assert ("R1", 0) in node.terminals
        node.remove_terminal("R1", 0)
        assert ("R1", 0) not in node.terminals

    def test_remove_terminal_nonexistent(self):
        """remove_terminal uses discard, so missing terminal is safe."""
        node = NodeData(auto_label="nodeA")
        node.remove_terminal("R1", 0)  # should not raise

    def test_remove_wire(self):
        """Line 128."""
        node = NodeData(auto_label="nodeA")
        node.add_wire(0)
        assert 0 in node.wire_indices
        node.remove_wire(0)
        assert 0 not in node.wire_indices

    def test_remove_wire_nonexistent(self):
        """remove_wire uses discard, so missing index is safe."""
        node = NodeData(auto_label="nodeA")
        node.remove_wire(99)  # should not raise

    def test_is_empty_true(self):
        """Line 188: is_empty returns True when no terminals."""
        node = NodeData(auto_label="nodeA")
        assert node.is_empty() is True

    def test_is_empty_false(self):
        node = NodeData(auto_label="nodeA")
        node.add_terminal("R1", 0)
        assert node.is_empty() is False

    def test_repr(self):
        """Lines 191-192."""
        node = NodeData(auto_label="nodeA")
        node.add_terminal("R1", 0)
        node.add_wire(0)
        r = repr(node)
        assert "nodeA" in r
        assert "terminals=1" in r
        assert "wires=1" in r


# ---------------------------------------------------------------------------
# wire.py
# ---------------------------------------------------------------------------


class TestWireDataCoverage:
    """Cover lines 39, 50, 70, 100."""

    def test_get_terminals(self):
        """Line 39."""
        wire = WireData(
            start_component_id="R1",
            start_terminal=0,
            end_component_id="R2",
            end_terminal=1,
        )
        terminals = wire.get_terminals()
        assert terminals == [("R1", 0), ("R2", 1)]

    def test_connects_terminal_start(self):
        """Line 50: connects_terminal matches start terminal."""
        wire = WireData(
            start_component_id="R1",
            start_terminal=0,
            end_component_id="R2",
            end_terminal=1,
        )
        assert wire.connects_terminal("R1", 0) is True

    def test_connects_terminal_end(self):
        """Line 50: connects_terminal matches end terminal."""
        wire = WireData(
            start_component_id="R1",
            start_terminal=0,
            end_component_id="R2",
            end_terminal=1,
        )
        assert wire.connects_terminal("R2", 1) is True

    def test_connects_terminal_false(self):
        wire = WireData(
            start_component_id="R1",
            start_terminal=0,
            end_component_id="R2",
            end_terminal=1,
        )
        assert wire.connects_terminal("R1", 1) is False
        assert wire.connects_terminal("R3", 0) is False

    def test_to_dict_locked(self):
        """Line 70: locked wire includes locked=True in dict."""
        wire = WireData(
            start_component_id="R1",
            start_terminal=0,
            end_component_id="R2",
            end_terminal=1,
            locked=True,
        )
        d = wire.to_dict()
        assert d["locked"] is True

    def test_to_dict_unlocked_no_locked_key(self):
        """Unlocked wire should not include locked key."""
        wire = WireData(
            start_component_id="R1",
            start_terminal=0,
            end_component_id="R2",
            end_terminal=1,
        )
        d = wire.to_dict()
        assert "locked" not in d

    def test_repr(self):
        """Line 100."""
        wire = WireData(
            start_component_id="R1",
            start_terminal=0,
            end_component_id="R2",
            end_terminal=1,
        )
        r = repr(wire)
        assert "R1[0]" in r
        assert "R2[1]" in r


# ---------------------------------------------------------------------------
# keybindings.py
# ---------------------------------------------------------------------------


class TestKeybindingsSaveError:
    """Cover lines 132-133: OSError during save."""

    def test_save_oserror_silenced(self, tmp_path):
        # Use a path that will fail to write
        config_path = tmp_path / "kb.json"
        reg = KeybindingsRegistry(config_path=config_path)
        reg.set("file.new", "Ctrl+Shift+N")
        # Make the config path a directory so writing fails
        config_path.mkdir(parents=True, exist_ok=True)
        # Should not raise
        reg.save()


# ---------------------------------------------------------------------------
# recent_exports.py
# ---------------------------------------------------------------------------


class TestRecentExportsNonListFallback:
    """Cover line 26: entries is not a list."""

    @pytest.fixture(autouse=True)
    def _clean(self):
        app_settings.set_json(SETTINGS_KEY, [])
        yield
        app_settings.set_json(SETTINGS_KEY, [])

    def test_non_list_entries_returns_empty(self):
        # Store a dict value (not a list) — get_json will return it as-is
        app_settings.set_json(SETTINGS_KEY, {"bad": "data"})
        result = get_recent_exports()
        assert result == []
