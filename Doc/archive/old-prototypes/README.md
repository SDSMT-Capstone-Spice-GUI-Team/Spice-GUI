# Archived Old Prototypes

This directory contains code from early project exploration that is no longer used in the current implementation.

## Core/ - PySide6 Prototype (Archived 2026-02-08)

**What it was:** Early main window prototype using PySide6
**Status:** Obsolete - Current implementation uses PyQt6
**Why archived:**
- Uses PySide6, current app uses PyQt6 (ADR 005)
- Replaced by main_window.py
- Not referenced anywhere in current codebase

**Contents:**
- `MainWindow.py` - Early main window with welcome screen
- `darkMode.qss` - Dark mode stylesheet (not used)

**Historical Note:** This represents the initial UI exploration before settling on the circuit design canvas approach.
