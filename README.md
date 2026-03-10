# SDM Spice

**South Dakota Mines Spice** - An open-source circuit design and simulation platform for electrical engineering education.

[![CI](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/actions/workflows/ci.yml/badge.svg)](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.9+-green.svg)](https://pypi.org/project/PyQt6/)
[![License](https://img.shields.io/badge/License-Open%20Source-brightgreen.svg)](LICENSE)

## Overview

SDM Spice is a desktop application developed at South Dakota School of Mines and Technology (SDSMT) that provides an intuitive drag-and-drop interface for designing and simulating electronic circuits. Built with Python and PyQt6, it integrates with ngspice to deliver accurate SPICE simulations while maintaining an accessible user experience for students, instructors, and researchers.

## Features

### Circuit Design
- Drag-and-drop component placement from visual palette
- Grid-aligned layout (10px snap)
- Intelligent wire routing with IDA* pathfinding
- Component rotation (90-degree increments)
- Real-time circuit editing

### Simulation
- **DC Operating Point** - Steady-state analysis
- **DC Sweep** - Voltage source parameter sweep
- **AC Sweep** - Frequency domain analysis
- **Transient** - Time-domain simulation

### Visualization
- Interactive waveform viewer with matplotlib
- Node voltage display on canvas
- Data table with scrollable results
- Color-blind friendly plot colors

### File Management
- Save/Load circuits (JSON format)
- Session persistence (auto-restore last circuit)
- Netlist export for ngspice

## Supported Components

| Component | Symbol | Status |
|-----------|--------|--------|
| Resistor | R | Fully Functional |
| Capacitor | C | Fully Functional |
| Inductor | L | Fully Functional |
| Voltage Source | V | Fully Functional |
| Current Source | I | Fully Functional |
| Waveform Source | VW | Fully Functional |
| Ground | GND | Fully Functional |
| Op-Amp | OA | Partial |

## Installation

### Prerequisites
- Python 3.10 or higher
- ngspice (must be installed separately)

### Install ngspice

**Windows:**
Download from [ngspice.sourceforge.io](http://ngspice.sourceforge.io/download.html) and add to PATH.

**macOS:**
```bash
brew install ngspice
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install ngspice
```

### Install SDM Spice

1. Clone the repository:
```bash
git clone https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI.git
cd Spice-GUI
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. Install dependencies:
```bash
pip install -r app/requirements.txt
```

4. Run the application:
```bash
python app/main.py
```

## Quick Start

1. **Add Components** - Drag components from the left palette onto the canvas
2. **Connect Wires** - Click on component terminals to create wire connections
3. **Edit Values** - Select a component and use the Properties panel to change values
4. **Run Simulation** - Select an analysis type from the Analysis menu and press F5
5. **View Results** - Results appear in the waveform viewer below the canvas

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New circuit |
| Ctrl+O | Open circuit |
| Ctrl+S | Save circuit |
| Ctrl+G | Generate netlist |
| F5 | Run simulation |
| Del | Delete selected |
| R | Rotate clockwise |
| Shift+R | Rotate counter-clockwise |

## System Requirements

### Minimum
- **OS:** Windows 10, macOS 10.14, Ubuntu 20.04
- **CPU:** Intel i3 / AMD Ryzen 3
- **RAM:** 4 GB
- **Storage:** 500 MB
- **Display:** 1280 x 720

### Recommended
- **OS:** Windows 11, macOS 12+, Ubuntu 22.04
- **CPU:** Intel i5 / AMD Ryzen 5
- **RAM:** 8 GB
- **Storage:** 1 GB
- **Display:** 1920 x 1080

## Technology Stack

- **GUI:** PyQt6 6.9.1
- **Plotting:** matplotlib 3.10.6
- **Numerical:** numpy 2.3.3, scipy 1.16.2
- **Simulation:** ngspice (external)

## Project Status

SDM Spice is currently in **Phase 1 (Student MVP)** development as part of an SDSMT Capstone project.

### Roadmap
- **Phase 1:** Student-focused circuit design tool (Current)
- **Phase 2:** Enhanced export/sharing and LMS integration
- **Phase 3:** Instructor tools (templates, assignments)
- **Phase 4:** Advanced instructor features (analytics)
- **Phase 5:** TA role support
- **Phase 6:** Researcher features (scripting API)
- **Phase 7:** Advanced features and polish

> **Note:** This project follows a **local-first architecture** without user accounts. See [ADR 001](Doc/decisions/001-local-first-no-user-accounts.md) for rationale.

## Documentation

- **[Architecture Decision Records](Doc/decisions/)** - Important architectural decisions and their rationale
- **[Development Methodology](Doc/autonomous-workflow.md)** - AI-assisted development approach and autonomous workflow
- **[Project Evolution](Doc/project-evolution.md)** - How the project evolved from discovery to implementation
- **[Discovery Documentation](DiscoveryDocs/)** - Initial exploration and requirements gathering (academic assignment)

## Development Setup

For contributors setting up a development environment:

### Install Development Dependencies

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Install runtime and development dependencies
make install-dev
# OR manually:
pip install -r app/requirements.txt -r app/requirements-dev.txt
```

### Install Pre-commit Hooks

Pre-commit hooks automatically check code quality before each commit:

```bash
make install-hooks
# OR manually:
pip install pre-commit
pre-commit install

# Test hooks on all files
pre-commit run --all-files
```

### Available Make Commands

| Command | Description |
|---------|-------------|
| `make test` | Run pytest test suite |
| `make lint` | Run linting checks (ruff + black + isort) |
| `make format` | Auto-format code with black and isort |
| `make check` | Run all checks (lint + test) |
| `make install-dev` | Install development dependencies |
| `make install-hooks` | Install pre-commit hooks |

### Code Quality Tools

The project uses several tools to maintain code quality:

- **ruff** - Fast Python linter (configured via `ruff.toml`)
- **black** - Code formatter (120 char line length)
- **isort** - Import statement organizer
- **pytest** - Test framework
- **pre-commit** - Git hook manager

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
cd app && python -m pytest tests/unit/test_file_controller.py -v

# Run with coverage
cd app && python -m pytest tests/ --cov=. --cov-report=html
```

## Contributing

This is a Capstone project for South Dakota School of Mines and Technology. For contribution guidelines, please see the [Wiki](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/wiki).

## Team

SDSMT Capstone Spice GUI Team

## License

Open Source - See [LICENSE](LICENSE) for details.

## Acknowledgments

- South Dakota School of Mines and Technology
- ngspice development team
- PyQt and Qt communities
- Developed with AI assistance from [Claude](https://claude.ai) (Anthropic) - Used for architecture design, code generation, testing, and documentation
