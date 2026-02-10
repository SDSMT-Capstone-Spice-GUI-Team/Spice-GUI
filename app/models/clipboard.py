"""
ClipboardData - Internal clipboard storage for copy/paste operations.

This module contains no Qt dependencies.
"""

from dataclasses import dataclass, field


@dataclass
class ClipboardData:
    """
    Snapshot of components and internal wires for copy/paste.

    Stores serialized dicts (not live objects) so the clipboard
    contents can be pasted multiple times with new IDs each time.
    """

    components: list[dict] = field(default_factory=list)
    wires: list[dict] = field(default_factory=list)
    paste_count: int = 0

    def is_empty(self) -> bool:
        return len(self.components) == 0
