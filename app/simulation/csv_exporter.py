"""
simulation/csv_exporter.py

Export simulation results to CSV format.
No Qt dependencies — file dialog is the view's responsibility.
"""

import csv
import io
from datetime import datetime


def export_op_results(node_voltages, circuit_name=""):
    """
    Export DC Operating Point results to CSV string.

    Args:
        node_voltages: dict mapping node name -> voltage (float)
        circuit_name: optional circuit filename

    Returns:
        str: CSV content
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["# Analysis Type", "DC Operating Point"])
    writer.writerow(["# Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    if circuit_name:
        writer.writerow(["# Circuit", circuit_name])
    writer.writerow([])

    writer.writerow(["Node", "Voltage (V)"])
    for node, voltage in sorted(node_voltages.items()):
        writer.writerow([node, voltage])

    return output.getvalue()


def export_dc_sweep_results(sweep_data, circuit_name=""):
    """
    Export DC Sweep results to CSV string.

    Args:
        sweep_data: dict with 'headers' (list) and 'data' (list of lists)
        circuit_name: optional circuit filename

    Returns:
        str: CSV content
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["# Analysis Type", "DC Sweep"])
    writer.writerow(["# Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    if circuit_name:
        writer.writerow(["# Circuit", circuit_name])
    writer.writerow([])

    headers = sweep_data.get("headers", [])
    writer.writerow(headers)

    for row in sweep_data.get("data", []):
        writer.writerow(row)

    return output.getvalue()


def export_ac_results(ac_data, circuit_name=""):
    """
    Export AC Sweep results to CSV string.

    Exports both magnitude and phase data with separate columns.

    Args:
        ac_data: dict with 'frequencies', 'magnitude', 'phase'
        circuit_name: optional circuit filename

    Returns:
        str: CSV content
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["# Analysis Type", "AC Sweep"])
    writer.writerow(["# Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    if circuit_name:
        writer.writerow(["# Circuit", circuit_name])
    writer.writerow([])

    frequencies = ac_data.get("frequencies", [])
    magnitude = ac_data.get("magnitude", {})
    phase = ac_data.get("phase", {})

    # Build headers: Frequency, |V(node1)|, phase(node1), |V(node2)|, ...
    headers = ["Frequency (Hz)"]
    mag_nodes = sorted(magnitude.keys())
    phase_nodes = sorted(phase.keys())
    all_nodes = sorted(set(mag_nodes) | set(phase_nodes))

    for node in all_nodes:
        if node in magnitude:
            headers.append(f"|V({node})|")
        if node in phase:
            headers.append(f"phase(V({node})) (deg)")

    writer.writerow(headers)

    for i, freq in enumerate(frequencies):
        row = [freq]
        for node in all_nodes:
            if node in magnitude:
                row.append(magnitude[node][i] if i < len(magnitude[node]) else "")
            if node in phase:
                row.append(phase[node][i] if i < len(phase[node]) else "")
        writer.writerow(row)

    return output.getvalue()


def export_transient_results(tran_data, circuit_name=""):
    """
    Export Transient analysis results to CSV string.

    Args:
        tran_data: list of dicts, each with 'time' and node voltage keys
        circuit_name: optional circuit filename

    Returns:
        str: CSV content
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["# Analysis Type", "Transient"])
    writer.writerow(["# Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    if circuit_name:
        writer.writerow(["# Circuit", circuit_name])
    writer.writerow([])

    if not tran_data:
        return output.getvalue()

    headers = list(tran_data[0].keys())
    writer.writerow(headers)

    for row in tran_data:
        writer.writerow([row[h] for h in headers])

    return output.getvalue()


def export_noise_results(noise_data, circuit_name=""):
    """
    Export Noise analysis results to CSV string.

    Args:
        noise_data: dict with 'frequencies', 'onoise_spectrum', 'inoise_spectrum'
        circuit_name: optional circuit filename

    Returns:
        str: CSV content
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["# Analysis Type", "Noise"])
    writer.writerow(["# Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    if circuit_name:
        writer.writerow(["# Circuit", circuit_name])
    writer.writerow([])

    frequencies = noise_data.get("frequencies", [])
    onoise = noise_data.get("onoise_spectrum", [])
    inoise = noise_data.get("inoise_spectrum", [])

    headers = ["Frequency (Hz)"]
    if onoise:
        headers.append("Output Noise (V/sqrt(Hz))")
    if inoise:
        headers.append("Input Noise (V/sqrt(Hz))")
    writer.writerow(headers)

    for i, freq in enumerate(frequencies):
        row = [freq]
        if onoise:
            row.append(onoise[i] if i < len(onoise) else "")
        if inoise:
            row.append(inoise[i] if i < len(inoise) else "")
        writer.writerow(row)

    return output.getvalue()


def write_csv(csv_content, filepath):
    """
    Write CSV content string to a file.

    Args:
        csv_content: str from one of the export_* functions
        filepath: path to write to
    """
    with open(filepath, "w", newline="") as f:
        f.write(csv_content)
