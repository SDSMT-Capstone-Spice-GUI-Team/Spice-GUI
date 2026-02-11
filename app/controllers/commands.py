"""
Command Pattern Implementation for Undo/Redo.

Each command stores minimal state needed to undo/redo an operation.
Commands are executed through the CircuitController to maintain consistency.
"""

from abc import ABC, abstractmethod
from typing import Optional

from models.annotation import AnnotationData
from models.component import ComponentData
from models.wire import WireData


class Command(ABC):
    """Base class for undoable commands."""

    @abstractmethod
    def execute(self) -> None:
        """Execute the command (perform the action)."""
        pass

    @abstractmethod
    def undo(self) -> None:
        """Undo the command (reverse the action)."""
        pass

    def get_description(self) -> str:
        """Return a human-readable description of this command."""
        return self.__class__.__name__


class AddComponentCommand(Command):
    """Command to add a component to the circuit."""

    def __init__(self, controller, component_type: str, position: tuple[float, float]):
        self.controller = controller
        self.component_type = component_type
        self.position = position
        self.component_id: Optional[str] = None

    def execute(self) -> None:
        """Add the component and store its ID for undo."""
        component = self.controller.add_component(self.component_type, self.position)
        self.component_id = component.component_id

    def undo(self) -> None:
        """Remove the added component."""
        if self.component_id:
            self.controller.remove_component(self.component_id)

    def get_description(self) -> str:
        return f"Add {self.component_type}"


class DeleteComponentCommand(Command):
    """Command to delete a component from the circuit."""

    def __init__(self, controller, component_id: str):
        self.controller = controller
        self.component_id = component_id
        self.component_data: Optional[ComponentData] = None
        self.deleted_wires: list[tuple[int, WireData]] = []

    def execute(self) -> None:
        """Delete the component and store its data for undo."""
        # Store component data before deletion
        self.component_data = self.controller.model.components.get(self.component_id)
        if self.component_data:
            self.component_data = ComponentData.from_dict(self.component_data.to_dict())

        # Store connected wires before deletion (with their indices)
        self.deleted_wires = []
        for idx, wire in enumerate(self.controller.model.wires):
            if wire.start_component_id == self.component_id or wire.end_component_id == self.component_id:
                self.deleted_wires.append((idx, WireData.from_dict(wire.to_dict())))

        # Delete the component (this also deletes connected wires)
        self.controller.remove_component(self.component_id)

    def undo(self) -> None:
        """Restore the deleted component and its wires."""
        if self.component_data:
            # Restore component directly to model
            self.controller.model.add_component(self.component_data)
            self.controller._notify("component_added", self.component_data)

            # Restore wires
            for _, wire_data in self.deleted_wires:
                self.controller.model.add_wire(wire_data)
                self.controller._notify("wire_added", wire_data)

    def get_description(self) -> str:
        return f"Delete {self.component_id}"


class MoveComponentCommand(Command):
    """Command to move a component to a new position."""

    def __init__(
        self,
        controller,
        component_id: str,
        new_position: tuple[float, float],
        old_position: Optional[tuple[float, float]] = None,
    ):
        self.controller = controller
        self.component_id = component_id
        self.new_position = new_position
        self.old_position = old_position

    def execute(self) -> None:
        """Move the component and store the old position."""
        component = self.controller.model.components.get(self.component_id)
        if component:
            if self.old_position is None:
                self.old_position = component.position
            self.controller.move_component(self.component_id, self.new_position)

    def undo(self) -> None:
        """Restore the old position."""
        if self.old_position:
            self.controller.move_component(self.component_id, self.old_position)

    def get_description(self) -> str:
        return f"Move {self.component_id}"


class RotateComponentCommand(Command):
    """Command to rotate a component."""

    def __init__(self, controller, component_id: str, clockwise: bool = True):
        self.controller = controller
        self.component_id = component_id
        self.clockwise = clockwise

    def execute(self) -> None:
        """Rotate the component."""
        self.controller.rotate_component(self.component_id, self.clockwise)

    def undo(self) -> None:
        """Rotate back in the opposite direction."""
        self.controller.rotate_component(self.component_id, not self.clockwise)

    def get_description(self) -> str:
        direction = "clockwise" if self.clockwise else "counter-clockwise"
        return f"Rotate {self.component_id} {direction}"


class FlipComponentCommand(Command):
    """Command to flip/mirror a component."""

    def __init__(self, controller, component_id: str, horizontal: bool = True):
        self.controller = controller
        self.component_id = component_id
        self.horizontal = horizontal

    def execute(self) -> None:
        """Flip the component."""
        self.controller.flip_component(self.component_id, self.horizontal)

    def undo(self) -> None:
        """Flip back (toggle state)."""
        self.controller.flip_component(self.component_id, self.horizontal)

    def get_description(self) -> str:
        direction = "horizontal" if self.horizontal else "vertical"
        return f"Flip {self.component_id} {direction}"


class ChangeValueCommand(Command):
    """Command to change a component's value."""

    def __init__(self, controller, component_id: str, new_value: str):
        self.controller = controller
        self.component_id = component_id
        self.new_value = new_value
        self.old_value: Optional[str] = None

    def execute(self) -> None:
        """Change the value and store the old value."""
        component = self.controller.model.components.get(self.component_id)
        if component:
            self.old_value = component.value
            self.controller.update_component_value(self.component_id, self.new_value)

    def undo(self) -> None:
        """Restore the old value."""
        if self.old_value is not None:
            self.controller.update_component_value(self.component_id, self.old_value)

    def get_description(self) -> str:
        return f"Change {self.component_id} value"


class AddWireCommand(Command):
    """Command to add a wire connection."""

    def __init__(
        self,
        controller,
        start_comp_id: str,
        start_term: int,
        end_comp_id: str,
        end_term: int,
        waypoints: Optional[list[tuple[float, float]]] = None,
    ):
        self.controller = controller
        self.start_comp_id = start_comp_id
        self.start_term = start_term
        self.end_comp_id = end_comp_id
        self.end_term = end_term
        self.waypoints = waypoints or []
        self.wire_index: Optional[int] = None

    def execute(self) -> None:
        """Add the wire and store its index."""
        self.controller.add_wire(
            self.start_comp_id,
            self.start_term,
            self.end_comp_id,
            self.end_term,
            self.waypoints,
        )
        # Find the index of the newly added wire
        self.wire_index = len(self.controller.model.wires) - 1

    def undo(self) -> None:
        """Remove the added wire."""
        if self.wire_index is not None and self.wire_index < len(self.controller.model.wires):
            self.controller.remove_wire(self.wire_index)

    def get_description(self) -> str:
        return f"Add wire {self.start_comp_id}-{self.end_comp_id}"


class DeleteWireCommand(Command):
    """Command to delete a wire."""

    def __init__(self, controller, wire_index: int):
        self.controller = controller
        self.wire_index = wire_index
        self.wire_data: Optional[WireData] = None

    def execute(self) -> None:
        """Delete the wire and store its data."""
        if self.wire_index < len(self.controller.model.wires):
            wire = self.controller.model.wires[self.wire_index]
            self.wire_data = WireData.from_dict(wire.to_dict())
            self.controller.remove_wire(self.wire_index)

    def undo(self) -> None:
        """Restore the deleted wire at its original index."""
        if self.wire_data:
            # Insert wire at the same index it was removed from
            self.controller.model.wires.insert(self.wire_index, self.wire_data)
            self.controller._notify("wire_added", self.wire_data)

    def get_description(self) -> str:
        return "Delete wire"


class PasteCommand(Command):
    """Command to paste clipboard contents."""

    def __init__(self, controller, offset: tuple[float, float] = (40.0, 40.0)):
        self.controller = controller
        self.offset = offset
        self.pasted_component_ids: list[str] = []
        self.pasted_wire_indices: list[int] = []

    def execute(self) -> None:
        """Paste components and wires, storing their IDs/indices."""
        new_components, new_wires = self.controller.paste_components(self.offset)
        self.pasted_component_ids = [comp.component_id for comp in new_components]
        # Store indices of pasted wires (they're at the end of the wire list)
        wire_count = len(self.controller.model.wires)
        self.pasted_wire_indices = list(range(wire_count - len(new_wires), wire_count))

    def undo(self) -> None:
        """Delete all pasted components and wires."""
        # Delete wires first (in reverse order to preserve indices)
        for wire_idx in sorted(self.pasted_wire_indices, reverse=True):
            if wire_idx < len(self.controller.model.wires):
                self.controller.remove_wire(wire_idx)

        # Delete components
        for comp_id in self.pasted_component_ids:
            if comp_id in self.controller.model.components:
                # Use model directly to avoid deleting wires again
                del self.controller.model.components[comp_id]
                self.controller._notify("component_removed", comp_id)

    def get_description(self) -> str:
        return f"Paste {len(self.pasted_component_ids)} components"


class AddAnnotationCommand(Command):
    """Command to add a text annotation."""

    def __init__(self, controller, annotation_data: AnnotationData):
        self.controller = controller
        self.annotation_data = annotation_data
        self.annotation_index: Optional[int] = None

    def execute(self) -> None:
        self.annotation_index = self.controller.add_annotation(self.annotation_data)

    def undo(self) -> None:
        if self.annotation_index is not None:
            self.controller.remove_annotation(self.annotation_index)

    def get_description(self) -> str:
        return "Add annotation"


class DeleteAnnotationCommand(Command):
    """Command to delete a text annotation."""

    def __init__(self, controller, annotation_index: int):
        self.controller = controller
        self.annotation_index = annotation_index
        self.annotation_data: Optional[AnnotationData] = None

    def execute(self) -> None:
        if self.annotation_index < len(self.controller.model.annotations):
            ann = self.controller.model.annotations[self.annotation_index]
            self.annotation_data = AnnotationData.from_dict(ann.to_dict())
            self.controller.remove_annotation(self.annotation_index)

    def undo(self) -> None:
        if self.annotation_data:
            self.controller.model.annotations.insert(self.annotation_index, self.annotation_data)
            self.controller._notify("annotation_added", self.annotation_data)

    def get_description(self) -> str:
        return "Delete annotation"


class EditAnnotationCommand(Command):
    """Command to edit a text annotation's text."""

    def __init__(self, controller, annotation_index: int, new_text: str):
        self.controller = controller
        self.annotation_index = annotation_index
        self.new_text = new_text
        self.old_text: Optional[str] = None

    def execute(self) -> None:
        if self.annotation_index < len(self.controller.model.annotations):
            self.old_text = self.controller.model.annotations[self.annotation_index].text
            self.controller.update_annotation_text(self.annotation_index, self.new_text)

    def undo(self) -> None:
        if self.old_text is not None:
            self.controller.update_annotation_text(self.annotation_index, self.old_text)

    def get_description(self) -> str:
        return "Edit annotation"


class CompoundCommand(Command):
    """Command that groups multiple commands into a single undo step."""

    def __init__(self, commands: list[Command], description: str = "Multiple actions"):
        self.commands = commands
        self.description = description

    def execute(self) -> None:
        """Execute all commands in order."""
        for command in self.commands:
            command.execute()

    def undo(self) -> None:
        """Undo all commands in reverse order."""
        for command in reversed(self.commands):
            command.undo()

    def get_description(self) -> str:
        return self.description
