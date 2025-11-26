"""
simulation/result_parser.py

Parses ngspice simulation output to extract results
"""

import re


class ResultParser:
    """Parses ngspice simulation results"""
    
    @staticmethod
    def parse_op_results(output):
        """Parse operational point analysis results to extract node voltages"""
        node_voltages = {}
        
        try:
            lines = output.split('\n')
            
            for i, line in enumerate(lines):
                # Pattern 1: v(nodename) = voltage
                match = re.search(r'v\((\w+)\)\s*[=:]\s*([-+]?[\d.]+e?[-+]?\d*)', line, re.IGNORECASE)
                if match:
                    node_name = match.group(1)
                    voltage = float(match.group(2))
                    node_voltages[node_name] = voltage
                    continue
                
                # Pattern 2: Node/Voltage table
                if 'node' in line.lower() and 'voltage' in line.lower():
                    for j in range(i+1, min(i+50, len(lines))):
                        result_line = lines[j].strip()
                        if not result_line or result_line.startswith('-'):
                            continue
                        if result_line.startswith('*') or result_line.lower().startswith('source'):
                            break
                        
                        parts = result_line.split()
                        if len(parts) >= 2:
                            try:
                                node_name = parts[0].replace('v(', '').replace(')', '')
                                voltage = float(parts[1])
                                node_voltages[node_name] = voltage
                            except (ValueError, IndexError):
                                continue
            
            # Pattern 3: ngspice print output format
            # Match lines like: " V(5)                             1.000000e-06 "
            for line in lines:
                match = re.match(r'^\s*V\((\w+)\)\s+([-+]?[\d.]+e?[-+]?\d*)\s*', line, re.IGNORECASE)
                if match:
                    node_name = match.group(1)
                    voltage = float(match.group(2))
                    node_voltages[node_name] = voltage
            
            return node_voltages
            
        except Exception as e:
            print(f"Error parsing OP results: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    @staticmethod
    def parse_dc_results(output):
        """Parse DC sweep results"""
        try:
            lines = output.split('\n')
            sweep_data = {'sweep_var': None, 'data': []}

            # Look for DC sweep data in the output
            # Format typically: "Index   v-sweep   v(node1)   v(node2) ..."
            header_found = False
            headers = []

            for i, line in enumerate(lines):
                # Look for table headers
                if 'index' in line.lower() or ('sweep' in line.lower() and 'v(' in line.lower()):
                    headers = line.split()
                    header_found = True
                    sweep_data['headers'] = headers
                    continue

                # Parse data rows after header
                if header_found:
                    parts = line.strip().split()
                    if len(parts) >= len(headers):
                        try:
                            # Convert to floats
                            data_row = [float(p) for p in parts[:len(headers)]]
                            sweep_data['data'].append(data_row)
                        except ValueError:
                            continue

            return sweep_data if sweep_data['data'] else None

        except Exception as e:
            print(f"Error parsing DC results: {e}")
            return None

    @staticmethod
    def parse_ac_results(output):
        """Parse AC sweep results"""
        try:
            lines = output.split('\n')
            ac_data = {'frequencies': [], 'magnitude': {}, 'phase': {}}

            # Look for AC analysis data
            # Format: "Index   frequency   v(node1)   vp(node1) ..."
            header_found = False
            headers = []

            for i, line in enumerate(lines):
                # Look for frequency data headers
                if 'frequency' in line.lower() or 'freq' in line.lower():
                    headers = line.split()
                    header_found = True
                    ac_data['headers'] = headers
                    continue

                # Parse data rows
                if header_found and line.strip():
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        try:
                            freq = float(parts[1]) if len(parts) > 1 else float(parts[0])
                            ac_data['frequencies'].append(freq)

                            # Parse voltage magnitudes and phases
                            for j, header in enumerate(headers[2:], start=2):
                                if j < len(parts):
                                    if 'vp(' in header.lower():
                                        # Phase data
                                        node = header.replace('vp(', '').replace(')', '')
                                        if node not in ac_data['phase']:
                                            ac_data['phase'][node] = []
                                        ac_data['phase'][node].append(float(parts[j]))
                                    elif 'v(' in header.lower():
                                        # Magnitude data
                                        node = header.replace('v(', '').replace(')', '')
                                        if node not in ac_data['magnitude']:
                                            ac_data['magnitude'][node] = []
                                        ac_data['magnitude'][node].append(float(parts[j]))
                        except (ValueError, IndexError):
                            continue

            return ac_data if ac_data['frequencies'] else None

        except Exception as e:
            print(f"Error parsing AC results: {e}")
            return None

    @staticmethod
    def parse_transient_results(output):
        """Parse transient analysis results into a list of dictionaries."""
        try:
            lines = output.split('\n')
            results = []
            headers = []
            data_started = False

            for line in lines:
                line = line.strip()

                if not line or line.startswith('*') or line.startswith('$') or "No. of Data Rows" in line:
                    continue

                if '---' in line:
                    continue

                # Find header row
                if not data_started and ('time' in line.lower() or 'v(' in line.lower() or 'i(' in line.lower()):
                    raw_headers = line.split()
                    # Sanitize headers: v(node) -> node, and handle potential duplicates
                    headers = []
                    for h in raw_headers:
                        sanitized_h = re.sub(r'^[vi]\((.*?)\)$', r'\1', h)
                        headers.append(sanitized_h)
                    data_started = True
                    continue

                if data_started:
                    parts = line.split()
                    if len(parts) == len(headers):
                        try:
                            row_data = {headers[i]: float(parts[i]) for i in range(len(headers))}
                            results.append(row_data)
                        except (ValueError, IndexError):
                            # Stop if a line doesn't conform, it might be the end of the data block
                            continue
            
            return results if results else None

        except Exception as e:
            print(f"Error parsing transient results: {e}")
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