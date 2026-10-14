"""Regression tests for issue #945: undoing wire deletion desyncs the canvas
wire list from the model wire list, corrupting wire routes.

The model (``CircuitModel.wires``) is the single source of truth for wire
order.  A restored model wire is a fresh ``WireData`` (``DeleteWireCommand``
stores ``WireData.from_dict(...)``), so the canvas graphics item must re-point
its ``.model`` at that instance rather than object-identity-matching the
original.  Order must therefore be reconciled by key (start/end component +
terminal), and each graphics item re-pointed at the restored model instance, so
the list stays both identity- and order-aligned with the model.

Reproduction (undoable path).  Given a 2-wire chain ``[W0, W1]`` and deleting
``[0]`` twice (so each ``DeleteWireCommand`` records ``wire_index=0``):

* undo ``cmd2`` inserts ``W1`` at index 0 -> model ``[W1]``; the canvas observer
  appends ``W1`` -> canvas ``[W1]``.
* undo ``cmd1`` inserts ``W0`` at index 0 -> model ``[W0, W1]``; the canvas
  observer appends ``W0`` -> canvas ``[W1, W0]``.

Model ``[W0, W1]`` vs canvas ``[W1, W0]``: ``canvas.wires[i].model`` is a
*different* wire than ``model.wires[i]``, so any redraw/waypoint-drag reads the
geometry off the wrong model entry (issue #945).
"""

from controllers.circuit_controller import CircuitController
from controllers.commands import DeleteWireCommand
from GUI.circuit_canvas import CircuitCanvasView
from models.circuit import CircuitModel


def _make_two_wire_chain():
    """Build a 2-wire chain and return ``(canvas, ctrl)``.

    Wire layout:

        V1[0] -- R1[0]   (W0)
        R1[1] -- GND1[0] (W1)
    """
    ctrl = CircuitController(CircuitModel())
    canvas = CircuitCanvasView(ctrl)

    v1 = ctrl.add_component("Voltage Source", (0, 0))
    r1 = ctrl.add_component("Resistor", (200, 0))
    ctrl.add_component("Ground", (400, 0))
    ctrl.add_wire(v1.component_id, 0, r1.component_id, 0)
    ctrl.add_wire(r1.component_id, 1, "GND1", 0)

    assert len(canvas.wires) == 2, "precondition: chain has two wires on the canvas"
    return canvas, ctrl


def _delete_both(cmd):
    """Delete both chain wires via two index-0 deletes (records 0, 0)."""
    cmd.execute_command(DeleteWireCommand(cmd, 0))
    assert len(cmd.model.wires) == 1
    cmd.execute_command(DeleteWireCommand(cmd, 0))
    assert len(cmd.model.wires) == 0


def _assert_aligned(canvas, ctrl):
    """Assert every canvas wire backs the model wire at the same index."""
    model_wires = list(ctrl.model.wires)
    assert len(canvas.wires) == len(
        model_wires
    ), f"canvas/model wire count mismatch: {len(canvas.wires)} vs {len(model_wires)}"
    for i, item in enumerate(canvas.wires):
        # Identity (not equality): the canvas item must back the exact
        # WireData the rest of the system sees, so geometry reads align.
        assert item.model is model_wires[i]


class TestWireUndoDesync:
    """The canvas and model wire lists must stay identity- and order-aligned."""

    def test_undo_multiple_wires_indices_align(self):
        """Core fix: restoring multiple deleted wires keeps the lists aligned."""
        canvas, ctrl = _make_two_wire_chain()
        _delete_both(ctrl)

        ctrl.undo()
        ctrl.undo()
        assert len(ctrl.model.wires) == 2
        _assert_aligned(canvas, ctrl)

    def test_undo_restored_wire_uses_rebuilt_model_data(self):
        """Restored model wires are fresh instances; canvas re-points at them."""
        canvas, ctrl = _make_two_wire_chain()
        _delete_both(ctrl)

        ctrl.undo()
        ctrl.undo()
        restored = list(ctrl.model.wires)

        # Deleting again and undoing produces new fresh instances; the canvas
        # must re-point at those, never a stale reference to the old object.
        before_ids = {id(w) for w in restored}
        _delete_both(ctrl)
        ctrl.undo()
        ctrl.undo()
        after_ids = {id(w) for w in ctrl.model.wires}

        # The fresh instances differ between the two restores, and the canvas
        # tracks the newest ones.
        _assert_aligned(canvas, ctrl)
        assert before_ids - after_ids, "restored wires should be re-created fresh"
        assert {id(w.model) for w in canvas.wires} == after_ids

    def test_redo_multiple_wires_indices_align(self):
        """Redo after a multi-undo keeps the lists aligned."""
        canvas, ctrl = _make_two_wire_chain()
        _delete_both(ctrl)

        ctrl.undo()
        ctrl.undo()
        _assert_aligned(canvas, ctrl)

        ctrl.redo()
        ctrl.redo()
        assert len(canvas.wires) == 0

    def test_single_undo_still_in_sync(self):
        """Regression guard: single-wire deletion/undo stays aligned."""
        canvas, ctrl = _make_two_wire_chain()

        ctrl.execute_command(DeleteWireCommand(ctrl, 0))
        assert len(canvas.wires) == 1

        ctrl.undo()
        assert len(canvas.wires) == 2
        _assert_aligned(canvas, ctrl)
