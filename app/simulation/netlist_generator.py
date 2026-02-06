"""
simulation/netlist_generator.py

Handles SPICE netlist generation from circuit data
"""


class NetlistGenerator:
    """Generates SPICE netlists from circuit components and nodes.

    Accepts pure Python model objects (ComponentData, WireData, NodeData)
    with no Qt dependencies.
    """

    def __init__(self, components, wires, nodes, terminal_to_node, analysis_type, analysis_params):
        """
        Args:
            components: Dict[str, ComponentData] - component models keyed by ID
            wires: List[WireData] - wire connection models
            nodes: List[NodeData] - electrical node models
            terminal_to_node: Dict[tuple, NodeData] - (comp_id, term_idx) -> node
            analysis_type: str
            analysis_params: dict
        """
        self.components = components
        self.wires = wires
        self.nodes = nodes
        self.terminal_to_node = terminal_to_node
        self.analysis_type = analysis_type
        self.analysis_params = analysis_params
    
    def generate(self):
        """Generate complete SPICE netlist"""
        lines = ["My Test Circuit", "* Generated netlist", ""]
        
        # Check for op-amps to add subcircuit
        has_opamp = any(c.component_type == 'Op-Amp' for c in self.components.values())
        if has_opamp:
            lines.append("* Ideal Op-Amp Subcircuit")
            lines.append(".subckt OPAMP_IDEAL inp inn out")
            lines.append("E_amp out 0 inp inn 1e6")
            lines.append("R_out out 0 1e-3")
            lines.append(".ends")
            lines.append("")

        # Build node connectivity map
        node_map = {}  # (comp_id, term_index) -> node_number
        next_node = 1
        
        # Process wires to assign nodes
        for wire in self.wires:
            start_key = (wire.start_component_id, wire.start_terminal)
            end_key = (wire.end_component_id, wire.end_terminal)
            
            start_node = node_map.get(start_key)
            end_node = node_map.get(end_key)
            
            if start_node is None and end_node is None:
                node_map[start_key] = next_node
                node_map[end_key] = next_node
                next_node += 1
            elif start_node is None:
                node_map[start_key] = end_node
            elif end_node is None:
                node_map[end_key] = start_node
                pass
            else:
                merged_node = min(start_node, end_node)
                for key, node in list(node_map.items()):
                    if node == max(start_node, end_node):
                        node_map[key] = merged_node
        
        # Ground nodes should be 0
        ground_comps = [c for c in self.components.values() 
                       if c.component_type == 'Ground']
        for gnd in ground_comps:
            key = (gnd.component_id, 0)
            if key in node_map:
                gnd_node = node_map[key]
                for k in node_map:
                    if node_map[k] == gnd_node:
                        node_map[k] = 0
        
        # Create mapping from node numbers to node labels
        node_labels = {}  # node_number -> label
        node_comps = [c for c in self.nodes if hasattr(c, 'get_label')]
        for node_comp in node_comps:
            # Find which terminals belong to this node
            for terminal_key, terminal_node in self.terminal_to_node.items():
                if terminal_node == node_comp:
                    if terminal_key in node_map:
                        node_num = node_map[terminal_key]
                        node_labels[node_num] = node_comp.get_label()
                        break
        
        # Generate component lines
        for comp in self.components.values():
            if comp.component_type in ['Ground']:
                continue
            
            comp_id = comp.component_id
            nodes = []
            for i in range(comp.get_terminal_count()):
                key = (comp_id, i)
                node_num = node_map.get(key, 999)
                node_str = node_labels.get(node_num, str(node_num))
                nodes.append(node_str)
            
            if comp.component_type == 'Resistor':
                lines.append(f"{comp_id} {' '.join(nodes)} {comp.value}")
            elif comp.component_type == 'Capacitor':
                lines.append(f"{comp_id} {' '.join(nodes)} {comp.value}")
            elif comp.component_type == 'Inductor':
                lines.append(f"{comp_id} {' '.join(nodes)} {comp.value}")
            elif comp.component_type == 'Voltage Source':
                lines.append(f"{comp_id} {' '.join(nodes)} DC {comp.value}")
            elif comp.component_type == 'Current Source':
                lines.append(f"{comp_id} {' '.join(nodes)} DC {comp.value}")
            elif comp.component_type == 'Waveform Source':
                # Use get_spice_value() method if available, otherwise use value
                if hasattr(comp, 'get_spice_value'):
                    spice_value = comp.get_spice_value()
                else:
                    spice_value = comp.value
                lines.append(f"{comp_id} {' '.join(nodes)} {spice_value}")
            elif comp.component_type == 'Op-Amp':
                # Map terminals to subcircuit nodes: inp, inn, out
                # Terminal 1 is non-inverting (inp), 0 is inverting (inn), 2 is output (out)
                opamp_nodes = [nodes[1], nodes[0], nodes[2]]
                lines.append(f"X{comp_id} {' '.join(opamp_nodes)} OPAMP_IDEAL")
        
        # Add comments about labeled nodes
        if node_labels:
            lines.append("")
            lines.append("* Labeled Nodes:")
            for node_num, label in sorted(node_labels.items()):
                lines.append(f"* Node {node_num} = {label}")
        
        # Add simulation options
        lines.append("")
        lines.append("* Simulation Options")
        lines.append(".option TEMP=27")
        lines.append(".option TNOM=27")
        
        # Add analysis command
        lines.extend(self._generate_analysis_commands(node_labels, node_map))
        
        lines.append("")
        lines.append(".end")
        
        return "\n".join(lines)
    
    def _generate_analysis_commands(self, node_labels, node_map):
        """Generate analysis-specific SPICE commands"""
        lines = ["", "* Analysis Command"]

        if self.analysis_type in ["DC Operating Point", "Operational Point"]:
            lines.append(".op")

        elif self.analysis_type == "DC Sweep":
            params = self.analysis_params
            voltage_sources = [c for c in self.components.values()
                             if c.component_type == 'Voltage Source']
            if voltage_sources:
                source_name = voltage_sources[0].component_id
                lines.append(f".dc {source_name} {params['min']} {params['max']} {params['step']}")
                pass
            else:
                lines.append("* Warning: DC Sweep requires a voltage source")
                lines.append(".op")

        elif self.analysis_type == "AC Sweep":
            params = self.analysis_params
            sweep_type = params.get('sweep_type', 'dec')
            lines.append(f".ac {sweep_type} {params['points']} {params['fStart']} {params['fStop']}")

        elif self.analysis_type == "Transient":
            params = self.analysis_params
            tstart = params.get('start', 0)
            lines.append(f".tran {params['step']} {params['duration']} {tstart}")

        # Add control block for running simulation and getting output
        lines.append("")
        lines.append("* Control block for batch execution")
        lines.append(".control")
        lines.append("run")  # Run first to populate vectors
        lines.append("")
        lines.append("* Calculate voltage drops for all resistors")

        # Generate appropriate print/plot commands based on analysis type
        if node_labels:
            print_vars = " ".join([f"v({label})" for label in node_labels.values()])
            pass
        else:
            print_vars = "all"
        # Define variables for voltages across resistors
        resistor_voltages_let = []
        resistor_voltages_print = []
        resistors = [c for c in self.components.values() if c.component_type == 'Resistor']
        for res in resistors:
            try:
                node1_num = node_map.get((res.component_id, 0))
                node2_num = node_map.get((res.component_id, 1))

                if node1_num is not None and node2_num is not None:
                    node1_str = node_labels.get(node1_num, str(node1_num))
                    node2_str = node_labels.get(node2_num, str(node2_num))
                    
                    # Standardize to lowercase for easier parsing, e.g., v_r1
                    alias = f"v_{res.component_id.lower()}"
                    
                    if node1_num == 0:  # Connected to ground
                        let_expression = f"-v({node2_str})"
                    elif node2_num == 0:  # Connected to ground
                        let_expression = f"v({node1_str})"
                    else:
                        let_expression = f"v({node1_str}) - v({node2_str})"
                    
                    resistor_voltages_let.append(f"let {alias} = {let_expression}")
                    resistor_voltages_print.append(alias)
            except Exception as e:
                # This may be too noisy, but it's useful for debugging
                print(f"Warning: Could not create voltage calculation for {res.component_id}: {e}")
        
        if resistor_voltages_let:
            lines.extend(resistor_voltages_let)
        
        lines.append("")
        lines.append("* Print to stdout (for parser)")
        
        # Generate appropriate print commands, excluding ground node 0.
        nodes_to_print = set(node_map.values())
        nodes_to_print.discard(0)
        labeled_nodes_to_print = {num: label for num, label in node_labels.items() if num != 0}

        all_print_vars = []
        if labeled_nodes_to_print:
            all_print_vars.extend([f"v({label})" for label in sorted(labeled_nodes_to_print.values())])
        elif nodes_to_print:
            all_print_vars.extend([f"v({node})" for node in sorted(list(nodes_to_print))])
        
        # Add resistor voltages to the print list
        all_print_vars.extend(resistor_voltages_print)
        
        print_vars = " ".join(all_print_vars)
        
        if print_vars:
            lines.append(f"print {print_vars}")
        
        lines.append("")
        lines.append("* Save to file (for backup)")
        lines.append("set wr_vecnames")
        lines.append("set wr_singlescale")
        
        if print_vars:
            lines.append(f"wrdata transient_data.txt {print_vars}")
            
        lines.append(".endc")

        return lines