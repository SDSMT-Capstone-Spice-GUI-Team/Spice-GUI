# Tech Stack

## Core

| Technology | Version | Role |
|-----------|---------|------|
| Python | 3.10+ | Primary language |
| PyQt6 | 6.9.1 | Desktop GUI framework |
| ngspice | 36+ | SPICE simulation engine (external binary) |
| matplotlib | 3.10.6 | Waveform plotting |
| numpy | (via matplotlib) | Numerical computing |
| scipy | 1.16.2 | Scientific computing |

## Supporting Libraries

| Library | Role |
|---------|------|
| PyYAML | Configuration file parsing |
| openpyxl | Excel (.xlsx) export |
| Pillow | Image processing |
| requests | HTTP (future cloud features) |
| PySpice | SPICE utility reference |

## Dev Tools

| Tool | Role |
|------|------|
| ruff | Fast Python linter (config in `ruff.toml`) |
| black | Code formatter (120 char line length) |
| isort | Import sorting |
| pytest | Test framework |
| pre-commit | Git hook manager |
| Makefile | Build targets (`test`, `lint`, `format`, `check`) |

## Key Architecture Constraint

> **Models and controllers have zero PyQt6 dependencies.**
> This means the entire business logic layer can be tested without a display server — fast, headless, CI-friendly.