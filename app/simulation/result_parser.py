"""
simulation/result_parser.py

Parses ngspice simulation output to extract results
"""

import logging
import math
import re

logger = logging.getLogger(__name__)

# SI prefix table for engineering notation
_SI_PREFIXES = [
    (1e-15, "f"),
    (1e-12, "p"),
    (1e-9, "n"),
    (1e-6, "\u00b5"),
    (1e-3, "m"),
    (1e0, ""),
    (1e3, "k"),
    (1e6, "M"),
    (1e9, "G"),
]


def format_si(value, unit=""):
    """Format a value with SI prefix.

    Examples:
        format_si(0.0033, "V") -> "3.30 mV"
        format_si(1500, "Hz") -> "1.50 kHz"
        format_si(0, "V") -> "0.00 V"
    """
    if value == 0 or not math.isfinite(value):
        return f"0.00 {unit}" if unit else "0.00"

    abs_val = abs(value)
    for threshold, prefix in _SI_PREFIXES:
        if abs_val < threshold * 1000:
            scaled = value / threshold
            return f"{scaled:.2f} {prefix}{unit}" if unit else f"{scaled:.2f} {prefix}"

    # Larger than 1G — use the largest prefix
    threshold, prefix = _SI_PREFIXES[-1]
    scaled = value / threshold
    return f"{scaled:.2f} {prefix}{unit}" if unit else f"{scaled:.2f} {prefix}"


class ResultParser:
    """Parses ngspice simulation results"""

    @staticmethod
    def parse_op_results(output):
        """Parse operational point analysis results to extract node voltages and branch currents.

        Returns a dict with 'node_voltages' and 'branch_currents' keys.
        For backward compatibility, can also be used as a plain dict of voltages
        when only voltages are present.
        """
        node_voltages = {}
        branch_currents = {}

        try:
            lines = output.split("\n")

            for i, line in enumerate(lines):
                # Pattern 1: v(nodename) = voltage
                match = re.search(r"v\((\w+)\)\s*[=:]\s*([-+]?[\d.]+e?[-+]?\d*)", line, re.IGNORECASE)
                if match:
                    node_name = match.group(1)
                    voltage = float(match.group(2))
                    node_voltages[node_name] = voltage
                    continue

                # Branch current patterns: i(device) = current or @device[current]
                i_match = re.search(
                    r"(?:i\((\w+)\)|@(\w+)\[current\])\s*[=:]\s*([-+]?[\d.]+e?[-+]?\d*)", line, re.IGNORECASE
                )
                if i_match:
                    device = i_match.group(1) or i_match.group(2)
                    current = float(i_match.group(3))
                    branch_currents[device.lower()] = current
                    continue

                # Pattern 2: Node/Voltage table
                if "node" in line.lower() and "voltage" in line.lower():
                    for j in range(i + 1, min(i + 50, len(lines))):
                        result_line = lines[j].strip()
                        if not result_line or result_line.startswith("-"):
                            continue
                        if result_line.startswith("*") or result_line.lower().startswith("source"):
                            break

                        parts = result_line.split()
                        if len(parts) >= 2:
                            try:
                                node_name = parts[0].replace("v(", "").replace(")", "")
                                voltage = float(parts[1])
                                node_voltages[node_name] = voltage
                            except (ValueError, IndexError):
                                continue

            # Pattern 3: ngspice print output format
            for line in lines:
                # Voltages: " V(5)   1.000000e-06 "
                match = re.match(r"^\s*V\((\w+)\)\s+([-+]?[\d.]+e?[-+]?\d*)\s*", line, re.IGNORECASE)
                if match:
                    node_name = match.group(1)
                    voltage = float(match.group(2))
                    node_voltages[node_name] = voltage
                    continue
                # Currents: " I(v1)   -2.100000e-03 "
                i_match = re.match(r"^\s*I\((\w+)\)\s+([-+]?[\d.]+e?[-+]?\d*)\s*", line, re.IGNORECASE)
                if i_match:
                    device = i_match.group(1)
                    current = float(i_match.group(2))
                    branch_currents[device.lower()] = current

            return {"node_voltages": node_voltages, "branch_currents": branch_currents}

        except (ValueError, IndexError, AttributeError) as e:
            logger.error("Error parsing OP results: %s", e, exc_info=True)
            return {"node_voltages": {}, "branch_currents": {}}

    @staticmethod
    def parse_dc_results(output):
        """Parse DC sweep results"""
        try:
            lines = output.split("\n")
            sweep_data = {"sweep_var": None, "data": []}

            # Look for DC sweep data in the output
            # Format typically: "Index   v-sweep   v(node1)   v(node2) ..."
            header_found = False
            headers = []

            for i, line in enumerate(lines):
                # Look for table headers
                if "index" in line.lower() or ("sweep" in line.lower() and "v(" in line.lower()):
                    headers = line.split()
                    header_found = True
                    sweep_data["headers"] = headers
                    continue

                # Parse data rows after header
                if header_found:
                    parts = line.strip().split()
                    if len(parts) >= len(headers):
                        try:
                            # Convert to floats
                            data_row = [float(p) for p in parts[: len(headers)]]
                            sweep_data["data"].append(data_row)
                        except ValueError:
                            continue

            return sweep_data if sweep_data["data"] else None

        except (ValueError, IndexError, KeyError) as e:
            logger.error("Error parsing DC results: %s", e)
            return None

    @staticmethod
    def parse_ac_results(output):
        """Parse AC sweep results"""
        try:
            lines = output.split("\n")
            ac_data = {"frequencies": [], "magnitude": {}, "phase": {}}

            # Look for AC analysis data
            # Format: "Index   frequency   v(node1)   vp(node1) ..."
            header_found = False
            headers = []

            for i, line in enumerate(lines):
                # Look for frequency data headers
                if "frequency" in line.lower() or "freq" in line.lower():
                    headers = line.split()
                    header_found = True
                    ac_data["headers"] = headers
                    continue

                # Parse data rows
                if header_found and line.strip():
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        try:
                            freq = float(parts[1]) if len(parts) > 1 else float(parts[0])
                            ac_data["frequencies"].append(freq)

                            # Parse voltage magnitudes and phases
                            for j, header in enumerate(headers[2:], start=2):
                                if j < len(parts):
                                    if "vp(" in header.lower():
                                        # Phase data
                                        node = header.replace("vp(", "").replace(")", "")
                                        if node not in ac_data["phase"]:
                                            ac_data["phase"][node] = []
                                        ac_data["phase"][node].append(float(parts[j]))
                                    elif "v(" in header.lower():
                                        # Magnitude data
                                        node = header.replace("v(", "").replace(")", "")
                                        if node not in ac_data["magnitude"]:
                                            ac_data["magnitude"][node] = []
                                        ac_data["magnitude"][node].append(float(parts[j]))
                        except (ValueError, IndexError):
                            continue

            return ac_data if ac_data["frequencies"] else None

        except (ValueError, IndexError, KeyError) as e:
            logger.error("Error parsing AC results: %s", e)
            return None

    @staticmethod
    def parse_transient_results(filepath):
        """
        Parses a wrdata output file from ngspice, which has a clean,
        whitespace-delimited format.
        """
        try:
            with open(filepath, "r") as f:
                lines = f.readlines()

            if not lines:
                return None

            # First line contains whitespace-separated headers
            raw_headers = lines[0].strip().split()
            headers = []
            for h in raw_headers:
                # Sanitize headers: v(node) -> node, i(branch) -> i_branch
                sanitized_h = re.sub(r"^v\((.*?)\)$", r"\1", h, flags=re.IGNORECASE)
                sanitized_h = re.sub(r"^i\((.*?)\)$", r"i_\1", sanitized_h, flags=re.IGNORECASE)
                headers.append(sanitized_h)

            results = []
            # Data starts from the second line
            for line in lines[1:]:
                parts = line.strip().split()
                if len(parts) == len(headers):
                    try:
                        row_data = {headers[i]: float(parts[i]) for i in range(len(parts))}
                        results.append(row_data)
                    except (ValueError, IndexError):
                        continue

            return results if results else None
        except FileNotFoundError:
            logger.error("wrdata file not found at %s", filepath)
            return None
        except (OSError, ValueError, IndexError, KeyError) as e:
            logger.error("Error parsing wrdata file: %s", e, exc_info=True)
            return None

    @staticmethod
    def format_results_as_table(results):
        """
        Format a list of dictionaries into a string table.

        Args:
            results (list of dict): The parsed data from parse_transient_results.

        Returns:
            str: A formatted string representing the data in a table.
        """
        if not results:
            return "No data to display."

        headers = list(results[0].keys())

        # Define column widths, with a minimum
        col_widths = {h: max(len(h), 12) for h in headers}
        for row in results:
            for h in headers:
                # Pad for floating point representation
                col_widths[h] = max(col_widths[h], len(f"{row[h]:<12.5e}"))

        # Header string
        header_str_list = []
        for h in headers:
            header_str_list.append(f"{h:<{col_widths[h]}}")
        header_str = " | ".join(header_str_list)

        # Separator
        separator = "-" * len(header_str)

        # Data rows
        data_rows = []
        for row in results:
            row_list = []
            for h in headers:
                row_list.append(f"{row[h]:<{col_widths[h]}.5e}")
            data_rows.append(" | ".join(row_list))

        return f"{header_str}\n{separator}\n" + "\n".join(data_rows)
