# -*- mode: python ; coding: utf-8 -*-
#
# SpiceGUI.spec -- PyInstaller spec for building a standalone Windows bundle
#
# Build instructions (run from the repo root):
#
#   1. Install build dependencies into your virtualenv:
#        pip install pyinstaller
#        pip install -r app/requirements.txt
#
#   2. Run PyInstaller with this spec file:
#        python -m PyInstaller SpiceGUI.spec
#
#   3. The distributable application will be in:
#        dist/SpiceGUI/SpiceGUI.exe
#
# Runtime dependency -- ngspice:
#   ngspice is invoked as an external subprocess and is NOT bundled.
#   Users must install ngspice separately.  On Windows the installer from
#   https://ngspice.sourceforge.io/ places ngspice.exe on the PATH or in
#   a well-known location that the application searches automatically
#   (see simulation/ngspice_runner.py for the full search list).
#
#   Optionally, you can place ngspice.exe (and its DLLs) next to
#   SpiceGUI.exe in the dist directory and it will be found via PATH.
#

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(SPECPATH)  # noqa: F821  (SPECPATH injected by PyInstaller)
APP_DIR = REPO_ROOT / "app"

# ---------------------------------------------------------------------------
# Data files: (source_path, dest_directory_inside_bundle)
#
# These use Path(__file__)-relative lookups at runtime, so the directory
# structure under app/ must be preserved inside the frozen bundle.
# ---------------------------------------------------------------------------
datas = [
    (str(APP_DIR / "examples"), "examples"),
    (str(APP_DIR / "templates"), "templates"),
]

# ---------------------------------------------------------------------------
# Hidden imports
#
# PyQt6 and matplotlib require explicit hints for plugins and backends
# that are loaded at runtime rather than via static imports.
# ---------------------------------------------------------------------------
hiddenimports = [
    # -- Matplotlib Qt backend (set via matplotlib.use("QtAgg") in plot_utils.py)
    "matplotlib.backends.backend_qtagg",
    "matplotlib.backends.backend_agg",
    # -- PyQt6 modules often missed by analysis
    "PyQt6.QtPrintSupport",
    "PyQt6.QtSvg",
    "PyQt6.QtSvgWidgets",
    # -- Numeric / scientific stack internals
    "numpy",
    "scipy",
    "scipy.special",
    "scipy.special._cdflib",
    # -- Data-export libraries
    "openpyxl",
    # -- YAML (used for config/export)
    "yaml",
    # -- Parsing libraries
    "ply",
    "ply.lex",
    "ply.yacc",
    # -- All app subpackages (catches intra-package dynamic references)
    *collect_submodules("GUI"),
    *collect_submodules("models"),
    *collect_submodules("controllers"),
    *collect_submodules("simulation"),
    *collect_submodules("algorithms"),
    *collect_submodules("services"),
    *collect_submodules("scripting"),
    *collect_submodules("grading"),
    *collect_submodules("protocols"),
    *collect_submodules("utils"),
]

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    [str(APP_DIR / "main.py")],
    pathex=[str(APP_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Not needed at runtime -- test and dev tooling
        "pytest",
        "black",
        "isort",
        "IPython",
        "jupyter",
        "notebook",
        "tkinter",
        "_tkinter",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

# ---------------------------------------------------------------------------
# Executable
# ---------------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # --onedir mode
    name="SpiceGUI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI application -- no terminal window
    # icon="app/assets/spicegui.ico",  # Uncomment when an .ico file is added
)

# ---------------------------------------------------------------------------
# Directory bundle (--onedir)
# ---------------------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SpiceGUI",
)
