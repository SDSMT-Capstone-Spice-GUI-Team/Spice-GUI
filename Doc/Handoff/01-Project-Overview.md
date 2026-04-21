# Project Overview

## What Is SDM Spice?

SDM Spice is an **open-source, cross-platform circuit design and simulation GUI** built at South Dakota School of Mines and Technology. It provides a drag-and-drop interface for designing electronic circuits and running SPICE simulations — targeted at students learning circuit analysis.

## Goals

- Give students an intuitive tool for building and simulating circuits
- Support educational workflows: templates, grading, rubrics
- Integrate with the industry-standard **ngspice** simulation engine
- Run on Linux, macOS, and Windows

## Current State

- **Phase 1 (Student MVP)** is the active development phase
- Core functionality is working: circuit design, simulation, file I/O, theming
- Grading system is implemented but still maturing
- UI polish (dark/light themes, scrollbars, layout) is the most recent focus area
- Test coverage on models and controllers is at 99%+

## Who Uses It

- **Students** — build and simulate circuits for coursework
- **Instructors** — create assignments, auto-grade student submissions
- **Researchers** — script simulations via the headless API or Jupyter integration

## License

Open source. See `LICENSE` in the project root.