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
            # print(f"Error parsing OP results: {e}")
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
            # print(f"Error parsing DC results: {e}")
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
            # print(f"Error parsing AC results: {e}")
            return None

    @staticmethod
    def parse_transient_results(output):
        """Parse transient analysis results"""
        try:
            lines = output.split('\n')
            tran_data = {'time': [], 'voltages': {}}

            # Look for transient data
            # Format: "Index   time   v(node1)   v(node2) ..."
            header_found = False
            headers = []

            for i, line in enumerate(lines):
                # Look for time-based headers
                if 'time' in line.lower() and ('v(' in line.lower() or 'index' in line.lower()):
                    headers = line.split()
                    header_found = True
                    tran_data['headers'] = headers
                    # Initialize voltage arrays for each node
                    for header in headers[2:]:  # Skip index and time
                        if 'v(' in header.lower():
                            node = header.replace('v(', '').replace(')', '')
                            tran_data['voltages'][node] = []
                    continue

                # Parse data rows
                if header_found and line.strip():
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        try:
                            # Second column is time (first is index)
                            time = float(parts[1]) if len(parts) > 1 else float(parts[0])
                            tran_data['time'].append(time)

                            # Parse voltages for each node
                            for j, header in enumerate(headers[2:], start=2):
                                if j < len(parts) and 'v(' in header.lower():
                                    node = header.replace('v(', '').replace(')', '')
                                    tran_data['voltages'][node].append(float(parts[j]))
                        except (ValueError, IndexError):
                            continue

            return tran_data if tran_data['time'] else None

        except Exception as e:
            # print(f"Error parsing transient results: {e}")
            return None