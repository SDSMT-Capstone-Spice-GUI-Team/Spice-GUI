#!/usr/bin/env python
# -*- mode: python ; coding: utf-8 -*-
#
# collect_licenses.py -- Auto-collect redistributable third-party license files
#                       for the SpiceGUI release bundle.
#
# PyInstaller/Inno need every redistributable dependency to carry its license.
# Hand-copying them drifts out of sync whenever dependencies change. This script
# derives the runtime dependency list straight from ``pyproject.toml`` and copies
# each package's license from the active environment's ``site-packages`` into the
# repo ``licenses/`` folder, then regenerates the single-file ``LICENSE-COMBINED.txt``
# that the Inno Setup script uses as its ``LicenseFile``.
#
# Run it from the repo root before building the release:
#     uvx python scripts/collect_licenses.py   # or: python scripts/collect_licenses.py
#
# It is safe to run repeatedly: outputs are overwritten deterministically.

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Runtime dependencies -- read from pyproject so we never miss a new one.
PYPROJECT = REPO_ROOT / "pyproject.toml"
# Files that are license-related but not legal license text (skip them).
_SKIP = ("third-party", "notice", "notices", "py.typed")

# License file names to look for. Includes the common English spellings plus the
# British "LICENCE" spelling (openpyxl ships `LICENCE.rst`).
_LICENSE_NAMES = ("LICENSE", "LICENSE.txt", "LICENSE.md", "LICENSE.rst",
                  "COPYING", "LICENCE", "LICENCE.txt", "LICENCE.rst")

# Non-pip redistributables that also carry a license and must be shipped, but
# are not captured by the pyproject dependency scan. Each maps to the repo
# filename (already present in licenses/).
_EXTRA = {
    "PYTHON": REPO_ROOT / "licenses" / "PYTHON-LICENSE.txt",
    "NGSPICE": REPO_ROOT / "licenses" / "NGSPICE-LICENSE.txt",
}


def parse_dependencies(pyproject: Path) -> list[str]:
    """Return the raw dependency strings from ``[project].dependencies``.

    Handles plain ``"numpy"`` as well as markers like ``"numpy>=1.24"`` and
    ``"PyQt6>=6.6.0,<7.0.0; ..."``.
    """
    text = pyproject.read_text(encoding="utf-8")
    block = re.search(r"dependencies\s*=\s*\[(.*?)\]", text, re.DOTALL)
    if not block:
        return []
    deps = []
    for line in block.group(1).splitlines():
        stripped = line.strip().strip('"').strip("'").strip()
        name = re.match(r"([A-Za-z0-9_.\-]+)", stripped)
        if name:
            deps.append(name.group(1))
    return deps


def site_packages() -> Path | None:
    """Locate the environment's site-packages directory.

    Prefers an explicit ``--site-packages`` argument, then the active virtualenv,
    then falls back to scanning for the most common venv layout.
    """
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).resolve()

    # Active virtualenv root is one level up from sys.prefix.
    prefix = Path(sys.prefix)
    cand = prefix / "Lib" / "site-packages"
    if cand.is_dir():
        return cand

    # Fallback: <repo>/.venv/Lib/site-packages
    for venv in (REPO_ROOT / ".venv",):
        found = venv / "Lib" / "site-packages"
        if found.is_dir():
            return found
    return None


def find_license(pkg: str, sp: Path) -> Path | None:
    """Return the path to *pkg*'s license, or ``None`` if not found."""
    pkg_dir = sp / pkg
    # 1) A top-level package directory may carry its own LICENSE (e.g. numpy/).
    #    Best-effort: if the dir is missing (namespace pkg / import name != dist
    #    name, e.g. PyYAML -> "yaml"), fall through to the dist-info lookup.
    if pkg_dir.is_dir():
        for name in _LICENSE_NAMES:
            p = pkg_dir / name
            if p.is_file():
                return p

    # 2) <pkg>-<ver>.dist-info/licenses/LICENSE at the dist-info root.
    #    dist-info dir names are case-insensitive and may differ in case from the
    #    dependency name, so match on the lowercase form.
    lowered = pkg.lower()
    dist_infos = sorted(p for p in sp.glob("*.dist-info") if p.name.lower().startswith(lowered))
    for di in dist_infos:
        for name in _LICENSE_NAMES:
            p = di / "licenses" / name
            if p.is_file():
                return p
            p2 = di / name
            if p2.is_file():
                return p2
    return None


def is_license_text(path: Path) -> bool:
    """Reject license *files* that are really just notices/spdx data files."""
    low = path.name.lower()
    return not any(t in low for t in _SKIP)


def main() -> int:
    deps = parse_dependencies(PYPROJECT)
    sp = site_packages()
    if sp is None or not sp.is_dir():
        print("ERROR: could not locate site-packages.", file=sys.stderr)
        return 1

    license_dir = REPO_ROOT / "licenses"
    license_dir.mkdir(parents=True, exist_ok=True)

    collected: list[Path] = []
    missing: list[str] = []
    for pkg in deps:
        lic = find_license(pkg, sp)
        if lic is None or not is_license_text(lic):
            missing.append(pkg)
            continue
        out = license_dir / f"{pkg.replace('-', '_').upper()}-LICENSE.txt"
        shutil.copy2(lic, out)
        collected.append(out)
        print(f"  collected {pkg:<16} -> {out.name}")

    combined = REPO_ROOT / "LICENSE-COMBINED.txt"
    # Non-pip redistributables that also carry a license but aren't in the
    # pyproject scan (Python, vendored ngspice). They must be shipped too.
    for name, path in _EXTRA.items():
        if not path.is_file():
            missing.append(name)
        else:
            collected.append(path)
            print(f"  included {name:<16} -> {path.name}")

    write_combined(combined, sorted(collected))
    print(f"\nWrote combined license: {combined}")

    print(f"\n{len(collected)} licenses collected, {len(missing)} missing: {missing}")
    return 0 if not missing else 2


def write_combined(combined: Path, files: list[Path]) -> None:
    """Write a single-file concatenation of all licenses (Inno LicenseFile)."""
    with combined.open("w", encoding="utf-8") as f:
        f.write("THIRD-PARTY LICENSES\n")
        f.write("====================\n\n")
        f.write(
            "This application redistributes third-party software. The license text\n"
            "for each component is provided individually in the \\licenses\\ folder of\n"
            "the installation and below. If you cannot locate a license, contact the\n"
            "SDSMT Capstone Spice GUI Team.\n\n"
        )
        for lic in files:
            try:
                rel = lic.relative_to(REPO_ROOT)
            except ValueError:
                rel = lic
            f.write(f"=== {rel.as_posix()} ===\n\n")
            f.write(lic.read_text(encoding="utf-8"))
            f.write("\n\n---\n\n")


if __name__ == "__main__":
    raise SystemExit(main())
