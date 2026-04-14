# Dev Setup

## Prerequisites

- **Python 3.10+**
- **ngspice 36+** — must be installed and on your PATH
  - Ubuntu/Debian: `sudo apt install ngspice`
  - macOS: `brew install ngspice`
  - Arch: `sudo pacman -S ngspice`
- **Git**

## Installation

```bash
# Clone the repo
git clone <repo-url>
cd Spice-GUI

# Create a virtual environment
python -m venv venv
source venv/bin/activate      # Linux/macOS
# venv\Scripts\activate       # Windows

# Install runtime dependencies
pip install -r app/requirements.txt

# Install dev dependencies
pip install -r app/requirements-dev.txt
# Or:
make install-dev

# Install pre-commit hooks
make install-hooks
```

## Running the App

```bash
python app/main.py
```

## Makefile Targets

| Target | What It Does |
|--------|-------------|
| `make test` | Run full test suite |
| `make lint` | Check code with ruff |
| `make format` | Auto-format with black + isort |
| `make check` | Lint + test combined |
| `make install-dev` | Install dev dependencies |
| `make install-hooks` | Install pre-commit hooks |

## IDE Setup

The repo includes configs for both **PyCharm** (`.idea/`) and **VS Code** (`.vscode/`). Both should work out of the box once you point them at the virtual environment.

## Branching Strategy

See `docs/adr/003-branching-strategy.md` and `docs/decisions/2026-02-10-epic-workflow-and-branch-strategy.md` for the full branching model. In short:

- `main` — stable, releasable code
- `dev-main-epic-*` — epic-level feature branches
- Feature branches off of epic branches for individual work

## Code Quality

Pre-commit hooks enforce:
- **ruff** — linting
- **black** — formatting (120 char lines)
- **isort** — import ordering

Run `make check` before pushing to catch issues early.

## Circuit File Format

Circuits are stored as JSON. See `data/` and `app/templates/` for examples. The schema is defined by `CircuitModel.to_dict()` / `from_dict()`.