"""
simulation/bundle_exporter.py

Create a dated ZIP bundle containing all circuit artifacts for lab submission.
No Qt dependencies -- the caller is responsible for generating Qt-dependent
artifacts (schematic PNG, report PDF) and passing them as bytes/strings.
"""

import json
import zipfile
from datetime import datetime
from pathlib import Path


def create_bundle(
    filepath,
    circuit_json=None,
    netlist=None,
    schematic_png=None,
    results_csv=None,
    results_xlsx_path=None,
    report_pdf=None,
    circuit_name="",
):
    """Create a ZIP bundle with all available circuit artifacts.

    Args:
        filepath: Path to write the .zip file.
        circuit_json: dict or str of the native circuit JSON (always included).
        netlist: str of the SPICE netlist (always included if available).
        schematic_png: bytes of the rendered schematic PNG (always included if available).
        results_csv: str of simulation results CSV (only if simulation was run).
        results_xlsx_path: path to a temp .xlsx file to include (only if simulation was run).
        report_pdf: bytes of the PDF report (only if simulation results available).
        circuit_name: name for the bundle prefix.

    Returns:
        list[str]: names of files included in the bundle.
    """
    included = []

    # AUDIT(security): zip archive creation does not set a maximum size limit; large simulation outputs could create unexpectedly large archives
    with zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as zf:
        # Circuit JSON (native format for re-import)
        if circuit_json is not None:
            content = circuit_json if isinstance(circuit_json, str) else json.dumps(circuit_json, indent=2)
            zf.writestr("circuit.json", content)
            included.append("circuit.json")

        # SPICE netlist
        if netlist:
            zf.writestr("netlist.cir", netlist)
            included.append("netlist.cir")

        # Schematic image
        if schematic_png:
            zf.writestr("schematic.png", schematic_png)
            included.append("schematic.png")

        # Simulation results CSV
        if results_csv:
            zf.writestr("results.csv", results_csv)
            included.append("results.csv")

        # Simulation results Excel
        if results_xlsx_path and Path(results_xlsx_path).exists():
            zf.write(results_xlsx_path, "results.xlsx")
            included.append("results.xlsx")

        # PDF report
        if report_pdf:
            zf.writestr("report.pdf", report_pdf)
            included.append("report.pdf")

    return included


def suggest_bundle_name(circuit_name=""):
    """Suggest a filename for the ZIP bundle.

    Returns:
        str: filename like 'circuit_name_2024-01-15.zip'
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    name = circuit_name.replace(".json", "").strip() if circuit_name else "circuit"
    # Sanitize
    name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    return f"{name}_{date_str}.zip"
