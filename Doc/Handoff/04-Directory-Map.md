# Directory Map

```
Spice-GUI/
│
├── app/                            ← Main application package
│   ├── main.py                     ← Entry point
│   ├── cli.py                      ← CLI for batch/headless operations
│   ├── requirements.txt            ← Runtime dependencies
│   ├── requirements-dev.txt        ← Dev dependencies
│   │
│   ├── models/                     ← Data layer (pure Python, no Qt)
│   │   ├── circuit.py              ←   CircuitModel — single source of truth
│   │   ├── component.py            ←   ComponentData + SPICE_SYMBOLS
│   │   ├── wire.py                 ←   WireData
│   │   ├── node.py                 ←   NodeData + NodeLabelGenerator
│   │   ├── annotation.py           ←   Canvas annotations
│   │   ├── clipboard.py            ←   Copy/paste data
│   │   ├── assignment.py           ←   Assignment/grading model
│   │   ├── template.py             ←   Circuit templates
│   │   ├── grading_session.py      ←   Grading state
│   │   ├── subcircuit_library.py   ←   Subcircuit definitions
│   │   └── circuit_schema_validator.py
│   │
│   ├── controllers/                ← Business logic (pure Python, no Qt)
│   │   ├── circuit_controller.py   ←   Component/wire CRUD + observer
│   │   ├── simulation_controller.py←   Simulation pipeline
│   │   ├── file_controller.py      ←   File I/O + session persistence
│   │   ├── commands.py             ←   Command pattern (undo/redo)
│   │   ├── undo_manager.py         ←   Undo/redo stack
│   │   ├── keybindings.py          ←   Keyboard shortcut registry
│   │   ├── theme_controller.py     ←   Theme switching logic
│   │   ├── settings_service.py     ←   QSettings bridge
│   │   ├── template_controller.py  ←   Template operations
│   │   ├── template_manager.py     ←   Template file management
│   │   ├── assignment_controller.py←   Assignment management
│   │   └── recent_exports.py       ←   Recent file tracking
│   │
│   ├── GUI/                        ← PyQt6 views (largest module)
│   │   ├── main_window.py          ←   MainWindow + 8 mixin files
│   │   ├── circuit_canvas.py       ←   QGraphicsView (circuit drawing)
│   │   ├── component_item.py       ←   QGraphicsItem (component rendering)
│   │   ├── wire_item.py            ←   QGraphicsItem (wire rendering)
│   │   ├── component_palette.py    ←   Draggable component source
│   │   ├── properties_panel.py     ←   Component property editor
│   │   ├── results_panel.py        ←   Simulation results display
│   │   ├── analysis_dialog.py      ←   Analysis type selector
│   │   ├── waveform_dialog.py      ←   Waveform configuration
│   │   ├── preferences_dialog.py   ←   User settings
│   │   ├── styles/                 ←   Theming system
│   │   │   ├── theme.py            ←     Abstract theme interface
│   │   │   ├── dark_theme.py       ←     Dark theme colors
│   │   │   ├── light_theme.py      ←     Light theme colors
│   │   │   ├── dark_theme.qss      ←     Dark QSS stylesheet
│   │   │   ├── light_theme.qss     ←     Light QSS stylesheet
│   │   │   └── constants.py        ←     Grid size, canvas size
│   │   └── ... (20+ dialog files)
│   │
│   ├── simulation/                 ← SPICE pipeline (pure Python, no Qt)
│   │   ├── netlist_generator.py    ←   CircuitModel → SPICE netlist
│   │   ├── ngspice_runner.py       ←   Run ngspice subprocess
│   │   ├── result_parser.py        ←   Parse ngspice output
│   │   ├── circuit_semantic_validator.py
│   │   ├── csv_exporter.py         ←   Export formats...
│   │   ├── excel_exporter.py
│   │   ├── asc_exporter.py         ←   LTSpice format
│   │   ├── circuitikz_exporter.py  ←   LaTeX format
│   │   ├── fft_analysis.py         ←   FFT computation
│   │   ├── monte_carlo.py          ←   Monte Carlo simulation
│   │   └── ... (more exporters/analysis)
│   │
│   ├── grading/                    ← Educational auto-grading (no Qt)
│   │   ├── grader.py               ←   Main grading engine
│   │   ├── rubric.py               ←   Rubric data structure
│   │   ├── circuit_comparer.py     ←   Compare student circuits
│   │   ├── batch_grader.py         ←   Grade multiple submissions
│   │   └── ... (feedback, export, histograms)
│   │
│   ├── algorithms/                 ← Graph algorithms (no Qt)
│   │   ├── path_finding.py         ←   IDA* wire routing
│   │   └── graph_ops.py            ←   Node graph operations
│   │
│   ├── scripting/                  ← Headless API (no Qt)
│   │   ├── circuit.py              ←   Programmatic circuit creation
│   │   └── jupyter.py              ←   Jupyter notebook integration
│   │
│   ├── services/                   ← Cross-cutting services
│   │   ├── theme_manager.py        ←   Theme singleton
│   │   └── report_generator.py     ←   Report creation
│   │
│   ├── protocols/                  ← Type contracts (no Qt)
│   │   └── application.py, canvas.py, dialogs.py, ...
│   │
│   ├── utils/                      ← Shared utilities (no Qt)
│   │   ├── format_utils.py         ←   SI unit parsing (1k → 1000)
│   │   ├── connectivity.py         ←   Wire connectivity helpers
│   │   └── constants.py            ←   Global constants
│   │
│   ├── tests/                      ← Test suite
│   │   ├── unit/                   ←   142 unit test files
│   │   └── integration/            ←   4 integration test files
│   │
│   ├── templates/                  ← 7 built-in circuit templates (JSON)
│   └── examples/                   ← Example circuit files
│
├── data/                           ← Example circuits (JSON)
├── docs/                           ← Architecture Decision Records
├── wiki/                           ← User-facing documentation
├── Doc/                            ← Legacy docs + this handoff
├── scripts/                        ← Build/dev scripts
│
├── Makefile                        ← Build targets
├── pyproject.toml                  ← Pytest config
├── ruff.toml                       ← Linter config
├── .pre-commit-config.yaml         ← Git hooks
└── README.md
```