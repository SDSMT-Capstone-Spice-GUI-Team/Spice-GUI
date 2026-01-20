# SDM Spice

**South Dakota Mines Spice** - An open-source circuit design and simulation platform for electrical engineering education.

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
- **Phase 2:** User accounts and cloud storage
- **Phase 3:** Instructor tools (assignments, grading)
- **Phase 4:** Advanced instructor features (analytics)
- **Phase 5:** TA role support
- **Phase 6:** Researcher features (scripting API)
- **Phase 7:** Administrator tools and polish

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
