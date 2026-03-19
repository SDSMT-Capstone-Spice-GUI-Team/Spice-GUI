"""Context-menu builder extracted from CircuitCanvasView.

Constructs a QMenu based on what the cursor is over (component, wire,
annotation, node, or empty space).
"""

from GUI.annotation_item import AnnotationItem
from GUI.component_item import ComponentGraphicsItem
from GUI.wire_item import WireItem
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu


def build_context_menu(canvas, scene_pos):
    """Build and return a context menu for *scene_pos* on *canvas*.

    Parameters
    ----------
    canvas : CircuitCanvasView
        The canvas view providing items, controller, and action methods.
    scene_pos : QPointF
        The position in scene coordinates where the user right-clicked.

    Returns
    -------
    QMenu
        A fully populated menu ready to ``exec()``.
    """
    view_pos = canvas.mapFromScene(scene_pos)
    item = canvas.itemAt(view_pos)

    # If a component is right-clicked, emit a signal to show properties
    if isinstance(item, ComponentGraphicsItem):
        canvas.componentRightClicked.emit(item, canvas.mapToGlobal(view_pos))

    menu = QMenu()

    if isinstance(item, ComponentGraphicsItem):
        _build_component_menu(menu, canvas, item)
    elif isinstance(item, AnnotationItem):
        _build_annotation_menu(menu, canvas, item)
    elif isinstance(item, WireItem):
        _build_wire_menu(menu, canvas, item, scene_pos)
    else:
        _build_empty_area_menu(menu, canvas, scene_pos)

    # Paste action (always available when clipboard has content)
    has_clipboard = (
        canvas.controller and canvas.controller.has_clipboard_content()
    ) or not canvas._clipboard.is_empty()
    if has_clipboard:
        paste_action = QAction("Paste", canvas)
        paste_action.triggered.connect(canvas.paste_components)
        menu.addAction(paste_action)

    # Always offer "Add Annotation"
    menu.addSeparator()
    add_ann_action = QAction("Add Annotation", canvas)
    add_ann_action.triggered.connect(lambda: canvas.add_annotation(scene_pos))
    menu.addAction(add_ann_action)

    return menu


def _build_component_menu(menu, canvas, item):
    """Populate *menu* with actions for a right-clicked component."""
    delete_action = QAction(f"Delete {item.component_id}", canvas)
    delete_action.triggered.connect(lambda: canvas.delete_component(item))
    menu.addAction(delete_action)

    menu.addSeparator()

    rotate_cw_action = QAction("Rotate Clockwise (R)", canvas)
    rotate_cw_action.triggered.connect(lambda: canvas.rotate_component(item, True))
    menu.addAction(rotate_cw_action)

    rotate_ccw_action = QAction("Rotate Counter-Clockwise (Shift+R)", canvas)
    rotate_ccw_action.triggered.connect(lambda: canvas.rotate_component(item, False))
    menu.addAction(rotate_ccw_action)

    menu.addSeparator()

    flip_h_action = QAction("Flip Horizontal (F)", canvas)
    flip_h_action.triggered.connect(lambda: canvas.flip_component(item, True))
    menu.addAction(flip_h_action)

    flip_v_action = QAction("Flip Vertical (Shift+F)", canvas)
    flip_v_action.triggered.connect(lambda: canvas.flip_component(item, False))
    menu.addAction(flip_v_action)


def _build_annotation_menu(menu, canvas, item):
    """Populate *menu* with actions for a right-clicked annotation."""
    delete_action = QAction("Delete Annotation", canvas)
    delete_action.triggered.connect(lambda: canvas._delete_annotation(item))
    menu.addAction(delete_action)

    edit_action = QAction("Edit Annotation", canvas)
    edit_action.triggered.connect(lambda: canvas._edit_annotation(item))
    menu.addAction(edit_action)


def _build_wire_menu(menu, canvas, item, scene_pos):
    """Populate *menu* with actions for a right-clicked wire."""
    delete_action = QAction("Delete Wire", canvas)
    delete_action.triggered.connect(lambda: canvas.delete_wire(item))
    menu.addAction(delete_action)

    menu.addSeparator()

    # Lock/Unlock wire path toggle
    if item.model.locked:
        lock_action = QAction("Unlock Wire Path", canvas)
        lock_action.triggered.connect(lambda: canvas.toggle_wire_lock(item, False))
    else:
        lock_action = QAction("Lock Wire Path", canvas)
        lock_action.triggered.connect(lambda: canvas.toggle_wire_lock(item, True))
    menu.addAction(lock_action)

    # Check if multiple wires are selected
    selected_wires = [i for i in canvas.scene().selectedItems() if isinstance(i, WireItem)]
    if len(selected_wires) > 1 and item in selected_wires:
        reroute_action = QAction(f"Reroute Selected Wires ({len(selected_wires)})", canvas)
        reroute_action.triggered.connect(lambda: canvas.reroute_selected_wires(selected_wires))
    else:
        reroute_action = QAction("Reroute Wire", canvas)
        reroute_action.triggered.connect(lambda: canvas.reroute_wire(item))
    menu.addAction(reroute_action)

    if item.node:
        menu.addSeparator()
        current = item.node.get_label()
        label_action = QAction(f"Set Net Name ({current})...", canvas)
        label_action.triggered.connect(lambda: canvas.label_node(item.node))
        menu.addAction(label_action)


def _build_empty_area_menu(menu, canvas, scene_pos):
    """Populate *menu* with actions for an empty-area right-click."""
    # Check if we clicked near a terminal to set its net name
    clicked_node = canvas.find_node_at_position(scene_pos)
    if clicked_node:
        current = clicked_node.get_label()
        label_action = QAction(f"Set Net Name ({current})...", canvas)
        label_action.triggered.connect(lambda: canvas.label_node(clicked_node))
        menu.addAction(label_action)
        menu.addSeparator()

    # No specific item, offer to delete all selected
    selected_items = canvas.scene().selectedItems()
    if selected_items:
        delete_action = QAction(f"Delete Selected ({len(selected_items)} items)", canvas)
        delete_action.triggered.connect(canvas.delete_selected)
        menu.addAction(delete_action)

        # Check if any components are selected
        selected_components = [i for i in selected_items if isinstance(i, ComponentGraphicsItem)]
        if selected_components:
            menu.addSeparator()
            rotate_cw_action = QAction("Rotate Selected Clockwise", canvas)
            rotate_cw_action.triggered.connect(lambda: canvas.rotate_selected(True))
            menu.addAction(rotate_cw_action)

            rotate_ccw_action = QAction("Rotate Selected Counter-Clockwise", canvas)
            rotate_ccw_action.triggered.connect(lambda: canvas.rotate_selected(False))
            menu.addAction(rotate_ccw_action)

            flip_h_action = QAction("Flip Selected Horizontal", canvas)
            flip_h_action.triggered.connect(lambda: canvas.flip_selected(True))
            menu.addAction(flip_h_action)

            flip_v_action = QAction("Flip Selected Vertical", canvas)
            flip_v_action.triggered.connect(lambda: canvas.flip_selected(False))
            menu.addAction(flip_v_action)

            menu.addSeparator()
            sel_ids = [c.component_id for c in selected_components]
            copy_action = QAction(
                f"Copy ({len(selected_components)} component{'s' if len(selected_components) != 1 else ''})",
                canvas,
            )
            copy_action.triggered.connect(lambda checked=False, ids=sel_ids: canvas.copy_selected_components(ids))
            menu.addAction(copy_action)

            cut_action = QAction(
                f"Cut ({len(selected_components)} component{'s' if len(selected_components) != 1 else ''})",
                canvas,
            )
            cut_action.triggered.connect(lambda checked=False, ids=sel_ids: canvas.cut_selected_components(ids))
            menu.addAction(cut_action)
