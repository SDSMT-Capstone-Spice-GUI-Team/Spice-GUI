"""
Observer event contract for CircuitController notifications.

Every view that registers as a CircuitController observer receives
``(event_name: str, data)`` callbacks. This module defines the
complete set of event names and their expected payload types.
"""

from __future__ import annotations

from typing import Literal

# All events emitted by CircuitController._notify
ObserverEvent = Literal[
    "component_added",
    "component_removed",
    "component_moved",
    "component_rotated",
    "component_flipped",
    "component_value_changed",
    "wire_added",
    "wire_removed",
    "wire_routed",
    "wire_lock_changed",
    "wire_reroute_requested",
    "circuit_cleared",
    "nodes_rebuilt",
    "model_loaded",
    "model_saved",
    "simulation_started",
    "simulation_completed",
    "annotation_added",
    "annotation_removed",
    "annotation_updated",
    "net_name_changed",
    "locked_components_changed",
    "recommended_components_changed",
]

# Payload type documentation.
# Import paths are relative to the ``app`` package.
#
#   from models.component import ComponentData
#   from models.wire import WireData
#   from models.node import NodeData
#   from models.annotation import AnnotationData
#   from controllers.simulation_controller import SimulationResult
#
EVENT_PAYLOADS: dict[str, str] = {
    "component_added": "ComponentData",
    "component_removed": "str  # component_id",
    "component_moved": "ComponentData",
    "component_rotated": "ComponentData",
    "component_flipped": "ComponentData",
    "component_value_changed": "ComponentData",
    "wire_added": "WireData",
    "wire_removed": "int  # wire_index",
    "wire_routed": "tuple[int, WireData]  # (wire_index, wire_data)",
    "wire_lock_changed": "tuple[int, bool]  # (wire_index, locked)",
    "wire_reroute_requested": "int  # wire_index",
    "circuit_cleared": "None",
    "nodes_rebuilt": "None",
    "model_loaded": "None",
    "model_saved": "None",
    "simulation_started": "None",
    "simulation_completed": "SimulationResult",
    "annotation_added": "AnnotationData",
    "annotation_removed": "int  # annotation_index",
    "annotation_updated": "AnnotationData",
    "net_name_changed": "NodeData",
    "locked_components_changed": "list[str]  # component_ids",
    "recommended_components_changed": "list[str]  # component_types",
}
