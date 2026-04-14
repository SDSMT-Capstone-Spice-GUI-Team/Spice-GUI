"""
Pure-function circuit connectivity analysis.

Detects floating (unconnected) terminals and other connectivity issues.
No Qt or GUI dependency — operates on model data structures only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.component import ComponentData
    from models.node import NodeData


def find_floating_terminals(
    components: dict[str, ComponentData],
    terminal_to_node: dict[tuple[str, int], NodeData],
) -> set[tuple[str, int]]:
    """Return the set of terminals that are not connected to any node.

    Ground components are excluded since they implicitly connect to node 0.

    Args:
        components: Map of component_id → ComponentData.
        terminal_to_node: Map of (component_id, terminal_index) → NodeData.

    Returns:
        Set of ``(component_id, terminal_index)`` tuples for unconnected terminals.
    """
    floating: set[tuple[str, int]] = set()
    for comp in components.values():
        if comp.component_type == "Ground":
            continue
        for tidx in range(comp.get_terminal_count()):
            key = (comp.component_id, tidx)
            if key not in terminal_to_node:
                floating.add(key)
    return floating
