from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsTextItem

import app.models.component
import app.models.wire
import app.models.node
import app.models.annotation

import app.controllers.circuit_controller
import app.controllers.commands

import app.algorithms.path_finding

import app.GUI.styles.constants

import app.protocols.canvas
import app.protocols.events
from app.GUI.styles import theme_manager

class CircuitCanvasViewRebuild(QGraphicsView):
    def __init__(self, controller=None):
        super().__init__()

        #Init Objects
        self.controller = controller
        #self.controller.add_observer(self._on_model_changed)

        #Init Canvas Scene
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        #Importing Constants from constants when needed, makes reading easier
        grid_constant = app.GUI.styles.constants.GRID_EXTENT
        self.setSceneRect(-grid_constant, -grid_constant, grid_constant*2, grid_constant*2)
        #Render Hints help with adding anti-aliasing
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        #Disable Dragging
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        #Draw Grid
        self._grid_items = []
        self._draw_grid()

    #Dummy function atm, used to help with initialize
    def _on_model_changed(self, event: str, data) -> None:
        return

    #Helper private function to draw the grid
    def _draw_grid(self):
        #Grab themes from app.GUI.styles
        minor_pen = theme_manager.pen("grid_minor")
        major_pen = theme_manager.pen("grid_major")
        grid_label_color = theme_manager.color("grid_label")
        grid_label_font = theme_manager.font("grid_label")

        #Grab constants
        grid_extent = app.GUI.styles.constants.GRID_EXTENT
        grid_size = app.GUI.styles.constants.GRID_SIZE
        major_grid_interval = app.GUI.styles.constants.MAJOR_GRID_INTERVAL
        #Make this a constant
        behind_components = -1

        #Draw Verts and Horz
        for i in range(-grid_extent, grid_extent + 1, grid_size):
            #Check if we are on a major grid line
            is_major = i % major_grid_interval == 0
            if is_major:
                #Draw Vertical Line, item because we might need the append later
                line = self.scene.addLine(i, -grid_extent, i, grid_extent, major_pen)
                #Don't understand need for _grid_items, might show up later on, commented for now
                #self._grid_items.append(line)

                #Draw Horizontal Line
                line = self.scene.addLine(-grid_extent, i, grid_extent, i, major_pen)
                #self._grid_items.append(line)

                #NOTE:
                #Labels need to change how the -500 works, as it is rendered doubly,
                #when fixing the positioning, change this too

                #Add Label
                labelY = QGraphicsTextItem(str(i))
                labelY.setDefaultTextColor(grid_label_color)
                labelY.setFont(grid_label_font)
                #Place on Vertical
                #This is a brute force way to "center" the label pos, need to figure out better
                labelY.setPos(i - 15, -grid_extent)
                labelY.setZValue(behind_components)
                self.scene.addItem(labelY)
                #Don't understand this, it will render if commented
                #self._grid_items.append(label)

                #Place on Horizontal
                labelX = QGraphicsTextItem(str(i))
                labelX.setDefaultTextColor(grid_label_color)
                labelX.setFont(grid_label_font)
                #Same as Vertical, need to figure out better way to position
                labelX.setPos(-grid_extent, i - 10)
                labelX.setZValue(behind_components)
                self.scene.addItem(labelX)
                #self._grid_items.append(label)
            else:
                #Draw Vertical Line, same as major
                line = self.scene.addLine(i, -grid_extent, i, grid_extent, minor_pen)
                #self._grid_items.append(line)

                #Draw Horizontal Line, same as major
                line = self.scene.addLine(-grid_extent, i, grid_extent, i, minor_pen)
                #self._grid_items.append(line)