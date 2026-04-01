"""
simulation/netlist_generator.py

Handles SPICE netlist generation from circuit data
"""

import logging

from simulation.spice_sanitizer import sanitize_netlist_text, sanitize_spice_value, validate_wrdata_filepath

logger = logging.getLogger(__name__)


def generate_analysis_command(analysis_type: str, params: dict) -> str:
    """Generate a SPICE analysis directive from type and parameters.

    This is the single source of truth for mapping analysis type + params
    to a SPICE command string.  Both the dialog preview and the netlist
    generator delegate here.

    Args:
        analysis_type: Analysis type name (e.g. "DC Sweep", "AC Sweep").
        params: Analysis parameters dict (keys vary by type).

    Returns:
        SPICE directive string (e.g. ".dc V1 0 10 0.1"), or "" if
        the analysis type is unknown.
    """
    if analysis_type in ("DC Operating Point", "Operational Point"):
        return ".op"

    if analysis_type == "DC Sweep":
        source = params.get("source", "V1")
        start = params.get("min", 0)
        stop = params.get("max", 10)
        step = params.get("step", 0.1)
        return f".dc {source} {start} {stop} {step}"

    if analysis_type == "AC Sweep":
        fstart = params.get("fStart", 1)
        fstop = params.get("fStop", 1e6)
        points = params.get("points", 100)
        sweep_type = params.get("sweepType", params.get("sweep_type", "dec"))
        return f".ac {sweep_type} {points} {fstart} {fstop}"

    if analysis_type == "Transient":
        tstep = params.get("step", 0.001)
        tstop = params.get("duration", 1)
        tstart = params.get("startTime", params.get("start", 0))
        return f".tran {tstep} {tstop} {tstart}"

    if analysis_type == "Temperature Sweep":
        tstart = params.get("tempStart", -40)
        tstop = params.get("tempStop", 85)
        tstep = params.get("tempStep", 25)
        return f".step temp {tstart} {tstop} {tstep}"

    if analysis_type == "Noise":
        output = params.get("output_node", "out")
        source = params.get("source", "V1")
        fstart = params.get("fStart", 1)
        fstop = params.get("fStop", 1e6)
        points = params.get("points", 100)
        sweep_type = params.get("sweepType", params.get("sweep_type", "dec"))
        return f".noise v({output}) {source} {sweep_type} {points} {fstart} {fstop}"

    if analysis_type == "Sensitivity":
        output = params.get("output_node", "out")
        return f".sens v({output})"

    if analysis_type == "Transfer Function":
        output_var = params.get("output_var", "v(out)")
        input_source = params.get("input_source", "V1")
        return f".tf {output_var} {input_source}"

    if analysis_type == "Pole-Zero":
        inp = params.get("input_pos", "1")
        inn = params.get("input_neg", "0")
        outp = params.get("output_pos", "2")
        outn = params.get("output_neg", "0")
        tf_type = params.get("transfer_type", "vol")
        pz_type = params.get("pz_type", "pz")
        return f".pz {inp} {inn} {outp} {outn} {tf_type} {pz_type}"

    return ""


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
        spice_options=None,
        measurements=None,
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
            spice_options: Optional[dict[str, str]] - extra .options key=value pairs
            measurements: Optional[list[str]] - .meas directive strings
        """
        self.components = components
        self.wires = wires
        self.nodes = nodes
        self.terminal_to_node = terminal_to_node
        self.analysis_type = analysis_type
        self.analysis_params = analysis_params
        self.wrdata_filepath = validate_wrdata_filepath(wrdata_filepath)
        self.spice_options = spice_options or {}
        self.measurements = measurements or []
        self._is_temp_sweep = False

    def _sanitize_value(self, value: str) -> str:
        """Sanitize a component value before interpolation into the netlist."""
        return sanitize_spice_value(value)

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

        # Add subcircuit definitions from the subcircuit library
        self._inject_subcircuit_definitions(lines)

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
                if key not in node_map:
                    raise ValueError(
                        f"Unconnected terminal: {comp_id} terminal {i} ({comp.component_type}) is not wired to any node"
                    )
                node_num = node_map[key]
                node_str = node_labels.get(node_num, str(node_num))
                nodes.append(node_str)

            if comp.component_type == "Resistor":
                val = self._sanitize_value(comp.value)
                lines.append(f"{comp_id} {' '.join(nodes)} {val}")
            elif comp.component_type == "Capacitor":
                val = self._sanitize_value(comp.value)
                ic = f" IC={comp.initial_condition}" if getattr(comp, "initial_condition", None) else ""
                lines.append(f"{comp_id} {' '.join(nodes)} {val}{ic}")
            elif comp.component_type == "Inductor":
                val = self._sanitize_value(comp.value)
                ic = f" IC={comp.initial_condition}" if getattr(comp, "initial_condition", None) else ""
                lines.append(f"{comp_id} {' '.join(nodes)} {val}{ic}")
            elif comp.component_type == "Voltage Source":
                val = self._sanitize_value(comp.value)
                lines.append(f"{comp_id} {' '.join(nodes)} DC {val}")
            elif comp.component_type == "Current Source":
                val = self._sanitize_value(comp.value)
                lines.append(f"{comp_id} {' '.join(nodes)} DC {val}")
            elif comp.component_type == "AC Voltage Source":
                # Vxxx n+ n- AC magnitude phase
                val = self._sanitize_value(comp.value)
                lines.append(f"{comp_id} {' '.join(nodes)} AC {val}")
            elif comp.component_type == "AC Current Source":
                # Ixxx n+ n- AC magnitude phase
                val = self._sanitize_value(comp.value)
                lines.append(f"{comp_id} {' '.join(nodes)} AC {val}")
            elif comp.component_type == "Current Probe":
                # 0V voltage source for current measurement
                lines.append(f"{comp_id} {' '.join(nodes)} 0")
            elif comp.component_type == "Waveform Source":
                # Use get_spice_value() method if available, otherwise use value
                if hasattr(comp, "get_spice_value"):
                    spice_value = self._sanitize_value(comp.get_spice_value())
                else:
                    spice_value = self._sanitize_value(comp.value)
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
                val = self._sanitize_value(comp.value)
                lines.append(f"{comp_id} {nodes[2]} {nodes[3]} {nodes[0]} {nodes[1]} {val}")
            elif comp.component_type == "VCCS":
                # G<name> out+ out- ctrl+ ctrl- transconductance
                # Terminals: 0=ctrl+, 1=ctrl-, 2=out+, 3=out-
                val = self._sanitize_value(comp.value)
                lines.append(f"{comp_id} {nodes[2]} {nodes[3]} {nodes[0]} {nodes[1]} {val}")
            elif comp.component_type == "CCVS":
                # H<name> out+ out- Vname transresistance
                # Insert hidden 0V voltage source for current sensing
                # Terminals: 0=ctrl+, 1=ctrl-, 2=out+, 3=out-
                val = self._sanitize_value(comp.value)
                sense_name = f"Vsense_{comp_id}"
                lines.append(f"{sense_name} {nodes[0]} {nodes[1]} 0")
                lines.append(f"{comp_id} {nodes[2]} {nodes[3]} {sense_name} {val}")
            elif comp.component_type == "CCCS":
                # F<name> out+ out- Vname gain
                # Insert hidden 0V voltage source for current sensing
                # Terminals: 0=ctrl+, 1=ctrl-, 2=out+, 3=out-
                val = self._sanitize_value(comp.value)
                sense_name = f"Vsense_{comp_id}"
                lines.append(f"{sense_name} {nodes[0]} {nodes[1]} 0")
                lines.append(f"{comp_id} {nodes[2]} {nodes[3]} {sense_name} {val}")
            elif comp.component_type == "BJT NPN":
                # Q<name> collector base emitter model_name
                # Terminals: 0=collector, 1=base, 2=emitter
                val = self._sanitize_value(comp.value)
                lines.append(f"{comp_id} {nodes[0]} {nodes[1]} {nodes[2]} {val}")
            elif comp.component_type == "BJT PNP":
                # Q<name> collector base emitter model_name
                val = self._sanitize_value(comp.value)
                lines.append(f"{comp_id} {nodes[0]} {nodes[1]} {nodes[2]} {val}")
            elif comp.component_type in ("MOSFET NMOS", "MOSFET PMOS"):
                # M<name> drain gate source bulk model_name
                # Terminals: 0=drain, 1=gate, 2=source
                # Bulk (body) tied to source for simplicity
                val = self._sanitize_value(comp.value)
                lines.append(f"{comp_id} {nodes[0]} {nodes[1]} {nodes[2]} {nodes[2]} {val}")
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
            elif comp.component_type == "Transformer":
                # Transformer modeled as two coupled inductors + K coupling
                # value = "Lprimary Lsecondary coupling" e.g. "10mH 10mH 0.99"
                # Terminals: 0=prim+, 1=prim-, 2=sec+, 3=sec-
                sanitized_val = self._sanitize_value(comp.value)
                parts = sanitized_val.split()
                l_prim = parts[0] if len(parts) > 0 else "10mH"
                l_sec = parts[1] if len(parts) > 1 else "10mH"
                coupling = parts[2] if len(parts) > 2 else "0.99"
                prim_name = f"L_prim_{comp_id}"
                sec_name = f"L_sec_{comp_id}"
                lines.append(f"{prim_name} {nodes[0]} {nodes[1]} {l_prim}")
                lines.append(f"{sec_name} {nodes[2]} {nodes[3]} {l_sec}")
                lines.append(f"K_{comp_id} {prim_name} {sec_name} {coupling}")
            elif comp.get_spice_symbol() == "X":
                # Generic subcircuit instance (from subcircuit library)
                # X<name> node1 node2 ... subckt_name
                lines.append(f"X{comp_id} {' '.join(nodes)} {comp.value}")

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

        # Add extra SPICE options (e.g. relaxed tolerances for convergence retry)
        if self.spice_options:
            pairs = " ".join(f"{k}={v}" for k, v in self.spice_options.items())
            lines.append(f".options {pairs}")

        # Add .meas measurement directives
        if self.measurements:
            lines.append("")
            lines.append("* Measurement Directives")
            for meas in self.measurements:
                directive = meas.strip()
                if not directive.lower().startswith(".meas"):
                    directive = f".meas {directive}"
                lines.append(directive)

        # Add analysis command
        lines.extend(self._generate_analysis_commands(node_labels, node_map))

        lines.append("")
        lines.append(".end")

        # Defence-in-depth: scan final netlist for dangerous directives
        return sanitize_netlist_text("\n".join(lines))

    def _inject_subcircuit_definitions(self, lines):
        """Inject .subckt definitions for any subcircuit-library components used."""
        try:
            from models.subcircuit_library import SubcircuitLibrary

            library = SubcircuitLibrary()
        except Exception:
            return

        subckt_names_used = set()
        for comp in self.components.values():
            if comp.get_spice_symbol() == "X" and comp.component_type != "Op-Amp":
                subckt_names_used.add(comp.value)

        for subckt_name in sorted(subckt_names_used):
            defn = library.get(subckt_name)
            if defn is not None:
                lines.append(f"* {subckt_name} Subcircuit")
                lines.append(defn.spice_definition)
                lines.append("")

    def _generate_analysis_commands(self, node_labels, node_map):
        """Generate analysis-specific SPICE commands"""
        lines = ["", "* Analysis Command"]

        if self.analysis_type == "DC Sweep":
            # Special handling: fall back to first voltage source if none specified
            params = self.analysis_params
            source_name = params.get("source")
            if not source_name:
                voltage_sources = [c for c in self.components.values() if c.component_type == "Voltage Source"]
                source_name = voltage_sources[0].component_id if voltage_sources else None
            if not source_name:
                lines.append("* Warning: DC Sweep requires a voltage source")
                lines.append(".op")
            else:
                effective_params = dict(params, source=source_name)
                lines.append(generate_analysis_command(self.analysis_type, effective_params))
        elif self.analysis_type == "Temperature Sweep":
            # Temperature sweep needs .op before .step
            lines.append(".op")
            lines.append(generate_analysis_command(self.analysis_type, self.analysis_params))
            # Mark that we need the temperature vector printed alongside voltages
            self._is_temp_sweep = True
        else:
            lines.append(generate_analysis_command(self.analysis_type, self.analysis_params))

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

            is_ac = self.analysis_type == "AC Sweep"
            # For AC analysis, use vm() for magnitude or vdb() for
            # decibels instead of v() which returns the real part of
            # the complex voltage.
            use_db = is_ac and str(self.analysis_params.get("use_db", "No")).lower() in ("yes", "true", "1")
            ac_mag_func = "vdb" if use_db else "vm"

            all_print_vars = []
            if labeled_nodes_to_print:
                for label in sorted(labeled_nodes_to_print.values()):
                    if is_ac:
                        all_print_vars.append(f"{ac_mag_func}({label})")
                        all_print_vars.append(f"vp({label})")
                    else:
                        all_print_vars.append(f"v({label})")
            elif nodes_to_print:
                for node in sorted(list(nodes_to_print)):
                    if is_ac:
                        all_print_vars.append(f"{ac_mag_func}({node})")
                        all_print_vars.append(f"vp({node})")
                    else:
                        all_print_vars.append(f"v({node})")

            # Add resistor voltages to the print list
            all_print_vars.extend(resistor_voltages_print)

            # Add current probe measurements: i(probe_id) for each Current Probe
            probes = [c for c in self.components.values() if c.component_type == "Current Probe"]
            for probe in sorted(probes, key=lambda c: c.component_id):
                all_print_vars.append(f"i({probe.component_id})")

            # Note: for DC sweep, the sweep variable (v-sweep) is automatically
            # included as the first column in wrdata output when wr_singlescale
            # is set. Do NOT add the source name (e.g. "v1") — ngspice does not
            # expose it as a vector; the sweep column is always named "v-sweep".

            # For temperature sweep, prepend the temperature vector so the
            # parser can extract temperature alongside node voltages.
            if getattr(self, "_is_temp_sweep", False) and all_print_vars:
                all_print_vars.insert(0, "temp-sweep")

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
