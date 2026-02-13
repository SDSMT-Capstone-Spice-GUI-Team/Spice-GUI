"""Tests for copy/paste/cut functionality in CircuitController."""

import pytest
from controllers.circuit_controller import CircuitController
from controllers.commands import PasteCommand
from models.clipboard import ClipboardData
from models.component import COMPONENT_TYPES, DEFAULT_VALUES, SPICE_SYMBOLS


@pytest.fixture
def controller():
    return CircuitController()


@pytest.fixture
def events():
    recorded = []

    def callback(event, data):
        recorded.append((event, data))

    return recorded, callback


@pytest.fixture
def two_resistor_circuit(controller):
    """Create a circuit with R1-R2 connected by a wire."""
    controller.add_component("Resistor", (0.0, 0.0))
    controller.add_component("Resistor", (100.0, 0.0))
    controller.add_wire("R1", 1, "R2", 0)
    return controller


class TestClipboardData:
    def test_empty_clipboard(self):
        cb = ClipboardData()
        assert cb.is_empty()
        assert cb.paste_count == 0

    def test_non_empty_clipboard(self):
        cb = ClipboardData(components=[{"id": "R1"}])
        assert not cb.is_empty()


class TestCopyComponents:
    def test_copy_single_component(self, controller):
        controller.add_component("Resistor", (50.0, 50.0))
        result = controller.copy_components(["R1"])
        assert result is True
        assert controller.has_clipboard_content()

    def test_copy_empty_list_returns_false(self, controller):
        result = controller.copy_components([])
        assert result is False

    def test_copy_nonexistent_id_returns_false(self, controller):
        result = controller.copy_components(["R999"])
        assert result is False

    def test_copy_preserves_component_data(self, controller):
        controller.add_component("Resistor", (50.0, 75.0))
        controller.update_component_value("R1", "10k")
        controller.rotate_component("R1")
        controller.copy_components(["R1"])
        assert len(controller._clipboard.components) == 1
        comp = controller._clipboard.components[0]
        assert comp["value"] == "10k"
        assert comp["rotation"] == 90

    def test_copy_multiple_components(self, two_resistor_circuit):
        ctrl = two_resistor_circuit
        result = ctrl.copy_components(["R1", "R2"])
        assert result is True
        assert len(ctrl._clipboard.components) == 2

    def test_copy_includes_internal_wires(self, two_resistor_circuit):
        ctrl = two_resistor_circuit
        ctrl.copy_components(["R1", "R2"])
        assert len(ctrl._clipboard.wires) == 1
        wire = ctrl._clipboard.wires[0]
        assert wire["start_comp"] == "R1"
        assert wire["end_comp"] == "R2"

    def test_copy_excludes_external_wires(self, two_resistor_circuit):
        ctrl = two_resistor_circuit
        # Only copy R1 -- the wire to R2 should NOT be included
        ctrl.copy_components(["R1"])
        assert len(ctrl._clipboard.wires) == 0

    def test_copy_resets_paste_count(self, controller):
        controller.add_component("Resistor", (0.0, 0.0))
        controller.copy_components(["R1"])
        controller.paste_components()
        assert controller._clipboard.paste_count == 1
        # Copy again should reset
        controller.copy_components(["R1"])
        assert controller._clipboard.paste_count == 0


class TestPasteComponents:
    def test_paste_empty_clipboard(self, controller):
        new_comps, new_wires = controller.paste_components()
        assert new_comps == []
        assert new_wires == []

    def test_paste_creates_new_ids(self, controller):
        controller.add_component("Resistor", (0.0, 0.0))
        controller.copy_components(["R1"])
        new_comps, _ = controller.paste_components()
        assert len(new_comps) == 1
        assert new_comps[0].component_id == "R2"
        assert new_comps[0].component_id != "R1"

    def test_paste_offsets_position(self, controller):
        controller.add_component("Resistor", (100.0, 200.0))
        controller.copy_components(["R1"])
        new_comps, _ = controller.paste_components()
        assert new_comps[0].position == (140.0, 240.0)

    def test_paste_multiple_times_increments_offset(self, controller):
        controller.add_component("Resistor", (100.0, 100.0))
        controller.copy_components(["R1"])

        comps1, _ = controller.paste_components()
        assert comps1[0].position == (140.0, 140.0)

        comps2, _ = controller.paste_components()
        assert comps2[0].position == (180.0, 180.0)
        assert comps2[0].component_id == "R3"

    def test_paste_preserves_rotation_and_value(self, controller):
        controller.add_component("Resistor", (0.0, 0.0))
        controller.update_component_value("R1", "4.7k")
        controller.rotate_component("R1")  # 90 degrees
        controller.copy_components(["R1"])
        new_comps, _ = controller.paste_components()
        assert new_comps[0].value == "4.7k"
        assert new_comps[0].rotation == 90

    def test_paste_remaps_wire_ids(self, two_resistor_circuit):
        ctrl = two_resistor_circuit
        ctrl.copy_components(["R1", "R2"])
        new_comps, new_wires = ctrl.paste_components()
        assert len(new_wires) == 1
        wire = new_wires[0]
        new_ids = {c.component_id for c in new_comps}
        assert wire.start_component_id in new_ids
        assert wire.end_component_id in new_ids
        # Old IDs should NOT appear
        assert wire.start_component_id not in {"R1", "R2"}
        assert wire.end_component_id not in {"R1", "R2"}

    def test_paste_fires_observer_events(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.copy_components(["R1"])
        controller.add_observer(callback)
        controller.paste_components()
        comp_events = [e for e in recorded if e[0] == "component_added"]
        assert len(comp_events) == 1

    def test_paste_adds_to_model(self, controller):
        controller.add_component("Resistor", (0.0, 0.0))
        controller.copy_components(["R1"])
        controller.paste_components()
        assert "R1" in controller.model.components
        assert "R2" in controller.model.components
        assert len(controller.model.components) == 2

    def test_paste_waveform_source(self, controller):
        controller.add_component("Waveform Source", (0.0, 0.0))
        controller.copy_components(["VW1"])
        new_comps, _ = controller.paste_components()
        assert new_comps[0].component_type == "Waveform Source"
        assert new_comps[0].waveform_type is not None

    def test_paste_multiple_components_with_wire(self, two_resistor_circuit):
        ctrl = two_resistor_circuit
        ctrl.copy_components(["R1", "R2"])
        new_comps, new_wires = ctrl.paste_components()
        assert len(new_comps) == 2
        assert len(new_wires) == 1
        # Verify model has all 4 components and 2 wires
        assert len(ctrl.model.components) == 4
        assert len(ctrl.model.wires) == 2


class TestCutComponents:
    def test_cut_copies_and_deletes(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_observer(callback)
        result = controller.cut_components(["R1"])
        assert result is True
        assert controller.has_clipboard_content()
        assert "R1" not in controller.model.components
        assert ("component_removed", "R1") in recorded

    def test_cut_then_paste(self, controller):
        controller.add_component("Resistor", (50.0, 50.0))
        controller.cut_components(["R1"])
        assert len(controller.model.components) == 0
        new_comps, _ = controller.paste_components()
        assert len(new_comps) == 1
        assert len(controller.model.components) == 1

    def test_cut_empty_list(self, controller):
        assert controller.cut_components([]) is False

    def test_cut_removes_wires_too(self, two_resistor_circuit):
        ctrl = two_resistor_circuit
        ctrl.cut_components(["R1"])
        assert "R1" not in ctrl.model.components
        assert "R2" in ctrl.model.components
        # Wire connecting R1 to R2 should be removed
        assert len(ctrl.model.wires) == 0


class TestNoQtDependencies:
    def test_clipboard_no_pyqt(self):
        import models.clipboard as mod

        source = open(mod.__file__).read()
        assert "PyQt" not in source
        assert "QtCore" not in source

    def test_controller_no_pyqt(self):
        import controllers.circuit_controller as mod

        source = open(mod.__file__).read()
        assert "PyQt" not in source
        assert "QtCore" not in source


# ---------------------------------------------------------------------------
# Round-trip tests (issue #358)
# ---------------------------------------------------------------------------


class TestRoundTripAllComponentTypes:
    """Parametrized copy-paste round-trip across every component type."""

    @pytest.mark.parametrize("comp_type", COMPONENT_TYPES)
    def test_copy_paste_round_trip(self, comp_type):
        """Copy a single component, paste it, and verify data integrity."""
        ctrl = CircuitController()
        original = ctrl.add_component(comp_type, (50.0, 75.0))
        original_id = original.component_id

        assert ctrl.copy_components([original_id]) is True
        new_comps, _ = ctrl.paste_components()

        assert len(new_comps) == 1
        pasted = new_comps[0]

        # New ID must differ from the original
        assert pasted.component_id != original_id

        # Component type and default value must survive the round-trip
        assert pasted.component_type == comp_type
        assert pasted.value == DEFAULT_VALUES.get(comp_type, "1")

        # Position must be offset
        assert pasted.position == (90.0, 115.0)

        # Model should hold both the original and the pasted copy
        assert original_id in ctrl.model.components
        assert pasted.component_id in ctrl.model.components

    @pytest.mark.parametrize("comp_type", COMPONENT_TYPES)
    def test_cut_paste_round_trip(self, comp_type):
        """Cut a component, paste it back, and verify the model is consistent."""
        ctrl = CircuitController()
        original = ctrl.add_component(comp_type, (10.0, 20.0))
        original_id = original.component_id

        assert ctrl.cut_components([original_id]) is True
        assert original_id not in ctrl.model.components
        assert len(ctrl.model.components) == 0

        new_comps, _ = ctrl.paste_components()
        assert len(new_comps) == 1
        assert new_comps[0].component_type == comp_type
        assert len(ctrl.model.components) == 1


class TestSharedSpiceSymbolCounters:
    """Components that share a SPICE symbol (e.g. BJT NPN / PNP share 'Q')."""

    def test_bjt_npn_then_pnp_counter(self, controller):
        """Adding NPN then PNP should share the Q counter."""
        npn = controller.add_component("BJT NPN", (0.0, 0.0))
        pnp = controller.add_component("BJT PNP", (100.0, 0.0))
        assert npn.component_id == "Q1"
        assert pnp.component_id == "Q2"

    def test_paste_shared_symbol_increments_counter(self, controller):
        """Pasting a BJT NPN when Q2 already exists should produce Q3."""
        controller.add_component("BJT NPN", (0.0, 0.0))  # Q1
        controller.add_component("BJT PNP", (100.0, 0.0))  # Q2
        controller.copy_components(["Q1"])
        new_comps, _ = controller.paste_components()
        assert new_comps[0].component_id == "Q3"

    def test_diode_led_zener_share_d_counter(self, controller):
        """Diode, LED, and Zener Diode all use the 'D' symbol."""
        d1 = controller.add_component("Diode", (0.0, 0.0))
        d2 = controller.add_component("LED", (100.0, 0.0))
        d3 = controller.add_component("Zener Diode", (200.0, 0.0))
        assert d1.component_id == "D1"
        assert d2.component_id == "D2"
        assert d3.component_id == "D3"

        controller.copy_components(["D1"])
        new_comps, _ = controller.paste_components()
        assert new_comps[0].component_id == "D4"

    def test_mosfet_nmos_pmos_share_m_counter(self, controller):
        """MOSFET NMOS and PMOS share the 'M' symbol."""
        m1 = controller.add_component("MOSFET NMOS", (0.0, 0.0))
        m2 = controller.add_component("MOSFET PMOS", (100.0, 0.0))
        assert m1.component_id == "M1"
        assert m2.component_id == "M2"


class TestFlipPreservation:
    """Verify that flip_h and flip_v survive copy-paste round-trips."""

    def test_paste_preserves_flip_h(self, controller):
        controller.add_component("Resistor", (0.0, 0.0))
        controller.flip_component("R1", horizontal=True)
        assert controller.model.components["R1"].flip_h is True

        controller.copy_components(["R1"])
        new_comps, _ = controller.paste_components()
        assert new_comps[0].flip_h is True
        assert new_comps[0].flip_v is False

    def test_paste_preserves_flip_v(self, controller):
        controller.add_component("Capacitor", (0.0, 0.0))
        controller.flip_component("C1", horizontal=False)
        assert controller.model.components["C1"].flip_v is True

        controller.copy_components(["C1"])
        new_comps, _ = controller.paste_components()
        assert new_comps[0].flip_v is True
        assert new_comps[0].flip_h is False

    def test_paste_preserves_both_flips(self, controller):
        controller.add_component("Inductor", (0.0, 0.0))
        controller.flip_component("L1", horizontal=True)
        controller.flip_component("L1", horizontal=False)

        controller.copy_components(["L1"])
        new_comps, _ = controller.paste_components()
        assert new_comps[0].flip_h is True
        assert new_comps[0].flip_v is True


class TestRotationFlipTransformState:
    """Rotation + flip combinations must survive the round-trip."""

    def test_rotation_270_flip_h(self, controller):
        controller.add_component("Voltage Source", (0.0, 0.0))
        for _ in range(3):
            controller.rotate_component("V1")
        controller.flip_component("V1", horizontal=True)

        controller.copy_components(["V1"])
        new_comps, _ = controller.paste_components()
        assert new_comps[0].rotation == 270
        assert new_comps[0].flip_h is True
        assert new_comps[0].flip_v is False

    def test_rotation_180_flip_v(self, controller):
        controller.add_component("Current Source", (0.0, 0.0))
        controller.rotate_component("I1")
        controller.rotate_component("I1")
        controller.flip_component("I1", horizontal=False)

        controller.copy_components(["I1"])
        new_comps, _ = controller.paste_components()
        assert new_comps[0].rotation == 180
        assert new_comps[0].flip_v is True


class TestInitialConditionPreservation:
    """initial_condition field must survive copy-paste round-trip."""

    def test_capacitor_initial_condition(self, controller):
        controller.add_component("Capacitor", (0.0, 0.0))
        controller.model.components["C1"].initial_condition = "2.5V"

        controller.copy_components(["C1"])
        new_comps, _ = controller.paste_components()
        assert new_comps[0].initial_condition == "2.5V"

    def test_inductor_initial_condition(self, controller):
        controller.add_component("Inductor", (0.0, 0.0))
        controller.model.components["L1"].initial_condition = "100mA"

        controller.copy_components(["L1"])
        new_comps, _ = controller.paste_components()
        assert new_comps[0].initial_condition == "100mA"

    def test_no_initial_condition_stays_none(self, controller):
        controller.add_component("Resistor", (0.0, 0.0))
        controller.copy_components(["R1"])
        new_comps, _ = controller.paste_components()
        assert new_comps[0].initial_condition is None


class TestWaveformSourceDeepCopy:
    """Waveform source waveform_params must be deep-copied, not shared."""

    def test_waveform_params_independent_after_paste(self, controller):
        controller.add_component("Waveform Source", (0.0, 0.0))
        original = controller.model.components["VW1"]
        original.waveform_params["SIN"]["amplitude"] = "10"

        controller.copy_components(["VW1"])
        new_comps, _ = controller.paste_components()
        pasted = new_comps[0]

        # Mutating the pasted copy must not affect the original
        pasted.waveform_params["SIN"]["amplitude"] = "99"
        assert original.waveform_params["SIN"]["amplitude"] == "10"

    def test_waveform_type_preserved(self, controller):
        controller.add_component("Waveform Source", (0.0, 0.0))
        controller.model.components["VW1"].waveform_type = "PULSE"

        controller.copy_components(["VW1"])
        new_comps, _ = controller.paste_components()
        assert new_comps[0].waveform_type == "PULSE"


class TestMultiPasteIdempotency:
    """Pasting the same clipboard N times must always produce fresh IDs."""

    def test_three_successive_pastes(self, controller):
        controller.add_component("Resistor", (0.0, 0.0))
        controller.copy_components(["R1"])

        ids = {"R1"}
        for i in range(1, 4):
            comps, _ = controller.paste_components()
            new_id = comps[0].component_id
            assert new_id not in ids, f"Paste #{i} produced duplicate ID {new_id}"
            ids.add(new_id)

        # Model should contain R1 plus three pasted copies
        assert len(controller.model.components) == 4

    def test_successive_offsets_are_cumulative(self, controller):
        controller.add_component("Resistor", (0.0, 0.0))
        controller.copy_components(["R1"])

        positions = []
        for _ in range(3):
            comps, _ = controller.paste_components()
            positions.append(comps[0].position)

        assert positions[0] == (40.0, 40.0)
        assert positions[1] == (80.0, 80.0)
        assert positions[2] == (120.0, 120.0)


class TestMultiTerminalComponentsWithWires:
    """Components with >2 terminals (Op-Amp, BJT, VCVS, etc.) with wires."""

    def test_opamp_three_terminal_wire_copy(self, controller):
        """Copy an Op-Amp wired to two resistors; only fully-internal wires survive."""
        controller.add_component("Op-Amp", (0.0, 0.0))  # OA1
        controller.add_component("Resistor", (100.0, 0.0))  # R1
        controller.add_component("Resistor", (-100.0, 0.0))  # R2
        # Wire OA1 terminal 2 (output) -> R1 terminal 0
        controller.add_wire("OA1", 2, "R1", 0)
        # Wire OA1 terminal 0 (inp) -> R2 terminal 1
        controller.add_wire("OA1", 0, "R2", 1)

        # Copying all three should preserve both wires
        controller.copy_components(["OA1", "R1", "R2"])
        new_comps, new_wires = controller.paste_components()
        assert len(new_comps) == 3
        assert len(new_wires) == 2

        new_ids = {c.component_id for c in new_comps}
        for w in new_wires:
            assert w.start_component_id in new_ids
            assert w.end_component_id in new_ids

    def test_opamp_partial_selection_excludes_external_wire(self, controller):
        """Copying only OA1 and R1 should drop the wire to R2."""
        controller.add_component("Op-Amp", (0.0, 0.0))  # OA1
        controller.add_component("Resistor", (100.0, 0.0))  # R1
        controller.add_component("Resistor", (-100.0, 0.0))  # R2
        controller.add_wire("OA1", 2, "R1", 0)
        controller.add_wire("OA1", 0, "R2", 1)

        controller.copy_components(["OA1", "R1"])
        new_comps, new_wires = controller.paste_components()
        assert len(new_comps) == 2
        assert len(new_wires) == 1
        # The surviving wire should connect OA -> R
        wire = new_wires[0]
        assert wire.start_terminal == 2
        assert wire.end_terminal == 0

    def test_four_terminal_vcvs_wire_round_trip(self, controller):
        """VCVS has 4 terminals; wires on different terminal pairs."""
        controller.add_component("VCVS", (0.0, 0.0))  # E1
        controller.add_component("Resistor", (100.0, 0.0))  # R1
        controller.add_component("Resistor", (-100.0, 0.0))  # R2
        # Connect VCVS terminal 2 -> R1 terminal 0
        controller.add_wire("E1", 2, "R1", 0)
        # Connect VCVS terminal 0 -> R2 terminal 1
        controller.add_wire("E1", 0, "R2", 1)

        controller.copy_components(["E1", "R1", "R2"])
        new_comps, new_wires = controller.paste_components()
        assert len(new_comps) == 3
        assert len(new_wires) == 2

        terminal_pairs = {(w.start_terminal, w.end_terminal) for w in new_wires}
        assert (2, 0) in terminal_pairs
        assert (0, 1) in terminal_pairs


class TestCutPasteWires:
    """Cut two wired components, paste them back, verify wire integrity."""

    def test_cut_two_wired_paste_restores_wire(self, two_resistor_circuit):
        ctrl = two_resistor_circuit
        ctrl.cut_components(["R1", "R2"])
        assert len(ctrl.model.components) == 0
        assert len(ctrl.model.wires) == 0

        new_comps, new_wires = ctrl.paste_components()
        assert len(new_comps) == 2
        assert len(new_wires) == 1

        wire = new_wires[0]
        new_ids = {c.component_id for c in new_comps}
        assert wire.start_component_id in new_ids
        assert wire.end_component_id in new_ids

    def test_cut_single_from_pair_drops_wire(self, two_resistor_circuit):
        """Cutting only one component from a wired pair should not keep the wire."""
        ctrl = two_resistor_circuit
        ctrl.cut_components(["R1"])
        assert len(ctrl._clipboard.wires) == 0

        new_comps, new_wires = ctrl.paste_components()
        assert len(new_comps) == 1
        assert len(new_wires) == 0


class TestHasClipboardContent:
    """has_clipboard_content() must reflect state transitions correctly."""

    def test_initially_empty(self, controller):
        assert controller.has_clipboard_content() is False

    def test_after_copy(self, controller):
        controller.add_component("Resistor", (0.0, 0.0))
        controller.copy_components(["R1"])
        assert controller.has_clipboard_content() is True

    def test_after_failed_copy(self, controller):
        controller.copy_components(["NONEXISTENT"])
        assert controller.has_clipboard_content() is False

    def test_after_cut(self, controller):
        controller.add_component("Capacitor", (0.0, 0.0))
        controller.cut_components(["C1"])
        assert controller.has_clipboard_content() is True

    def test_content_persists_after_paste(self, controller):
        """Clipboard should retain its content after pasting."""
        controller.add_component("Resistor", (0.0, 0.0))
        controller.copy_components(["R1"])
        controller.paste_components()
        assert controller.has_clipboard_content() is True

    def test_new_copy_replaces_old(self, controller):
        """A new copy should replace whatever was on the clipboard."""
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Capacitor", (100.0, 0.0))
        controller.copy_components(["R1"])
        controller.copy_components(["C1"])
        assert len(controller._clipboard.components) == 1
        assert controller._clipboard.components[0]["id"] == "C1"


class TestPasteCommandUndo:
    """PasteCommand.undo() must remove all pasted items."""

    def test_undo_removes_pasted_component(self, controller):
        controller.add_component("Resistor", (0.0, 0.0))
        controller.copy_components(["R1"])

        cmd = PasteCommand(controller)
        controller.execute_command(cmd)
        assert "R2" in controller.model.components

        controller.undo()
        assert "R2" not in controller.model.components
        # Original must remain untouched
        assert "R1" in controller.model.components

    def test_undo_removes_pasted_wires(self, two_resistor_circuit):
        ctrl = two_resistor_circuit
        ctrl.copy_components(["R1", "R2"])

        cmd = PasteCommand(ctrl)
        ctrl.execute_command(cmd)
        assert len(ctrl.model.components) == 4
        assert len(ctrl.model.wires) == 2

        ctrl.undo()
        assert len(ctrl.model.components) == 2
        assert len(ctrl.model.wires) == 1

    def test_undo_paste_then_redo(self, controller):
        controller.add_component("Resistor", (0.0, 0.0))
        controller.copy_components(["R1"])

        cmd = PasteCommand(controller)
        controller.execute_command(cmd)
        assert len(controller.model.components) == 2

        controller.undo()
        assert len(controller.model.components) == 1

        controller.redo()
        assert len(controller.model.components) == 2

    def test_undo_fires_removal_events(self, controller, events):
        recorded, callback = events
        controller.add_component("Resistor", (0.0, 0.0))
        controller.copy_components(["R1"])

        cmd = PasteCommand(controller)
        controller.execute_command(cmd)

        controller.add_observer(callback)
        controller.undo()

        removed_events = [e for e in recorded if e[0] == "component_removed"]
        assert len(removed_events) == 1
        assert removed_events[0][1] == "R2"


class TestWireTerminalPreservation:
    """Wire terminal indices must be preserved through copy-paste."""

    def test_terminal_indices_preserved(self, controller):
        controller.add_component("Resistor", (0.0, 0.0))
        controller.add_component("Capacitor", (100.0, 0.0))
        controller.add_wire("R1", 1, "C1", 0)

        controller.copy_components(["R1", "C1"])
        _, new_wires = controller.paste_components()
        assert len(new_wires) == 1
        assert new_wires[0].start_terminal == 1
        assert new_wires[0].end_terminal == 0

    def test_multiple_wires_between_components(self, controller):
        """If two components have two wires (on different terminals), both are copied."""
        controller.add_component("VCVS", (0.0, 0.0))  # E1 (4 terminals)
        controller.add_component("Transformer", (100.0, 0.0))  # K1 (4 terminals)
        controller.add_wire("E1", 0, "K1", 0)
        controller.add_wire("E1", 2, "K1", 2)

        controller.copy_components(["E1", "K1"])
        _, new_wires = controller.paste_components()
        assert len(new_wires) == 2
        terminal_pairs = sorted([(w.start_terminal, w.end_terminal) for w in new_wires])
        assert terminal_pairs == [(0, 0), (2, 2)]
