"""
Tests for model/controller-level data round-trips and undo operations.

Covers:
- Serialization round-trips (flip, rotation, waveform, models, values)
- Wire data persistence through save/load
- Undo/redo stack via controller commands
- FileController operations (new, save, load, dirty tracking)
- Node consistency after wire add/remove

Issue: #280
"""

import json

import pytest
from controllers.circuit_controller import CircuitController
from controllers.commands import (
    AddAnnotationCommand,
    AddComponentCommand,
    ChangeValueCommand,
    DeleteAnnotationCommand,
    DeleteComponentCommand,
    EditAnnotationCommand,
    FlipComponentCommand,
    MoveComponentCommand,
    RotateComponentCommand,
)
from controllers.file_controller import FileController
from models.annotation import AnnotationData
from models.circuit import CircuitModel
from models.component import COMPONENT_TYPES, ComponentData
from models.wire import WireData

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_circuit_with_all_fields():
    """Build a circuit exercising every serializable field."""
    model = CircuitModel()
    r1 = ComponentData(
        component_id="R1",
        component_type="Resistor",
        value="4.7k",
        position=(100.0, 200.0),
        rotation=90,
        flip_h=True,
        flip_v=False,
    )
    c1 = ComponentData(
        component_id="C1",
        component_type="Capacitor",
        value="10u",
        position=(200.0, 200.0),
        rotation=180,
        flip_h=False,
        flip_v=True,
    )
    v1 = ComponentData(
        component_id="V1",
        component_type="Voltage Source",
        value="12V",
        position=(0.0, 0.0),
    )
    gnd = ComponentData(
        component_id="GND1",
        component_type="Ground",
        value="0V",
        position=(100.0, 300.0),
    )
    model.add_component(r1)
    model.add_component(c1)
    model.add_component(v1)
    model.add_component(gnd)
    model.component_counter = {"R": 1, "C": 1, "V": 1, "GND": 1}

    model.add_wire(WireData("V1", 0, "R1", 0))
    model.add_wire(WireData("R1", 1, "C1", 0))
    model.add_wire(WireData("C1", 1, "GND1", 0))
    model.add_wire(WireData("V1", 1, "GND1", 0))

    model.analysis_type = "Transient"
    model.analysis_params = {"step": "1m", "duration": "10m"}

    # Add custom net name
    node = model.terminal_to_node.get(("V1", 0))
    if node:
        node.set_custom_label("Vin")

    # Add annotation
    model.annotations.append(
        AnnotationData(text="Test Label", x=50.0, y=50.0, font_size=14, bold=True, color="#FF0000")
    )

    return model


# ===========================================================================
# Serialization Round-Trips
# ===========================================================================


class TestSerializationRoundTrips:
    """Verify that to_dict → from_dict produces identical data."""

    def test_full_circuit_round_trip(self):
        """Complete circuit with all field types survives round-trip."""
        model = _build_circuit_with_all_fields()
        data1 = model.to_dict()
        model2 = CircuitModel.from_dict(data1)
        data2 = model2.to_dict()
        assert data1 == data2

    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    def test_rotation_round_trip(self, rotation):
        """Component rotation is preserved through serialization."""
        comp = ComponentData("R1", "Resistor", "1k", (0, 0), rotation=rotation)
        data = comp.to_dict()
        restored = ComponentData.from_dict(data)
        assert restored.rotation == rotation

    @pytest.mark.parametrize("flip_h,flip_v", [(True, False), (False, True), (True, True)])
    def test_flip_state_round_trip(self, flip_h, flip_v):
        """Component flip states are preserved through serialization."""
        comp = ComponentData("R1", "Resistor", "1k", (0, 0), flip_h=flip_h, flip_v=flip_v)
        data = comp.to_dict()
        restored = ComponentData.from_dict(data)
        assert restored.flip_h == flip_h
        assert restored.flip_v == flip_v

    def test_waveform_source_round_trip(self):
        """Waveform source with custom params survives round-trip."""
        comp = ComponentData("VW1", "Waveform Source", "SIN(0 5 1k)", (0, 0))
        # Customize SIN params
        comp.waveform_params["SIN"]["amplitude"] = "10"
        comp.waveform_params["SIN"]["frequency"] = "2k"
        comp.waveform_type = "SIN"

        data = comp.to_dict()
        restored = ComponentData.from_dict(data)
        assert restored.waveform_type == "SIN"
        assert restored.waveform_params["SIN"]["amplitude"] == "10"
        assert restored.waveform_params["SIN"]["frequency"] == "2k"

    def test_waveform_pulse_params_round_trip(self):
        """PULSE waveform type and params survive round-trip."""
        comp = ComponentData("VW1", "Waveform Source", "PULSE(0 5 0 1n 1n 500u 1m)", (0, 0))
        comp.waveform_type = "PULSE"
        comp.waveform_params["PULSE"]["v2"] = "3.3"

        data = comp.to_dict()
        restored = ComponentData.from_dict(data)
        assert restored.waveform_type == "PULSE"
        assert restored.waveform_params["PULSE"]["v2"] == "3.3"

    @pytest.mark.parametrize("model_name", ["Ideal", "LM741", "TL081", "LM358"])
    def test_opamp_model_round_trip(self, model_name):
        """Op-amp model names survive round-trip."""
        comp = ComponentData("OA1", "Op-Amp", model_name, (0, 0))
        data = comp.to_dict()
        restored = ComponentData.from_dict(data)
        assert restored.value == model_name
        assert restored.component_type == "Op-Amp"

    @pytest.mark.parametrize(
        "comp_type,value",
        [
            ("MOSFET NMOS", "NMOS1"),
            ("MOSFET PMOS", "PMOS1"),
            ("BJT NPN", "2N3904"),
            ("BJT PNP", "2N3906"),
            ("Diode", "IS=1e-14 N=1"),
            ("LED", "IS=1e-20 N=1.8 EG=1.9"),
            ("Zener Diode", "IS=1e-14 N=1 BV=5.1 IBV=1e-3"),
        ],
    )
    def test_semiconductor_model_round_trip(self, comp_type, value):
        """Semiconductor component model values survive round-trip."""
        comp = ComponentData("X1", comp_type, value, (0, 0))
        data = comp.to_dict()
        restored = ComponentData.from_dict(data)
        assert restored.value == value
        assert restored.component_type == comp_type

    @pytest.mark.parametrize("comp_type", COMPONENT_TYPES)
    def test_all_component_types_round_trip(self, comp_type):
        """Every component type serializes and deserializes without error."""
        comp = ComponentData("X1", comp_type, "test_val", (50.0, 75.0), rotation=90)
        data = comp.to_dict()
        restored = ComponentData.from_dict(data)
        assert restored.component_type == comp_type
        assert restored.position == (50.0, 75.0)
        assert restored.rotation == 90

    def test_analysis_settings_round_trip(self):
        """Analysis type and params survive circuit round-trip."""
        model = CircuitModel()
        model.analysis_type = "AC Sweep"
        model.analysis_params = {"variation": "dec", "points": "10", "fstart": "1", "fstop": "1e6"}

        data = model.to_dict()
        restored = CircuitModel.from_dict(data)
        assert restored.analysis_type == "AC Sweep"
        assert restored.analysis_params == model.analysis_params

    def test_default_analysis_omitted_from_dict(self):
        """Default analysis type (DC Operating Point) is not stored in dict."""
        model = CircuitModel()
        data = model.to_dict()
        assert "analysis_type" not in data
        assert "analysis_params" not in data

    def test_annotation_round_trip(self):
        """Annotation data survives circuit round-trip."""
        model = CircuitModel()
        model.annotations.append(AnnotationData(text="Note", x=10.0, y=20.0, font_size=16, bold=True, color="#00FF00"))
        data = model.to_dict()
        restored = CircuitModel.from_dict(data)
        assert len(restored.annotations) == 1
        ann = restored.annotations[0]
        assert ann.text == "Note"
        assert ann.x == 10.0
        assert ann.y == 20.0
        assert ann.font_size == 16
        assert ann.bold is True
        assert ann.color == "#00FF00"

    def test_empty_circuit_round_trip(self):
        """Empty circuit serializes and deserializes cleanly."""
        model = CircuitModel()
        data = model.to_dict()
        restored = CircuitModel.from_dict(data)
        assert len(restored.components) == 0
        assert len(restored.wires) == 0
        assert len(restored.nodes) == 0


# ===========================================================================
# Wire Data Persistence
# ===========================================================================


class TestWireDataPersistence:
    """Verify wire data survives save/load cycles."""

    def test_wire_round_trip(self):
        """Wire start/end component IDs and terminals survive round-trip."""
        wire = WireData("V1", 0, "R1", 1)
        data = wire.to_dict()
        restored = WireData.from_dict(data)
        assert restored.start_component_id == "V1"
        assert restored.start_terminal == 0
        assert restored.end_component_id == "R1"
        assert restored.end_terminal == 1

    def test_wire_deletion_persists_through_save_load(self, tmp_path):
        """Deleting a wire and saving/loading preserves the deletion."""
        model = CircuitModel()
        r1 = ComponentData("R1", "Resistor", "1k", (0, 0))
        r2 = ComponentData("R2", "Resistor", "2k", (100, 0))
        gnd = ComponentData("GND1", "Ground", "0V", (0, 100))
        model.add_component(r1)
        model.add_component(r2)
        model.add_component(gnd)
        model.component_counter = {"R": 2, "GND": 1}

        model.add_wire(WireData("R1", 0, "R2", 0))
        model.add_wire(WireData("R2", 1, "GND1", 0))
        assert len(model.wires) == 2

        # Delete first wire
        model.remove_wire(0)
        assert len(model.wires) == 1

        # Save and reload
        ctrl = FileController(model)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)

        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)
        assert len(ctrl2.model.wires) == 1
        assert ctrl2.model.wires[0].start_component_id == "R2"

    def test_net_label_survives_save_load(self, tmp_path):
        """Custom node labels (net names) survive save/load cycle."""
        model = CircuitModel()
        v1 = ComponentData("V1", "Voltage Source", "5V", (0, 0))
        r1 = ComponentData("R1", "Resistor", "1k", (100, 0))
        model.add_component(v1)
        model.add_component(r1)
        model.component_counter = {"V": 1, "R": 1}
        model.add_wire(WireData("V1", 0, "R1", 0))

        # Set custom label
        node = model.terminal_to_node[("V1", 0)]
        node.set_custom_label("Vout")

        ctrl = FileController(model)
        filepath = tmp_path / "net_names.json"
        ctrl.save_circuit(filepath)

        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)
        node2 = ctrl2.model.terminal_to_node[("V1", 0)]
        assert node2.custom_label == "Vout"
        assert node2.get_label() == "Vout"

    def test_waypoints_round_trip(self):
        """Wire waypoints survive serialization round-trip."""
        wire = WireData("V1", 0, "R1", 1)
        wire.waypoints = [(10.0, 20.0), (30.0, 20.0), (30.0, 40.0)]
        data = wire.to_dict()
        assert "waypoints" in data
        assert data["waypoints"] == [[10.0, 20.0], [30.0, 20.0], [30.0, 40.0]]

        restored = WireData.from_dict(data)
        assert restored.waypoints == [(10.0, 20.0), (30.0, 20.0), (30.0, 40.0)]

    def test_empty_waypoints_omitted_from_dict(self):
        """Wires with no waypoints don't include waypoints key in JSON."""
        wire = WireData("V1", 0, "R1", 1)
        data = wire.to_dict()
        assert "waypoints" not in data

    def test_old_format_without_waypoints_loads(self):
        """Old circuit files without waypoints field load without error."""
        data = {
            "start_comp": "V1",
            "start_term": 0,
            "end_comp": "R1",
            "end_term": 1,
        }
        wire = WireData.from_dict(data)
        assert wire.waypoints == []

    def test_waypoints_persist_through_file_save_load(self, tmp_path):
        """Wire waypoints survive save/load through FileController."""
        model = CircuitModel()
        r1 = ComponentData("R1", "Resistor", "1k", (0, 0))
        r2 = ComponentData("R2", "Resistor", "2k", (100, 0))
        model.add_component(r1)
        model.add_component(r2)
        model.component_counter = {"R": 2}

        wire = WireData("R1", 0, "R2", 0)
        wire.waypoints = [(30.0, 0.0), (50.0, 0.0), (70.0, 0.0)]
        model.add_wire(wire)

        ctrl = FileController(model)
        filepath = tmp_path / "waypoints.json"
        ctrl.save_circuit(filepath)

        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)
        assert len(ctrl2.model.wires) == 1
        assert ctrl2.model.wires[0].waypoints == [(30.0, 0.0), (50.0, 0.0), (70.0, 0.0)]

    def test_multiple_wires_waypoints_persist(self, tmp_path):
        """Multiple wires each keep their own waypoints through save/load."""
        model = CircuitModel()
        r1 = ComponentData("R1", "Resistor", "1k", (0, 0))
        r2 = ComponentData("R2", "Resistor", "2k", (100, 0))
        gnd = ComponentData("GND1", "Ground", "0V", (50, 100))
        model.add_component(r1)
        model.add_component(r2)
        model.add_component(gnd)
        model.component_counter = {"R": 2, "GND": 1}

        w1 = WireData("R1", 0, "R2", 0)
        w1.waypoints = [(10.0, 0.0), (90.0, 0.0)]
        w2 = WireData("R2", 1, "GND1", 0)
        w2.waypoints = [(100.0, 30.0), (100.0, 50.0), (50.0, 50.0), (50.0, 90.0)]
        model.add_wire(w1)
        model.add_wire(w2)

        ctrl = FileController(model)
        filepath = tmp_path / "multi_wp.json"
        ctrl.save_circuit(filepath)

        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)
        assert ctrl2.model.wires[0].waypoints == [(10.0, 0.0), (90.0, 0.0)]
        assert ctrl2.model.wires[1].waypoints == [
            (100.0, 30.0),
            (100.0, 50.0),
            (50.0, 50.0),
            (50.0, 90.0),
        ]

    def test_wire_count_preserved_through_save_load(self, tmp_path):
        """The exact number of wires is preserved through save/load."""
        model = CircuitModel()
        v1 = ComponentData("V1", "Voltage Source", "5V", (0, 0))
        r1 = ComponentData("R1", "Resistor", "1k", (100, 0))
        r2 = ComponentData("R2", "Resistor", "2k", (200, 0))
        gnd = ComponentData("GND1", "Ground", "0V", (200, 100))
        for c in [v1, r1, r2, gnd]:
            model.add_component(c)
        model.component_counter = {"V": 1, "R": 2, "GND": 1}

        model.add_wire(WireData("V1", 0, "R1", 0))
        model.add_wire(WireData("R1", 1, "R2", 0))
        model.add_wire(WireData("R2", 1, "GND1", 0))
        model.add_wire(WireData("V1", 1, "GND1", 0))

        ctrl = FileController(model)
        filepath = tmp_path / "wires.json"
        ctrl.save_circuit(filepath)

        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)
        assert len(ctrl2.model.wires) == 4


# ===========================================================================
# Undo/Redo Stack
# ===========================================================================


class TestUndoRedoWorkflows:
    """Test undo/redo through CircuitController command execution."""

    def test_add_component_undo_redo(self):
        """Place component → undo removes it → redo restores a component."""
        ctrl = CircuitController()
        cmd = AddComponentCommand(ctrl, "Resistor", (100, 100))
        ctrl.execute_command(cmd)

        assert len(ctrl.model.components) == 1

        ctrl.undo()
        assert len(ctrl.model.components) == 0

        ctrl.redo()
        assert len(ctrl.model.components) == 1

    def test_delete_component_undo_restores(self):
        """Delete component → undo restores it with wires."""
        ctrl = CircuitController()
        comp = ctrl.add_component("Resistor", (0, 0))
        comp2 = ctrl.add_component("Resistor", (100, 0))
        ctrl.add_wire(comp.component_id, 0, comp2.component_id, 0)

        assert len(ctrl.model.wires) == 1

        cmd = DeleteComponentCommand(ctrl, comp.component_id)
        ctrl.execute_command(cmd)
        assert comp.component_id not in ctrl.model.components
        assert len(ctrl.model.wires) == 0

        ctrl.undo()
        assert comp.component_id in ctrl.model.components
        assert len(ctrl.model.wires) == 1

    def test_move_undo_reverts_position(self):
        """Move → undo reverts to original position."""
        ctrl = CircuitController()
        comp = ctrl.add_component("Resistor", (0, 0))
        original_pos = comp.position

        cmd = MoveComponentCommand(ctrl, comp.component_id, (200, 300))
        ctrl.execute_command(cmd)
        assert ctrl.model.components[comp.component_id].position == (200, 300)

        ctrl.undo()
        assert ctrl.model.components[comp.component_id].position == original_pos

    def test_flip_undo_reverts_flip_state(self):
        """Flip → undo reverts flip state."""
        ctrl = CircuitController()
        comp = ctrl.add_component("Resistor", (0, 0))
        assert comp.flip_h is False

        cmd = FlipComponentCommand(ctrl, comp.component_id, horizontal=True)
        ctrl.execute_command(cmd)
        assert ctrl.model.components[comp.component_id].flip_h is True

        ctrl.undo()
        assert ctrl.model.components[comp.component_id].flip_h is False

    def test_flip_vertical_undo(self):
        """Vertical flip → undo reverts."""
        ctrl = CircuitController()
        comp = ctrl.add_component("Capacitor", (0, 0))
        assert comp.flip_v is False

        cmd = FlipComponentCommand(ctrl, comp.component_id, horizontal=False)
        ctrl.execute_command(cmd)
        assert ctrl.model.components[comp.component_id].flip_v is True

        ctrl.undo()
        assert ctrl.model.components[comp.component_id].flip_v is False

    def test_rotate_undo(self):
        """Rotate → undo reverts rotation."""
        ctrl = CircuitController()
        comp = ctrl.add_component("Inductor", (0, 0))
        assert comp.rotation == 0

        cmd = RotateComponentCommand(ctrl, comp.component_id, clockwise=True)
        ctrl.execute_command(cmd)
        assert ctrl.model.components[comp.component_id].rotation == 90

        ctrl.undo()
        assert ctrl.model.components[comp.component_id].rotation == 0

    def test_change_value_undo(self):
        """Change value → undo restores old value."""
        ctrl = CircuitController()
        comp = ctrl.add_component("Resistor", (0, 0))
        old_value = comp.value

        cmd = ChangeValueCommand(ctrl, comp.component_id, "4.7k")
        ctrl.execute_command(cmd)
        assert ctrl.model.components[comp.component_id].value == "4.7k"

        ctrl.undo()
        assert ctrl.model.components[comp.component_id].value == old_value

    def test_annotation_add_undo_redo(self):
        """Add annotation → undo removes → redo restores."""
        ctrl = CircuitController()
        ann = AnnotationData(text="Test", x=10, y=20)
        cmd = AddAnnotationCommand(ctrl, ann)
        ctrl.execute_command(cmd)
        assert len(ctrl.model.annotations) == 1

        ctrl.undo()
        assert len(ctrl.model.annotations) == 0

        ctrl.redo()
        assert len(ctrl.model.annotations) == 1
        assert ctrl.model.annotations[0].text == "Test"

    def test_annotation_delete_undo(self):
        """Delete annotation → undo restores it."""
        ctrl = CircuitController()
        ann = AnnotationData(text="Important", x=5, y=10)
        ctrl.add_annotation(ann)
        assert len(ctrl.model.annotations) == 1

        cmd = DeleteAnnotationCommand(ctrl, 0)
        ctrl.execute_command(cmd)
        assert len(ctrl.model.annotations) == 0

        ctrl.undo()
        assert len(ctrl.model.annotations) == 1
        assert ctrl.model.annotations[0].text == "Important"

    def test_annotation_edit_undo(self):
        """Edit annotation text → undo restores old text."""
        ctrl = CircuitController()
        ann = AnnotationData(text="Original")
        ctrl.add_annotation(ann)

        cmd = EditAnnotationCommand(ctrl, 0, "Modified")
        ctrl.execute_command(cmd)
        assert ctrl.model.annotations[0].text == "Modified"

        ctrl.undo()
        assert ctrl.model.annotations[0].text == "Original"

    def test_multiple_undos_in_sequence(self):
        """Multiple operations can be undone in correct LIFO order."""
        ctrl = CircuitController()
        cmd1 = AddComponentCommand(ctrl, "Resistor", (0, 0))
        ctrl.execute_command(cmd1)
        cmd2 = AddComponentCommand(ctrl, "Capacitor", (100, 0))
        ctrl.execute_command(cmd2)

        assert len(ctrl.model.components) == 2

        ctrl.undo()  # undo capacitor
        assert len(ctrl.model.components) == 1
        assert cmd1.component_id in ctrl.model.components

        ctrl.undo()  # undo resistor
        assert len(ctrl.model.components) == 0

    def test_redo_cleared_after_new_command(self):
        """Executing a new command after undo clears the redo stack."""
        ctrl = CircuitController()
        cmd1 = AddComponentCommand(ctrl, "Resistor", (0, 0))
        ctrl.execute_command(cmd1)

        ctrl.undo()
        assert ctrl.can_redo()

        cmd2 = AddComponentCommand(ctrl, "Capacitor", (100, 0))
        ctrl.execute_command(cmd2)
        assert not ctrl.can_redo()


# ===========================================================================
# FileController Operations
# ===========================================================================


class TestFileControllerOperations:
    """Test FileController save/load/new behavior."""

    def test_new_circuit_clears_model(self):
        """new_circuit() clears all model data."""
        model = _build_circuit_with_all_fields()
        ctrl = FileController(model)
        ctrl.new_circuit()

        assert len(ctrl.model.components) == 0
        assert len(ctrl.model.wires) == 0
        assert len(ctrl.model.nodes) == 0
        assert len(ctrl.model.annotations) == 0
        assert ctrl.model.analysis_type == "DC Operating Point"
        assert ctrl.model.analysis_params == {}
        assert ctrl.current_file is None

    def test_save_sets_current_file(self, tmp_path):
        """save_circuit() updates current_file."""
        model = CircuitModel()
        ctrl = FileController(model)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)

        assert ctrl.current_file == filepath
        assert ctrl.has_file()

    def test_load_updates_current_file(self, tmp_path):
        """load_circuit() updates current_file."""
        model = CircuitModel()
        ctrl = FileController(model)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)

        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)
        assert ctrl2.current_file == filepath

    def test_new_circuit_clears_file_path(self, tmp_path):
        """new_circuit() after save clears the current_file."""
        model = CircuitModel()
        ctrl = FileController(model)
        filepath = tmp_path / "test.json"
        ctrl.save_circuit(filepath)
        assert ctrl.has_file()

        ctrl.new_circuit()
        assert not ctrl.has_file()
        assert ctrl.current_file is None

    def test_load_preserves_model_reference(self, tmp_path):
        """load_circuit() updates model in place, preserving the reference."""
        model = CircuitModel()
        ctrl = FileController(model)

        # Save a non-empty circuit
        model2 = _build_circuit_with_all_fields()
        ctrl2 = FileController(model2)
        filepath = tmp_path / "full.json"
        ctrl2.save_circuit(filepath)

        # Load into original controller
        model_ref = ctrl.model
        ctrl.load_circuit(filepath)
        assert ctrl.model is model_ref  # same object
        assert len(ctrl.model.components) > 0

    def test_save_load_round_trip_full(self, tmp_path):
        """Full circuit save → load preserves all data."""
        model = _build_circuit_with_all_fields()
        ctrl = FileController(model)
        filepath = tmp_path / "full.json"
        ctrl.save_circuit(filepath)

        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)

        assert set(ctrl2.model.components.keys()) == set(model.components.keys())
        assert len(ctrl2.model.wires) == len(model.wires)
        assert ctrl2.model.analysis_type == "Transient"
        assert ctrl2.model.analysis_params["step"] == "1m"
        assert len(ctrl2.model.annotations) == 1
        assert ctrl2.model.annotations[0].text == "Test Label"

    def test_save_load_preserves_flip_state(self, tmp_path):
        """Component flip_h and flip_v survive save/load."""
        model = CircuitModel()
        comp = ComponentData("R1", "Resistor", "1k", (0, 0), flip_h=True, flip_v=True)
        model.add_component(comp)
        model.component_counter = {"R": 1}

        ctrl = FileController(model)
        filepath = tmp_path / "flip.json"
        ctrl.save_circuit(filepath)

        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)
        restored = ctrl2.model.components["R1"]
        assert restored.flip_h is True
        assert restored.flip_v is True

    def test_save_load_preserves_rotation(self, tmp_path):
        """Component rotation survives save/load."""
        model = CircuitModel()
        comp = ComponentData("C1", "Capacitor", "10u", (0, 0), rotation=270)
        model.add_component(comp)
        model.component_counter = {"C": 1}

        ctrl = FileController(model)
        filepath = tmp_path / "rot.json"
        ctrl.save_circuit(filepath)

        ctrl2 = FileController()
        ctrl2.load_circuit(filepath)
        assert ctrl2.model.components["C1"].rotation == 270

    def test_save_produces_valid_json(self, tmp_path):
        """Saved file is valid JSON."""
        model = _build_circuit_with_all_fields()
        ctrl = FileController(model)
        filepath = tmp_path / "valid.json"
        ctrl.save_circuit(filepath)

        with open(filepath) as f:
            data = json.load(f)
        assert "components" in data
        assert "wires" in data


# ===========================================================================
# Node Consistency
# ===========================================================================


class TestNodeConsistency:
    """Verify terminal-to-node mapping stays valid after operations."""

    def test_terminal_to_node_valid_after_wire_add(self):
        """Adding a wire updates terminal-to-node mapping correctly."""
        model = CircuitModel()
        r1 = ComponentData("R1", "Resistor", "1k", (0, 0))
        r2 = ComponentData("R2", "Resistor", "2k", (100, 0))
        model.add_component(r1)
        model.add_component(r2)

        model.add_wire(WireData("R1", 0, "R2", 0))

        # Both terminals should map to the same node
        node1 = model.terminal_to_node[("R1", 0)]
        node2 = model.terminal_to_node[("R2", 0)]
        assert node1 is node2
        assert ("R1", 0) in node1.terminals
        assert ("R2", 0) in node1.terminals

    def test_node_merge_on_connect(self):
        """Connecting two existing nodes merges them."""
        model = CircuitModel()
        r1 = ComponentData("R1", "Resistor", "1k", (0, 0))
        r2 = ComponentData("R2", "Resistor", "2k", (100, 0))
        r3 = ComponentData("R3", "Resistor", "3k", (200, 0))
        model.add_component(r1)
        model.add_component(r2)
        model.add_component(r3)

        # Create two separate nodes
        model.add_wire(WireData("R1", 0, "R2", 0))
        model.add_wire(WireData("R2", 1, "R3", 0))

        # R1:0 and R2:0 are in one node
        # R2:1 and R3:0 are in another node
        node_a = model.terminal_to_node[("R1", 0)]
        node_b = model.terminal_to_node[("R2", 1)]
        assert node_a is not node_b

        # Now bridge R1:1 → R2:1 to merge nodes
        model.add_wire(WireData("R1", 1, "R2", 1))
        merged = model.terminal_to_node[("R1", 1)]
        assert model.terminal_to_node[("R2", 1)] is merged
        assert model.terminal_to_node[("R3", 0)] is merged

    def test_node_splitting_on_wire_remove(self):
        """Removing a wire can split a node into two."""
        model = CircuitModel()
        r1 = ComponentData("R1", "Resistor", "1k", (0, 0))
        r2 = ComponentData("R2", "Resistor", "2k", (100, 0))
        r3 = ComponentData("R3", "Resistor", "3k", (200, 0))
        model.add_component(r1)
        model.add_component(r2)
        model.add_component(r3)

        # Chain: R1:1 -- R2:0, R2:1 -- R3:0
        model.add_wire(WireData("R1", 1, "R2", 0))
        model.add_wire(WireData("R2", 0, "R3", 0))

        # All three terminals should be in the same node
        node = model.terminal_to_node[("R1", 1)]
        assert ("R2", 0) in node.terminals
        assert ("R3", 0) in node.terminals

        # Remove the bridge wire
        model.remove_wire(0)  # R1:1 -- R2:0

        # R2:0 and R3:0 should still be connected, R1:1 should be separate
        node_r2 = model.terminal_to_node.get(("R2", 0))
        # After wire removal, R1:1 has no wires connecting it, so it won't have a node
        # R2:0 and R3:0 still share a node
        assert node_r2 is not None
        assert ("R3", 0) in node_r2.terminals

    def test_ground_node_assignment_persists(self):
        """Ground nodes are correctly identified and persist."""
        model = CircuitModel()
        gnd = ComponentData("GND1", "Ground", "0V", (0, 0))
        r1 = ComponentData("R1", "Resistor", "1k", (100, 0))
        model.add_component(gnd)
        model.add_component(r1)
        model.add_wire(WireData("GND1", 0, "R1", 1))

        node = model.terminal_to_node[("GND1", 0)]
        assert node.is_ground
        assert ("R1", 1) in node.terminals

    def test_ground_node_persists_through_rebuild(self):
        """rebuild_nodes() preserves ground status."""
        model = CircuitModel()
        gnd = ComponentData("GND1", "Ground", "0V", (0, 0))
        r1 = ComponentData("R1", "Resistor", "1k", (100, 0))
        model.add_component(gnd)
        model.add_component(r1)
        model.add_wire(WireData("GND1", 0, "R1", 1))

        model.rebuild_nodes()

        node = model.terminal_to_node[("GND1", 0)]
        assert node.is_ground

    def test_custom_label_preserved_through_rebuild(self):
        """Custom net labels survive rebuild_nodes()."""
        model = CircuitModel()
        r1 = ComponentData("R1", "Resistor", "1k", (0, 0))
        r2 = ComponentData("R2", "Resistor", "2k", (100, 0))
        model.add_component(r1)
        model.add_component(r2)
        model.add_wire(WireData("R1", 0, "R2", 0))

        node = model.terminal_to_node[("R1", 0)]
        node.set_custom_label("MyNet")

        model.rebuild_nodes()

        rebuilt_node = model.terminal_to_node[("R1", 0)]
        assert rebuilt_node.custom_label == "MyNet"

    def test_node_count_matches_topology(self):
        """Simple series circuit has the expected number of nodes."""
        model = CircuitModel()
        v1 = ComponentData("V1", "Voltage Source", "5V", (0, 0))
        r1 = ComponentData("R1", "Resistor", "1k", (100, 0))
        gnd = ComponentData("GND1", "Ground", "0V", (100, 100))
        model.add_component(v1)
        model.add_component(r1)
        model.add_component(gnd)

        model.add_wire(WireData("V1", 0, "R1", 0))
        model.add_wire(WireData("R1", 1, "GND1", 0))
        model.add_wire(WireData("V1", 1, "GND1", 0))

        # V1:0 + R1:0 = nodeA, R1:1 + GND1:0 + V1:1 = ground
        assert len(model.nodes) == 2

        ground_nodes = [n for n in model.nodes if n.is_ground]
        assert len(ground_nodes) == 1
