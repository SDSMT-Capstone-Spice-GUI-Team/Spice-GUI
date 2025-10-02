import sys
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsItem,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QFileDialog,
    QStyleOptionGraphicsItem,
)
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPen, QColor, QPainter
from PyQt6.QtGui import QCursor
import json
import uuid
from PyQt6.QtWidgets import QCheckBox


class BaseComponentItem(QGraphicsItem):
    """Base class for components providing pin infrastructure and basic selection/moving."""
    def __init__(self, x, y, w=60, h=24, label="R", uid=None):
        super().__init__()
        self._w = w
        self._h = h
        self.setPos(x, y)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        )
        # unique id for serialization and connection tracking (stable string UUID)
        self.uid = uid or str(uuid.uuid4())
        # wires attached: list of (WireItem, pin_index or None)
        self._attached_wires = []
        self.label = label
        # UX: accept hover and show open-hand cursor
        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))

    def boundingRect(self):
        return QRectF(-self._w/2, -self._h/2, self._w, self._h)

    def pins(self):
        """Return list of pin positions in local coordinates."""
        # default: two pins left/right
        return [QPointF(-self._w/2, 0), QPointF(self._w/2, 0)]

    def pin_scene_positions(self):
        return [self.mapToScene(p) for p in self.pins()]

    def itemChange(self, change, value):
        # update attached wires when the item moves
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # value is the new position (QPointF)
            for wire, pin_idx in list(self._attached_wires):
                if pin_idx is None:
                    continue
                # compute new pin pos and update wire
                pin_pos = self.pin_scene_positions()[pin_idx]
                wire.update_endpoint(self.uid, pin_idx, pin_pos)
        return super().itemChange(change, value)

    def attach_wire(self, wire, pin_idx):
        self._attached_wires.append((wire, pin_idx))

    def detach_wire(self, wire):
        self._attached_wires = [(w, idx) for (w, idx) in self._attached_wires if w is not wire]

    # Hover and press UI feedback
    def hoverEnterEvent(self, event):
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        # show closed hand while dragging
        self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        super().mouseReleaseEvent(event)

    def to_dict(self):
        return {"type": "component", "uid": str(self.uid), "label": self.label, "value": getattr(self, "value", None), "x": self.pos().x(), "y": self.pos().y()}


class WireItem(QGraphicsLineItem):
    """Wire with endpoint references.

    Each endpoint is either a dict {"comp": uid, "pin": idx} or a raw point {"x": float, "y": float}.
    """
    def __init__(self, ep1, ep2):
        # ep1/ep2: either QPointF or endpoint dicts
        p1 = ep1 if isinstance(ep1, QPointF) else QPointF(ep1["x"], ep1["y"]) if isinstance(ep1, dict) and "x" in ep1 else QPointF(0,0)
        p2 = ep2 if isinstance(ep2, QPointF) else QPointF(ep2["x"], ep2["y"]) if isinstance(ep2, dict) and "x" in ep2 else QPointF(0,0)
        super().__init__(p1.x(), p1.y(), p2.x(), p2.y())
        self.setPen(QPen(Qt.GlobalColor.black, 2))
        # store endpoints as either {'comp':uid,'pin':idx} or {'x':..,'y':..}
        self.ep1 = ep1 if isinstance(ep1, dict) else {"x": p1.x(), "y": p1.y()}
        self.ep2 = ep2 if isinstance(ep2, dict) else {"x": p2.x(), "y": p2.y()}

    def update_endpoint(self, comp_uid, pin_idx, scene_pos: QPointF):
        changed = False
        if isinstance(self.ep1, dict) and self.ep1.get("comp") == comp_uid and self.ep1.get("pin") == pin_idx:
            self.ep1 = {"comp": comp_uid, "pin": pin_idx}
            # set line start to scene_pos
            line = self.line()
            self.setLine(scene_pos.x(), scene_pos.y(), line.x2(), line.y2())
            changed = True
        if isinstance(self.ep2, dict) and self.ep2.get("comp") == comp_uid and self.ep2.get("pin") == pin_idx:
            self.ep2 = {"comp": comp_uid, "pin": pin_idx}
            line = self.line()
            self.setLine(line.x1(), line.y1(), scene_pos.x(), scene_pos.y())
            changed = True
        return changed

    def resolve_positions(self, scene):
        """Resolve endpoint dicts that refer to component uids into actual scene coords."""
        def resolve(ep):
            if ep is None:
                return None
            if "comp" in ep:
                # find component by uid
                for it in scene.items():
                    if isinstance(it, BaseComponentItem) and getattr(it, "uid", None) == ep["comp"]:
                        pins = it.pin_scene_positions()
                        idx = ep.get("pin", 0)
                        if 0 <= idx < len(pins):
                            # register attachment on the component
                            it.attach_wire(self, idx)
                            return pins[idx]
                return None
            if "x" in ep and "y" in ep:
                return QPointF(ep["x"], ep["y"])
            return None

        p1 = resolve(self.ep1)
        p2 = resolve(self.ep2)
        if p1 and p2:
            self.setLine(p1.x(), p1.y(), p2.x(), p2.y())

    def to_dict(self):
        return {"type": "wire", "ep1": self.ep1, "ep2": self.ep2}


class ResistorItem(BaseComponentItem):
    def __init__(self, x, y, uid=None):
        super().__init__(x, y, w=70, h=20, label="R", uid=uid)

    def paint(self, painter, option, widget=None):
        # simple resistor rectangle with label and pins
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(QColor("#f7f7f7"))
        rect = QRectF(-self._w/2, -self._h/2, self._w, self._h)
        painter.drawRect(rect)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.label)
        # draw pins
        pins = self.pins()
        for p in pins:
            painter.drawEllipse(p, 3, 3)


class CapacitorItem(BaseComponentItem):
    def __init__(self, x, y, uid=None):
        super().__init__(x, y, w=60, h=30, label="C", uid=uid)

    def paint(self, painter, option, widget=None):
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        # two plates
        x_off = 10
        painter.drawLine(QPointF(-x_off, -self._h/2 + 2), QPointF(-x_off, self._h/2 - 2))
        painter.drawLine(QPointF(x_off, -self._h/2 + 2), QPointF(x_off, self._h/2 - 2))
        painter.drawText(QRectF(-self._w/2, -self._h/2, self._w, self._h), Qt.AlignmentFlag.AlignCenter, self.label)
        for p in self.pins():
            painter.drawEllipse(p, 3, 3)


class GroundItem(BaseComponentItem):
    def __init__(self, x, y, uid=None):
        super().__init__(x, y, w=30, h=12, label="GND", uid=uid)

    def paint(self, painter, option, widget=None):
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        # simple ground symbol: three horizontal lines
        painter.drawLine(QPointF(-10, -2), QPointF(10, -2))
        painter.drawLine(QPointF(-6, 2), QPointF(6, 2))
        painter.drawLine(QPointF(-2, 6), QPointF(2, 6))
        painter.drawText(QRectF(-self._w/2, -self._h/2, self._w, self._h), Qt.AlignmentFlag.AlignCenter, self.label)


class CanvasView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self._scene = scene
        self.drawing = False
        self.temp_line = None
        self.start_pos = None
        self.wire_mode = False
        self.left_start = None

    def find_nearest_pin(self, pos: QPointF, threshold=12):
        nearest = None
        best_dist = threshold
        for it in self._scene.items():
            if isinstance(it, BaseComponentItem):
                pins = it.pin_scene_positions()
                for idx, pin in enumerate(pins):
                    d = (pin - pos).manhattanLength()
                    if d < best_dist:
                        best_dist = d
                        nearest = (it, idx, pin)
        return nearest

    def mousePressEvent(self, ev):
        # Start wire-drawing only when right-clicking on empty canvas OR when left-click in wire_mode
        if ev.button() == Qt.MouseButton.RightButton or (ev.button() == Qt.MouseButton.LeftButton and self.wire_mode):
            scene_pos = self.mapToScene(ev.position().toPoint())
            clicked_item = self._scene.itemAt(scene_pos, self.transform())
            # climb parent chain so child shapes inside a component are treated as the component
            parent = clicked_item
            while parent is not None and not isinstance(parent, BaseComponentItem):
                parent = parent.parentItem()
            clicked_item = parent
            # If clicking on a component (or its child), don't start wire mode (allow selection/drag)
            # If wire_mode and left-click on component pin, begin pin-to-pin wire
            if ev.button() == Qt.MouseButton.LeftButton and self.wire_mode:
                # if clicked_item is a component, start from nearest pin
                if clicked_item is not None:
                    # find nearest pin on this component
                    pins = clicked_item.pin_scene_positions()
                    best_idx, best_p = 0, pins[0]
                    best_d = (best_p - scene_pos).manhattanLength()
                    for idx, p in enumerate(pins):
                        d = (p - scene_pos).manhattanLength()
                        if d < best_d:
                            best_d = d
                            best_idx, best_p = idx, p
                    self.left_start = (clicked_item, best_idx, best_p)
                    # create temp line
                    self.temp_line = QGraphicsLineItem(best_p.x(), best_p.y(), best_p.x(), best_p.y())
                    self.temp_line.setPen(QPen(Qt.GlobalColor.darkGray, 1, Qt.PenStyle.DashLine))
                    self._scene.addItem(self.temp_line)
                    return
                else:
                    # start freepoint wire
                    self.drawing = True
                    self.start_pos = scene_pos
                    self.temp_line = QGraphicsLineItem(self.start_pos.x(), self.start_pos.y(), self.start_pos.x(), self.start_pos.y())
                    self.temp_line.setPen(QPen(Qt.GlobalColor.darkGray, 1, Qt.PenStyle.DashLine))
                    self._scene.addItem(self.temp_line)
                    return
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if (self.drawing or self.left_start) and self.temp_line:
            pos = self.mapToScene(ev.position().toPoint())
            if self.left_start:
                # rubber band from start pin
                self.temp_line.setLine(self.left_start[2].x(), self.left_start[2].y(), pos.x(), pos.y())
            else:
                self.temp_line.setLine(self.start_pos.x(), self.start_pos.y(), pos.x(), pos.y())
        else:
            super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        # handle left-click finish in wire_mode
        if ev.button() == Qt.MouseButton.LeftButton and self.wire_mode and self.left_start:
            end_pos = self.mapToScene(ev.position().toPoint())
            clicked_item = self._scene.itemAt(end_pos, self.transform())
            parent = clicked_item
            while parent is not None and not isinstance(parent, BaseComponentItem):
                parent = parent.parentItem()
            clicked_item = parent
            start_comp, start_pin, start_pos = self.left_start
            if clicked_item is not None:
                # find nearest pin on clicked_item
                pins = clicked_item.pin_scene_positions()
                best_idx, best_p = 0, pins[0]
                best_d = (best_p - end_pos).manhattanLength()
                for idx, p in enumerate(pins):
                    d = (p - end_pos).manhattanLength()
                    if d < best_d:
                        best_d = d
                        best_idx, best_p = idx, p
                ep1 = {"comp": start_comp.uid, "pin": start_pin}
                ep2 = {"comp": clicked_item.uid, "pin": best_idx}
                w = WireItem(ep1, ep2)
                self._scene.addItem(w)
                start_comp.attach_wire(w, start_pin)
                clicked_item.attach_wire(w, best_idx)
            else:
                # finish at freepoint
                ep1 = {"comp": start_comp.uid, "pin": start_pin}
                ep2 = {"x": end_pos.x(), "y": end_pos.y()}
                w = WireItem(ep1, ep2)
                self._scene.addItem(w)
                start_comp.attach_wire(w, start_pin)

            if self.temp_line:
                self._scene.removeItem(self.temp_line)
                self.temp_line = None
            self.left_start = None
            return

        # fallback: original right-click drag behavior
        if ev.button() == Qt.MouseButton.RightButton and self.drawing:
            end_pos = self.mapToScene(ev.position().toPoint())
            # snapping: find component and pin for start and end
            s = self.find_nearest_pin(self.start_pos)
            e = self.find_nearest_pin(end_pos)
            if s:
                comp_s, pin_s, pinpos_s = s
                ep1 = {"comp": comp_s.uid, "pin": pin_s}
            else:
                ep1 = {"x": self.start_pos.x(), "y": self.start_pos.y()}
            if e:
                comp_e, pin_e, pinpos_e = e
                ep2 = {"comp": comp_e.uid, "pin": pin_e}
            else:
                ep2 = {"x": end_pos.x(), "y": end_pos.y()}

            w = WireItem(ep1, ep2)
            self._scene.addItem(w)
            # register attachments on components
            if s:
                comp_s.attach_wire(w, pin_s)
            if e:
                comp_e.attach_wire(w, pin_e)

            if self.temp_line:
                self._scene.removeItem(self.temp_line)
                self.temp_line = None
            self.drawing = False
            self.start_pos = None
            return

        super().mouseReleaseEvent(ev)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spice GUI - Diagram Prototype")
        self.resize(1000, 700)

        central = QWidget()
        self.setCentralWidget(central)

        h = QHBoxLayout(central)

        # Left palette
        left = QVBoxLayout()
        palette = QListWidget()
        palette.addItem(QListWidgetItem("Resistor (R)"))
        palette.addItem(QListWidgetItem("Capacitor (C)"))
        palette.addItem(QListWidgetItem("Ground"))
        left.addWidget(palette)

        wire_mode_checkbox = QCheckBox("Wire Mode (click pins)")
        left.addWidget(wire_mode_checkbox)

        btn_save = QPushButton("Save JSON")
        btn_load = QPushButton("Load JSON")
        left.addWidget(btn_save)
        left.addWidget(btn_load)

        h.addLayout(left, 1)

        # Canvas
        self.scene = QGraphicsScene()
        self.view = CanvasView(self.scene)
        # enable antialiasing for nicer lines
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        h.addWidget(self.view, 4)

        # Connect signals
        palette.itemDoubleClicked.connect(self.on_palette_double)
        btn_save.clicked.connect(self.on_save)
        btn_load.clicked.connect(self.on_load)
        wire_mode_checkbox.stateChanged.connect(lambda s: setattr(self.view, 'wire_mode', s == 2))

        # Wire drawing state
        self.drawing_wire = False
        self.wire_start = None

    def on_palette_double(self, item: QListWidgetItem):
        text = item.text()
        # place component in center of view
        center = self.view.mapToScene(self.view.viewport().rect().center())
        if "Resistor" in text:
            c = ResistorItem(center.x(), center.y())
        elif "Capacitor" in text:
            c = CapacitorItem(center.x(), center.y())
        else:
            c = GroundItem(center.x(), center.y())
        self.scene.addItem(c)

    # wire handling moved to CanvasView

    def on_save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save diagram", "", "JSON Files (*.json)")
        if not path:
            return
        data = {"items": []}
        for it in self.scene.items():
            if isinstance(it, BaseComponentItem):
                data["items"].append(it.to_dict())
            elif isinstance(it, WireItem):
                data["items"].append(it.to_dict())
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def on_load(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load diagram", "", "JSON Files (*.json)")
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.scene.clear()
        for itm in data.get("items", []):
            if itm.get("type") == "component":
                lbl = itm.get("label", "R")
                uid = itm.get("uid")
                if lbl == "R":
                    c = ResistorItem(itm["x"], itm["y"], uid=uid)
                elif lbl == "C":
                    c = CapacitorItem(itm["x"], itm["y"], uid=uid)
                else:
                    c = GroundItem(itm["x"], itm["y"], uid=uid)
                # restore value if present
                if itm.get("value"):
                    c.value = itm.get("value")
                self.scene.addItem(c)
            elif itm.get("type") == "wire":
                # wires store ep1/ep2
                ep1 = itm.get("ep1")
                ep2 = itm.get("ep2")
                w = WireItem(ep1, ep2)
                self.scene.addItem(w)
                # resolve positions and register attachments
                w.resolve_positions(self.scene)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
