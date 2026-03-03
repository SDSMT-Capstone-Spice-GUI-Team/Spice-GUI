from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView

import app.algorithms.path_finding
import app.controllers.circuit_controller
import app.controllers.commands
import app.GUI.styles.constants
import app.models.annotation
import app.models.component
import app.models.node
import app.models.wire
import app.protocols.canvas
import app.protocols.events
from app.GUI.styles import theme_manager


class CircuitCanvasViewRebuild(QGraphicsView):
    def __init__(self, controller=None):
        super().__init__()

        # Init Objects
        self.controller = controller
        self.controller.add_observer(self._on_model_changed)

        # Init Canvas Scene
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        # Importing Constants from constants when needed, makes reading easier
        grid_constant = app.GUI.styles.constants.GRID_EXTENT
        self.setSceneRect(-grid_constant, -grid_constant, grid_constant * 2, grid_constant * 2)
        # Render Hints help with adding anti-aliasing
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        # Disable Dragging
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        # Draw Grid
        self.__draw_grid()

    # Dummy function atm, used to help with initialize
    def _on_model_changed(self, event: str, data) -> None:
        return

    # Helper private function to draw the grid
    def __draw_grid(self):
        # Grab themes from app.GUI.styles
        _minor_pen = theme_manager.pen("grid_minor")
        _major_pen = theme_manager.pen("grid_major")
        _grid_label_color = theme_manager.color("grid_label")
        _grid_label_font = theme_manager.font("grid_label")
