"""In-app help system: searchable help panel and guided tutorial for MainWindow."""

import logging

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (
    QDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
)

logger = logging.getLogger(__name__)

# ---- Help content organized by topic ----

HELP_TOPICS: list[dict] = [
    {
        "title": "Getting Started",
        "keywords": ["start", "begin", "intro", "overview", "new"],
        "body": (
            "<h2>Getting Started</h2>"
            "<p>Welcome to the Circuit Design GUI!  Use this application to design, "
            "simulate, and analyze electronic circuits.</p>"
            "<ol>"
            "<li><b>Add components</b> — drag them from the <i>Component Palette</i> on the left, "
            "or double-click a component name.</li>"
            "<li><b>Connect wires</b> — click a terminal (the small square at the end of a component), "
            "then click another terminal to draw a wire.</li>"
            "<li><b>Set values</b> — select a component and change its value in the <i>Properties Panel</i> on the right.</li>"
            "<li><b>Run a simulation</b> — choose an analysis type from the <i>Analysis</i> menu, "
            "then click <i>Simulation → Run</i> (or press F5).</li>"
            "</ol>"
        ),
    },
    {
        "title": "Adding Components",
        "keywords": [
            "component",
            "add",
            "drag",
            "palette",
            "resistor",
            "capacitor",
            "place",
        ],
        "body": (
            "<h2>Adding Components</h2>"
            "<p>The <b>Component Palette</b> on the left side lists all available components grouped by category.</p>"
            "<ul>"
            "<li><b>Drag &amp; drop</b> a component from the palette onto the canvas.</li>"
            "<li><b>Double-click</b> a component name to place it at the center of the canvas.</li>"
            "<li>Use the <b>search box</b> at the top of the palette to filter by name or tooltip.</li>"
            "</ul>"
            "<p>Components include resistors, capacitors, inductors, voltage/current sources, "
            "diodes, BJTs, MOSFETs, op-amps, and more.</p>"
        ),
    },
    {
        "title": "Drawing Wires",
        "keywords": ["wire", "connect", "terminal", "waypoint", "bend", "route"],
        "body": (
            "<h2>Drawing Wires</h2>"
            "<p>Wires connect component terminals to form a circuit.</p>"
            "<ol>"
            "<li>Click on a <b>terminal</b> (small square) of a component to start drawing.</li>"
            "<li>Optionally click empty space to place <b>bend points</b> (waypoints).</li>"
            "<li>Click a terminal on another component to <b>complete</b> the wire.</li>"
            "</ol>"
            "<p>Press <b>Escape</b> to cancel an in-progress wire.</p>"
            "<p>After routing, you can <b>select a wire</b> and drag its waypoint handles to reshape it.</p>"
        ),
    },
    {
        "title": "Simulation",
        "keywords": [
            "simulate",
            "run",
            "analysis",
            "dc",
            "ac",
            "transient",
            "netlist",
            "results",
        ],
        "body": (
            "<h2>Running Simulations</h2>"
            "<p>The application generates a SPICE netlist from your circuit and runs it through ngspice.</p>"
            "<ol>"
            "<li>Select an analysis type from the <b>Analysis</b> menu (DC Operating Point, AC Sweep, Transient, etc.).</li>"
            "<li>Configure analysis parameters in the dialog that appears.</li>"
            "<li>Click <b>Simulation → Run Simulation</b> or press <b>F5</b>.</li>"
            "<li>View results in the <b>Results</b> tab at the bottom.</li>"
            "</ol>"
        ),
    },
    {
        "title": "Saving and Loading",
        "keywords": ["save", "load", "open", "file", "export", "import", "json"],
        "body": (
            "<h2>Saving and Loading Circuits</h2>"
            "<p>Circuits are saved as JSON files.</p>"
            "<ul>"
            "<li><b>Ctrl+S</b> — Save the current circuit.</li>"
            "<li><b>Ctrl+Shift+S</b> — Save As (new filename).</li>"
            "<li><b>Ctrl+O</b> — Open an existing circuit file.</li>"
            "<li><b>Ctrl+N</b> — New blank circuit.</li>"
            "</ul>"
            "<p>You can also <b>export</b> your circuit as a SPICE netlist, PDF, LaTeX, PNG, or BOM.</p>"
        ),
    },
    {
        "title": "Keyboard Shortcuts",
        "keywords": [
            "shortcut",
            "key",
            "keyboard",
            "hotkey",
            "keybinding",
            "accelerator",
        ],
        "body": (
            "<h2>Keyboard Shortcuts</h2>"
            "<table border='1' cellpadding='4' cellspacing='0'>"
            "<tr><td><b>Ctrl+N</b></td><td>New circuit</td></tr>"
            "<tr><td><b>Ctrl+O</b></td><td>Open circuit</td></tr>"
            "<tr><td><b>Ctrl+S</b></td><td>Save circuit</td></tr>"
            "<tr><td><b>Ctrl+Z</b></td><td>Undo</td></tr>"
            "<tr><td><b>Ctrl+Shift+Z</b></td><td>Redo</td></tr>"
            "<tr><td><b>Ctrl+C / Ctrl+X / Ctrl+V</b></td><td>Copy / Cut / Paste</td></tr>"
            "<tr><td><b>Delete</b></td><td>Delete selected items</td></tr>"
            "<tr><td><b>R</b></td><td>Rotate selected component</td></tr>"
            "<tr><td><b>H / V</b></td><td>Flip horizontal / vertical</td></tr>"
            "<tr><td><b>F5</b></td><td>Run simulation</td></tr>"
            "<tr><td><b>Escape</b></td><td>Cancel wire drawing</td></tr>"
            "</table>"
        ),
    },
    {
        "title": "Properties Panel",
        "keywords": ["property", "value", "edit", "panel", "change", "component value"],
        "body": (
            "<h2>Properties Panel</h2>"
            "<p>The <b>Properties Panel</b> on the right shows details of the selected component.</p>"
            "<ul>"
            "<li>Select a component on the canvas to display its properties.</li>"
            "<li>Edit the <b>value</b> field to change the component value (e.g., '1k', '10u', '5V').</li>"
            "<li>View the component type, ID, and terminal count.</li>"
            "</ul>"
        ),
    },
    {
        "title": "Themes and Display",
        "keywords": ["theme", "dark", "light", "color", "display", "zoom", "grid"],
        "body": (
            "<h2>Themes and Display</h2>"
            "<p>Customize the application appearance:</p>"
            "<ul>"
            "<li><b>View → Theme</b> — Switch between light and dark themes.</li>"
            "<li><b>View → Wire Thickness</b> — Adjust wire line width.</li>"
            "<li><b>View → Junction Dots</b> — Toggle dots at wire bend points.</li>"
            "<li><b>Ctrl+= / Ctrl+-</b> — Zoom in / out.</li>"
            "<li><b>Ctrl+0</b> — Reset zoom.</li>"
            "</ul>"
        ),
    },
]

# Tutorial steps for the guided walkthrough
TUTORIAL_STEPS: list[dict] = [
    {
        "title": "Step 1: Add a Component",
        "message": "Drag a <b>Resistor</b> from the Component Palette on the left onto the canvas.",
    },
    {
        "title": "Step 2: Add More Components",
        "message": "Add a <b>Voltage Source</b> and a <b>Ground</b> component to the canvas.",
    },
    {
        "title": "Step 3: Connect Wires",
        "message": (
            "Click a terminal on the Voltage Source, then click a terminal on the Resistor to draw a wire. "
            "Repeat to connect all components."
        ),
    },
    {
        "title": "Step 4: Set Values",
        "message": "Select the Resistor and change its value to <b>1k</b> in the Properties Panel.",
    },
    {
        "title": "Step 5: Run Simulation",
        "message": (
            "Go to <b>Analysis → DC Operating Point</b>, then click <b>Simulation → Run</b> (or press F5) "
            "to see results."
        ),
    },
]


class HelpDialog(QDialog):
    """Searchable help dialog with topic list and content viewer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Help — Circuit Design GUI")
        self.resize(QSize(700, 480))
        self._build_ui()
        self._populate_topics(HELP_TOPICS)

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Search bar
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search help topics...")
        self._search.textChanged.connect(self._on_search)
        layout.addWidget(self._search)

        # Splitter: topic list | content
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._topic_list = QListWidget()
        self._topic_list.currentItemChanged.connect(self._on_topic_selected)
        splitter.addWidget(self._topic_list)

        self._content = QTextBrowser()
        self._content.setOpenExternalLinks(True)
        splitter.addWidget(self._content)

        splitter.setSizes([200, 500])
        layout.addWidget(splitter)

    def _populate_topics(self, topics: list[dict]):
        self._topic_list.clear()
        for topic in topics:
            item = QListWidgetItem(topic["title"])
            item.setData(Qt.ItemDataRole.UserRole, topic["body"])
            item.setData(Qt.ItemDataRole.UserRole + 1, topic.get("keywords", []))
            self._topic_list.addItem(item)
        if self._topic_list.count() > 0:
            self._topic_list.setCurrentRow(0)

    def _on_topic_selected(self, current, _previous=None):
        if current is None:
            self._content.setHtml("")
            return
        self._content.setHtml(current.data(Qt.ItemDataRole.UserRole))

    def _on_search(self, text: str):
        text = text.lower()
        for i in range(self._topic_list.count()):
            item = self._topic_list.item(i)
            title = item.text().lower()
            keywords = item.data(Qt.ItemDataRole.UserRole + 1) or []
            matches = not text or text in title or any(text in kw for kw in keywords)
            item.setHidden(not matches)
        # Auto-select first visible
        for i in range(self._topic_list.count()):
            item = self._topic_list.item(i)
            if not item.isHidden():
                self._topic_list.setCurrentItem(item)
                break

    def topic_count(self) -> int:
        """Return the total number of help topics."""
        return self._topic_list.count()

    def visible_topic_count(self) -> int:
        """Return the number of visible (non-hidden) topics."""
        return sum(1 for i in range(self._topic_list.count()) if not self._topic_list.item(i).isHidden())


class HelpMixin:
    """Mixin providing in-app help and guided tutorial for MainWindow."""

    def _show_help(self):
        """Open the searchable Help dialog."""
        dialog = HelpDialog(self)
        dialog.exec()

    def _start_tutorial(self):
        """Run a guided step-by-step tutorial via message boxes."""
        for step in TUTORIAL_STEPS:
            result = QMessageBox.information(
                self,
                step["title"],
                step["message"],
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            )
            if result == QMessageBox.StandardButton.Cancel:
                break
