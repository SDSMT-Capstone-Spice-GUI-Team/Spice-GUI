"""
UndoManager - Manages undo/redo stacks and command execution.

Maintains a history of executed commands with configurable depth limit.
Supports undo, redo, and clearing history.
"""

from typing import Optional

from controllers.commands import Command


class UndoManager:
    """
    Manages command execution with undo/redo support.

    Commands are executed through this manager to ensure they can be undone.
    The manager maintains undo and redo stacks with a maximum depth limit.
    """

    def __init__(self, max_depth: int = 100):
        """
        Initialize the undo manager.

        Args:
            max_depth: Maximum number of commands to keep in history (default 100)
        """
        self.max_depth = max_depth
        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []

    def execute(self, command: Command) -> None:
        """
        Execute a command and add it to the undo stack.

        Clears the redo stack since a new action invalidates any redo history.

        Args:
            command: The command to execute
        """
        command.execute()

        # Add to undo stack
        self._undo_stack.append(command)

        # Enforce max depth
        if len(self._undo_stack) > self.max_depth:
            self._undo_stack.pop(0)

        # Clear redo stack - new actions invalidate redo history
        self._redo_stack.clear()

    def undo(self) -> bool:
        """
        Undo the last command.

        Returns:
            True if an action was undone, False if undo stack is empty
        """
        if not self._undo_stack:
            return False

        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)

        return True

    def redo(self) -> bool:
        """
        Redo the last undone command.

        Returns:
            True if an action was redone, False if redo stack is empty
        """
        if not self._redo_stack:
            return False

        command = self._redo_stack.pop()
        command.execute()
        self._undo_stack.append(command)

        return True

    def can_undo(self) -> bool:
        """Return whether there are commands to undo."""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Return whether there are commands to redo."""
        return len(self._redo_stack) > 0

    def get_undo_description(self) -> Optional[str]:
        """
        Get description of the command that would be undone.

        Returns:
            Description string or None if undo stack is empty
        """
        if self._undo_stack:
            return self._undo_stack[-1].get_description()
        return None

    def get_redo_description(self) -> Optional[str]:
        """
        Get description of the command that would be redone.

        Returns:
            Description string or None if redo stack is empty
        """
        if self._redo_stack:
            return self._redo_stack[-1].get_description()
        return None

    def clear(self) -> None:
        """Clear both undo and redo stacks."""
        self._undo_stack.clear()
        self._redo_stack.clear()

    def get_undo_count(self) -> int:
        """Return the number of commands in the undo stack."""
        return len(self._undo_stack)

    def get_redo_count(self) -> int:
        """Return the number of commands in the redo stack."""
        return len(self._redo_stack)
