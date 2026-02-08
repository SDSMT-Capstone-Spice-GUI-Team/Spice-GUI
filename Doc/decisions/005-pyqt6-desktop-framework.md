# ADR 005: PyQt6 Desktop Application Framework

**Date:** 2024-09-10 (Initial prototype)
**Status:** Accepted
**Deciders:** Development Team
**Related Commits:** fd70174 (PyQt5 → PyQt6 migration)

---

## Context

SDM Spice requires a GUI framework to provide:
- **Drag-and-drop circuit design** canvas
- **Interactive graphics** (components, wires, grid)
- **Real-time visualization** (waveform plots, node voltages)
- **Cross-platform support** (Windows, macOS, Linux)
- **Native performance** (smooth panning, zooming, rendering)

The application is an educational desktop tool for circuit design and simulation. It needs:
- Fast rendering for interactive schematic editing
- Tight integration with matplotlib for waveform plots
- Professional look-and-feel for university use
- Reasonable learning curve for student developers

### Technology Landscape (2024)
- **Python GUI frameworks:** PyQt, Tkinter, wxPython, Kivy
- **Web-based:** Electron, Tauri, PyWebView
- **Cross-platform native:** Qt, GTK, .NET MAUI

---

## Decision

**We will use PyQt6 as the GUI framework for a native desktop application.**

### Key Technology Choices
- **Framework:** PyQt6 (Qt6 Python bindings)
- **Graphics:** QGraphicsView/QGraphicsScene for canvas
- **Plotting:** matplotlib with Qt backend
- **Platform:** Desktop application (Windows, macOS, Linux)

---

## Consequences

### Positive

✅ **Rich widget library:** QGraphicsView perfect for circuit canvas
✅ **High performance:** Native rendering, smooth interaction
✅ **Professional appearance:** Qt widgets look native on each platform
✅ **Excellent documentation:** Qt docs + PyQt examples
✅ **matplotlib integration:** Built-in Qt backend for plots
✅ **Mature ecosystem:** 25+ years of Qt development
✅ **Active development:** Qt6 is latest major version
✅ **Educational:** Students learn industry-standard framework
✅ **Offline-first:** Desktop app works without internet

### Negative

❌ **Installation size:** ~100MB+ for PyQt6 + dependencies
❌ **Distribution complexity:** Must package Qt libs with app
❌ **GPL/Commercial license:** GPL for free, commercial license available
❌ **Learning curve:** Qt concepts (signals/slots, QObject model)
❌ **Platform-specific issues:** Occasional Qt bugs on specific OS versions
❌ **No web version:** Can't run in browser

### Mitigation Strategies

**Installation/Distribution:**
- Use pip for dependencies (simple for developers)
- Future: PyInstaller or similar for bundled executable
- Document installation process clearly in README

**Licensing:**
- GPL acceptable for open-source educational tool
- No commercial distribution planned

**Platform issues:**
- Test on all three platforms (Windows, macOS, Linux)
- CI/CD runs tests on multiple OS
- Document known platform-specific quirks

**Learning curve:**
- Focus on PyQt6 (not Qt/C++) for simplicity
- Provide code examples for common patterns
- Comment code to explain Qt idioms

---

## Alternatives Considered

### Alternative 1: Tkinter (Python Standard Library)
**Approach:** Use built-in Tkinter for GUI

**Pros:**
- No external dependencies
- Simple, lightweight
- Part of Python standard library

**Rejected because:**
- Poor graphics performance (no hardware acceleration)
- Canvas widget too basic for complex circuit schematics
- Dated appearance (doesn't look native)
- Limited matplotlib integration
- No QGraphicsView equivalent for scene management

### Alternative 2: wxPython
**Approach:** Use wxPython (wxWidgets bindings)

**Pros:**
- Native widgets on each platform
- Good documentation
- Active community

**Rejected because:**
- Graphics capabilities inferior to Qt
- Less mature graphics scene management
- Smaller ecosystem than Qt
- Team more familiar with Qt
- Less common in EDA tools

### Alternative 3: Web Application (Electron/React)
**Approach:** Build web UI with Electron or similar

**Pros:**
- Modern web UI (React, Vue)
- Cross-platform by default
- Familiar web technologies (HTML/CSS/JS)
- Easy to add cloud features later

**Rejected because:**
- Much larger installation size (~200MB+ for Electron)
- Worse performance for canvas rendering
- Must bridge Python simulation to JavaScript UI
- Offline experience more complex
- Against local-first architecture (ADR 001)
- Team expertise in Python, not JavaScript
- Canvas performance critical for smooth interaction

### Alternative 4: Dear PyGui / ImGui
**Approach:** Use immediate-mode GUI framework

**Pros:**
- Very fast rendering
- Simple API
- Good for data visualization

**Rejected because:**
- Unconventional UI paradigm (immediate mode)
- Less mature than Qt
- Fewer widgets/components
- Not widely used in desktop applications
- Steeper learning curve for immediate mode concepts

### Alternative 5: Kivy (Mobile-First Framework)
**Approach:** Use Kivy for cross-platform GUI

**Pros:**
- Cross-platform (desktop + mobile)
- Modern design language
- Touch-friendly

**Rejected because:**
- Optimized for mobile, not desktop
- Non-native appearance
- Overkill for desktop-only application
- Smaller community than Qt
- No clear advantage over PyQt6 for this use case

### Alternative 6: GTK (via PyGObject)
**Approach:** Use GTK+ toolkit with Python bindings

**Pros:**
- Open-source, no licensing concerns
- Native on Linux
- Good documentation

**Rejected because:**
- Less polished on Windows/macOS
- Smaller Python ecosystem than Qt
- Graphics capabilities less mature than Qt
- Team unfamiliar with GTK

---

## PyQt6 vs PyQt5

**Why PyQt6 over PyQt5?**

We migrated from PyQt5 → PyQt6 early in development (commit fd70174):

**PyQt6 advantages:**
- Latest Qt version (Qt6, released 2020)
- Long-term support (Qt5 maintenance mode)
- Better high-DPI support
- Modern API improvements
- Future-proof choice

**Migration cost:**
- Enum syntax changes (`Qt.AlignLeft` → `Qt.Alignment.AlignLeft`)
- Minimal breaking changes
- Worth it for long-term support

---

## Implementation Details

### Graphics Architecture
```python
# QGraphicsView for viewport
class CircuitCanvas(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        # Performance optimizations
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)

# Custom graphics items
class ComponentItem(QGraphicsItem):
    def paint(self, painter, option, widget):
        # Custom component rendering
        painter.drawRect(self.boundingRect())
```

### matplotlib Integration
```python
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

class WaveformViewer(QWidget):
    def __init__(self):
        self.figure = Figure()
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
```

### Signals and Slots
```python
# Qt's observer pattern
class PropertiesPanel(QWidget):
    value_changed = pyqtSignal(str, str)  # (component_id, new_value)

    def on_edit_finished(self):
        self.value_changed.emit(self.comp_id, self.value_input.text())

# Connect in main window
properties_panel.value_changed.connect(self.on_component_value_changed)
```

---

## Platform Support

### Windows
- ✅ Fully supported
- ✅ Native look-and-feel
- ✅ High-DPI support

### macOS
- ✅ Fully supported
- ✅ Retina display support
- ⚠️ Requires manual PyQt6 install via pip (not in default Python)

### Linux
- ✅ Fully supported (Ubuntu, Debian, Fedora, Arch)
- ✅ X11 and Wayland
- ⚠️ Requires system libraries: `libegl1`, `libxcb-*`

---

## Performance Optimizations

**Viewport updates:**
```python
# Use minimal updates instead of full viewport redraws
self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
```

**Caching:**
```python
# Cache component rendering
component_item.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
```

**Lazy loading:**
- Defer matplotlib imports until first plot
- Reduces startup time from ~3s to ~1s

**Debouncing:**
- Debounce wire updates during dragging
- Update path only after mouse released

---

## Testing Strategy

**Unit tests (without Qt):**
- Models and controllers have zero PyQt6 dependencies (ADR 002)
- Fast tests run without display server

**GUI tests (with Qt):**
- Use QTest for widget interaction
- Run with xvfb on Linux CI (headless)
- Test critical user flows (add component, connect wire, run sim)

**Platform testing:**
- GitHub Actions: Ubuntu (xvfb), Windows, macOS
- Manual testing on real devices

---

## Future Considerations

### Potential Web Version (Phase 6+)
If web interface needed:
- Keep MVC architecture (ADR 002)
- Models/controllers already Qt-free
- Could add web view layer while keeping desktop version
- Share 80%+ of codebase

### Mobile Support
- Not planned, but Qt has mobile support if needed
- Touch interface would need separate UX design

---

## Related Decisions

- [ADR 001](001-local-first-no-user-accounts.md) - Desktop-first aligns with local architecture
- [ADR 002](002-mvc-architecture-zero-qt-dependencies.md) - Qt only in view layer

---

## References

- PyQt6 documentation: https://www.riverbankcomputing.com/static/Docs/PyQt6/
- Qt6 documentation: https://doc.qt.io/qt-6/
- Migration commit: [fd70174](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/commit/fd70174)
- Circuit canvas: [circuit_canvas.py](../../app/GUI/circuit_canvas.py)
- Main window: [circuit_design_gui.py](../../app/GUI/circuit_design_gui.py)

---

## Review and Revision

This decision should be reviewed if:
- Web version becomes required (not just nice-to-have)
- Qt licensing changes unfavorably
- Performance issues emerge that Qt can't solve
- Team composition changes (all web developers, no Python experience)

**Status:** Excellent fit for current needs, no plans to change
