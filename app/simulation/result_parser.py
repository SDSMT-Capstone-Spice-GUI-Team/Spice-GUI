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
                    print(f"Parsed: node={node_name}, voltage={voltage}")
            
            return node_voltages
            
        except Exception as e:
            print(f"Error parsing OP results: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    @staticmethod
    def parse_dc_results(output):
        """Parse DC sweep results (to be implemented)"""
        # TODO: Implement DC sweep parsing
        return {}
    
    @staticmethod
    def parse_ac_results(output):
        """Parse AC sweep results (to be implemented)"""
        # TODO: Implement AC sweep parsing
        return {}
    
    @staticmethod
    def parse_transient_results(output):
        """Parse transient analysis results (to be implemented)"""
        # TODO: Implement transient parsing
        return {}