"""GUI-layer registration for subcircuit components.

Handles registering subcircuit definitions into Qt-dependent structures:
  - GUI.styles.constants (COMPONENTS, _COLOR_KEYS)
  - GUI.component_item (COMPONENT_CLASSES)
  - GUI.renderers (renderer factories)

Separated from models.subcircuit_library (issue #767) so that the model
layer has zero imports from the GUI layer.

Call :func:`register_subcircuit_gui` from GUI code after calling
``models.subcircuit_library.register_subcircuit_component`` to complete
the full registration pipeline.
"""

from models.subcircuit_library import SubcircuitDefinition, _generate_terminal_geometry


def register_subcircuit_gui(defn: SubcircuitDefinition) -> None:
    """Register a subcircuit definition into all GUI-layer structures.

    Safe to call when Qt is not available — all GUI imports are guarded by
    try/except so this function is a no-op in headless environments.

    Args:
        defn: The subcircuit definition to register.
    """
    name = defn.name

    # Register into styles constants
    try:
        from GUI.styles.constants import _COLOR_KEYS, COMPONENTS

        _COLOR_KEYS[name] = "component_subcircuit"
        COMPONENTS[name] = {
            "symbol": "X",
            "terminals": defn.terminal_count,
            "color_key": "component_subcircuit",
        }
    except (ImportError, AttributeError):
        pass  # OK if GUI not available (headless tests)

    _register_graphics(name, defn)


def _register_graphics(name: str, defn: SubcircuitDefinition) -> None:
    """Register a ComponentGraphicsItem subclass and renderer for *name*."""
    try:
        from GUI.component_item import COMPONENT_CLASSES, ComponentGraphicsItem

        # Create a dynamic subclass for this subcircuit type
        if name not in COMPONENT_CLASSES:
            cls = type(
                f"Subcircuit_{name}",
                (ComponentGraphicsItem,),
                {
                    "type_name": name,
                    "__init__": lambda self, component_id, model=None, _tn=name: ComponentGraphicsItem.__init__(
                        self, component_id, _tn, model=model
                    ),
                },
            )
            COMPONENT_CLASSES[name] = cls
    except (ImportError, AttributeError):
        pass  # GUI not importable in headless/model-only tests

    try:
        from GUI.renderers import _make_iec_delegate, register

        _register_subcircuit_renderer(name, defn, register, _make_iec_delegate)
    except (ImportError, AttributeError):
        pass


def _register_subcircuit_renderer(name, defn, register_fn, make_iec_delegate_fn):
    """Register IEEE + IEC renderers for a subcircuit component."""
    from GUI.renderers import ComponentRenderer, _bounding_rect_obstacle

    class SubcircuitRenderer(ComponentRenderer):
        """Generic box renderer for subcircuit components."""

        def __init__(self, defn):
            self._defn = defn

        def draw(self, painter, component):
            # Draw a rectangular box
            painter.drawRect(-18, -15, 36, 30)

            # Draw terminal connection lines
            if component.scene() is not None:
                tc = self._defn.terminal_count
                if tc == 2:
                    painter.drawLine(-30, 0, -18, 0)
                    painter.drawLine(18, 0, 30, 0)
                elif tc == 3:
                    painter.drawLine(-30, -10, -18, -10)
                    painter.drawLine(-30, 10, -18, 10)
                    painter.drawLine(18, 0, 30, 0)
                else:
                    # Draw leads for custom terminal positions
                    geom = self._defn and _generate_terminal_geometry(tc)
                    if geom and geom[2]:
                        for tx, ty in geom[2]:
                            if tx < 0:
                                painter.drawLine(int(tx), int(ty), -18, int(ty))
                            else:
                                painter.drawLine(18, int(ty), int(tx), int(ty))

            # Draw subcircuit name inside the box
            from PyQt6.QtCore import QRectF

            painter.drawText(QRectF(-16, -12, 32, 24), 0x0084, self._defn.name)

        def get_obstacle_shape(self, component):
            return _bounding_rect_obstacle(component)

    renderer = SubcircuitRenderer(defn)
    try:
        register_fn(name, "ieee", renderer)
        register_fn(name, "iec", make_iec_delegate_fn(renderer))
    except (TypeError, ValueError, KeyError, RuntimeError):
        pass
