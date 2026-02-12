"""
simulation/netlist_generator.py

Handles SPICE netlist generation from circuit data
"""

import logging

logger = logging.getLogger(__name__)


class NetlistGenerator:
    """Generates SPICE netlists from circuit components and nodes.

    Accepts pure Python model objects (ComponentData, WireData, NodeData)
    with no Qt dependencies.
    """

    def __init__(
        self,
        components,
        wires,
        nodes,
        terminal_to_node,
        analysis_type,
        analysis_params,
        wrdata_filepath="transient_data.txt",
    ):
        """
        Args:
            components: Dict[str, ComponentData] - component models keyed by ID
            wires: List[WireData] - wire connection models
            nodes: List[NodeData] - electrical node models
            terminal_to_node: Dict[tuple, NodeData] - (comp_id, term_idx) -> node
            analysis_type: str
            analysis_params: dict
            wrdata_filepath: str - path for wrdata output file
        """
        self.components = components
        self.wires = wires
        self.nodes = nodes
        self.terminal_to_node = terminal_to_node
        self.analysis_type = analysis_type
        self.analysis_params = analysis_params
        self.wrdata_filepath = wrdata_filepath

    def generate(self):
        """Generate complete SPICE netlist"""
        lines = ["My Test Circuit", "* Generated netlist", ""]

        # Add op-amp subcircuit definitions for each model used
        from models.component import OPAMP_SUBCIRCUITS

        opamp_models_used = set()
        for c in self.components.values():
            if c.component_type == "Op-Amp":
                opamp_models_used.add(c.value if c.value in OPAMP_SUBCIRCUITS else "Ideal")
        for model_name in sorted(opamp_models_used):
            lines.append(f"* {model_name} Op-Amp Subcircuit")
            lines.append(OPAMP_SUBCIRCUITS[model_name])
            lines.append("")

        # Add user-defined subcircuit definitions (deduplicated by name)
        subckt_defs_emitted = set()
        for c in self.components.values():
            if (
                c.component_type == "Subcircuit"
                and c.subcircuit_name
                and c.subcircuit_name not in subckt_defs_emitted
                and c.subcircuit_definition
            ):
                lines.append(f"* {c.subcircuit_name} Subcircuit")
                lines.append(c.subcircuit_definition)
                lines.append("")
                subckt_defs_emitted.add(c.subcircuit_name)

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
            else:
                merged_node = min(start_node, end_node)
                for key, node in list(node_map.items()):
                    if node == max(start_node, end_node):
                        node_map[key] = merged_node

        # Ground nodes should be 0
        ground_comps = [c for c in self.components.values() if c.component_type == "Ground"]
        for gnd in ground_comps:
            key = (gnd.component_id, 0)
            if key in node_map:
                gnd_node = node_map[key]
                for k in node_map:
                    if node_map[k] == gnd_node:
                        node_map[k] = 0

        # Create mapping from node numbers to node labels
        node_labels = {}  # node_number -> label
        node_comps = [c for c in self.nodes if hasattr(c, "get_label")]
        for node_comp in node_comps:
            # Find which terminals belong to this node
            for terminal_key, terminal_node in self.terminal_to_node.items():
                if terminal_node == node_comp:
                    if terminal_key in node_map:
                        node_num = node_map[terminal_key]
                        node_labels[node_num] = node_comp.get_label()
                        break

        # Build diode model name map: (type, value) → shared model name
        _diode_base = {"Diode": "D_Ideal", "LED": "D_LED", "Zener Diode": "D_Zener"}
        self._diode_model_map = {}
        _used_names = set()
        for comp in sorted(self.components.values(), key=lambda c: c.component_id):
            if comp.component_type not in _diode_base:
                continue
            key = (comp.component_type, comp.value)
            if key in self._diode_model_map:
                continue
            base = _diode_base[comp.component_type]
            name = base
            suffix = 2
            while name in _used_names:
                name = f"{base}_{suffix}"
                suffix += 1
            self._diode_model_map[key] = name
            _used_names.add(name)

        # Generate component lines
        for comp in self.components.values():
            if comp.component_type in ["Ground"]:
                continue

            comp_id = comp.component_id
            nodes = []
            for i in range(comp.get_terminal_count()):
                key = (comp_id, i)
                node_num = node_map.get(key, 999)
                node_str = node_labels.get(node_num, str(node_num))
                nodes.append(node_str)

            if comp.component_type == "Resistor":
                lines.append(f"{comp_id} {' '.join(nodes)} {comp.value}")
            elif comp.component_type == "Capacitor":
                lines.append(f"{comp_id} {' '.join(nodes)} {comp.value}")
            elif comp.component_type == "Inductor":
                lines.append(f"{comp_id} {' '.join(nodes)} {comp.value}")
            elif comp.component_type == "Voltage Source":
                lines.append(f"{comp_id} {' '.join(nodes)} DC {comp.value}")
            elif comp.component_type == "Current Source":
                lines.append(f"{comp_id} {' '.join(nodes)} DC {comp.value}")
            elif comp.component_type == "Waveform Source":
                # Use get_spice_value() method if available, otherwise use value
                if hasattr(comp, "get_spice_value"):
                    spice_value = comp.get_spice_value()
                else:
                    spice_value = comp.value
                lines.append(f"{comp_id} {' '.join(nodes)} {spice_value}")
            elif comp.component_type == "Op-Amp":
                # Map terminals to subcircuit nodes: inp, inn, out
                # Terminal 1 is non-inverting (inp), 0 is inverting (inn), 2 is output (out)
                opamp_nodes = [nodes[1], nodes[0], nodes[2]]
                model = comp.value if comp.value in OPAMP_SUBCIRCUITS else "Ideal"
                subckt_name = "OPAMP_IDEAL" if model == "Ideal" else model
                lines.append(f"X{comp_id} {' '.join(opamp_nodes)} {subckt_name}")
            elif comp.component_type == "VCVS":
                # E<name> out+ out- ctrl+ ctrl- gain
                # Terminals: 0=ctrl+, 1=ctrl-, 2=out+, 3=out-
                lines.append(f"{comp_id} {nodes[2]} {nodes[3]} {nodes[0]} {nodes[1]} {comp.value}")
            elif comp.component_type == "VCCS":
                # G<name> out+ out- ctrl+ ctrl- transconductance
                # Terminals: 0=ctrl+, 1=ctrl-, 2=out+, 3=out-
                lines.append(f"{comp_id} {nodes[2]} {nodes[3]} {nodes[0]} {nodes[1]} {comp.value}")
            elif comp.component_type == "CCVS":
                # H<name> out+ out- Vname transresistance
                # Insert hidden 0V voltage source for current sensing
                # Terminals: 0=ctrl+, 1=ctrl-, 2=out+, 3=out-
                sense_name = f"Vsense_{comp_id}"
                lines.append(f"{sense_name} {nodes[0]} {nodes[1]} 0")
                lines.append(f"{comp_id} {nodes[2]} {nodes[3]} {sense_name} {comp.value}")
            elif comp.component_type == "CCCS":
                # F<name> out+ out- Vname gain
                # Insert hidden 0V voltage source for current sensing
                # Terminals: 0=ctrl+, 1=ctrl-, 2=out+, 3=out-
                sense_name = f"Vsense_{comp_id}"
                lines.append(f"{sense_name} {nodes[0]} {nodes[1]} 0")
                lines.append(f"{comp_id} {nodes[2]} {nodes[3]} {sense_name} {comp.value}")
            elif comp.component_type == "BJT NPN":
                # Q<name> collector base emitter model_name
                # Terminals: 0=collector, 1=base, 2=emitter
                lines.append(f"{comp_id} {nodes[0]} {nodes[1]} {nodes[2]} {comp.value}")
            elif comp.component_type == "BJT PNP":
                # Q<name> collector base emitter model_name
                lines.append(f"{comp_id} {nodes[0]} {nodes[1]} {nodes[2]} {comp.value}")
            elif comp.component_type in ("MOSFET NMOS", "MOSFET PMOS"):
                # M<name> drain gate source bulk model_name
                # Terminals: 0=drain, 1=gate, 2=source
                # Bulk (body) tied to source for simplicity
                lines.append(f"{comp_id} {nodes[0]} {nodes[1]} {nodes[2]} {nodes[2]} {comp.value}")
            elif comp.component_type == "VC Switch":
                # S<name> switch+ switch- ctrl+ ctrl- model_name
                # Terminals: 0=ctrl+, 1=ctrl-, 2=switch+, 3=switch-
                model_name = f"SW_{comp_id}"
                lines.append(f"{comp_id} {nodes[2]} {nodes[3]} {nodes[0]} {nodes[1]} {model_name}")
            elif comp.component_type in ("Diode", "LED", "Zener Diode"):
                # D<name> anode cathode model_name
                # Terminals: 0=anode, 1=cathode
                model_name = self._diode_model_map.get((comp.component_type, comp.value), f"D_{comp_id}")
                lines.append(f"{comp_id} {nodes[0]} {nodes[1]} {model_name}")
            elif comp.component_type == "Subcircuit":
                # X<name> node1 node2 ... subckt_name
                subckt_name = comp.subcircuit_name or comp.value or "UNKNOWN"
                lines.append(f"{comp_id} {' '.join(nodes)} {subckt_name}")

        # Add BJT model directives
        bjt_models = set()
        for comp in self.components.values():
            if comp.component_type == "BJT NPN":
                bjt_models.add(("NPN", comp.value))
            elif comp.component_type == "BJT PNP":
                bjt_models.add(("PNP", comp.value))
        if bjt_models:
            lines.append("")
            lines.append("* BJT Model Definitions")
            for polarity, model_name in sorted(bjt_models):
                if model_name == "2N3904":
                    lines.append(f".model {model_name} NPN(BF=300 IS=1e-14 VAF=100)")
                elif model_name == "2N3906":
                    lines.append(f".model {model_name} PNP(BF=200 IS=1e-14 VAF=100)")
                else:
                    lines.append(f".model {model_name} {polarity}(BF=100 IS=1e-14)")

        # Add MOSFET model directives
        mosfet_models = set()
        for comp in self.components.values():
            if comp.component_type == "MOSFET NMOS":
                mosfet_models.add(("NMOS", comp.value))
            elif comp.component_type == "MOSFET PMOS":
                mosfet_models.add(("PMOS", comp.value))
        if mosfet_models:
            lines.append("")
            lines.append("* MOSFET Model Definitions")
            for polarity, model_name in sorted(mosfet_models):
                if polarity == "NMOS":
                    lines.append(f".model {model_name} NMOS(VTO=0.7 KP=110u)")
                else:
                    lines.append(f".model {model_name} PMOS(VTO=-0.7 KP=50u)")

        # Add VC Switch model directives
        vc_switches = [c for c in self.components.values() if c.component_type == "VC Switch"]
        if vc_switches:
            lines.append("")
            lines.append("* Voltage-Controlled Switch Model Definitions")
            for sw in vc_switches:
                model_name = f"SW_{sw.component_id}"
                lines.append(f".model {model_name} SW({sw.value})")

        # Add diode model directives (deduplicated by type + params)
        if self._diode_model_map:
            lines.append("")
            lines.append("* Diode Model Definitions")
            for (_dtype, params), model_name in sorted(self._diode_model_map.items(), key=lambda kv: kv[1]):
                lines.append(f".model {model_name} D({params})")

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
            voltage_sources = [c for c in self.components.values() if c.component_type == "Voltage Source"]
            if voltage_sources:
                source_name = voltage_sources[0].component_id
                lines.append(f".dc {source_name} {params['min']} {params['max']} {params['step']}")
            else:
                lines.append("* Warning: DC Sweep requires a voltage source")
                lines.append(".op")

        elif self.analysis_type == "AC Sweep":
            params = self.analysis_params
            sweep_type = params.get("sweep_type", "dec")
            lines.append(f".ac {sweep_type} {params['points']} {params['fStart']} {params['fStop']}")

        elif self.analysis_type == "Transient":
            params = self.analysis_params
            tstart = params.get("start", 0)
            lines.append(f".tran {params['step']} {params['duration']} {tstart}")

        elif self.analysis_type == "Temperature Sweep":
            params = self.analysis_params
            temp_start = params.get("tempStart", -40)
            temp_stop = params.get("tempStop", 85)
            temp_step = params.get("tempStep", 25)
            # DC operating point as the base analysis, swept over temperature
            lines.append(".op")
            lines.append(f".step temp {temp_start} {temp_stop} {temp_step}")

        elif self.analysis_type == "Noise":
            params = self.analysis_params
            output_node = params.get("output_node", "out")
            source = params.get("source", "V1")
            sweep_type = params.get("sweepType", "dec")
            pts = params.get("points", 100)
            fstart = params.get("fStart", 1)
            fstop = params.get("fStop", 1e6)
            lines.append(f".noise v({output_node}) {source} {sweep_type} {pts} {fstart} {fstop}")

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
        else:
            print_vars = "all"
        # Define variables for voltages across resistors
        resistor_voltages_let = []
        resistor_voltages_print = []
        resistors = [c for c in self.components.values() if c.component_type == "Resistor"]
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
            except (KeyError, TypeError, AttributeError) as e:
                logger.warning(
                    "Could not create voltage calculation for %s: %s",
                    res.component_id,
                    e,
                )

        if resistor_voltages_let:
            lines.extend(resistor_voltages_let)

        lines.append("")
        lines.append("* Print to stdout (for parser)")

        if self.analysis_type == "Noise":
            # Noise analysis prints spectral density vectors
            lines.append("setplot noise1")
            lines.append("print onoise_spectrum inoise_spectrum")
            lines.append("")
            lines.append("* Save to file (for backup)")
            lines.append("set wr_vecnames")
            lines.append("set wr_singlescale")
            wrdata_path = self.wrdata_filepath.replace("\\", "/")
            lines.append(f"wrdata {wrdata_path} onoise_spectrum inoise_spectrum")
        else:
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
                # Use forward slashes for ngspice compatibility on all platforms
                wrdata_path = self.wrdata_filepath.replace("\\", "/")
                lines.append(f"wrdata {wrdata_path} {print_vars}")

        lines.append(".endc")

        return lines
