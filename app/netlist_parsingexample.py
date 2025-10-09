"""
SPICE Netlist Parser
A comprehensive parser for SPICE netlist files with JSON export/import capabilities.
Designed to integrate with Qt GUI applications for circuit design.
"""

import re
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from enum import Enum


class ComponentType(Enum):
    """Enumeration of SPICE component types"""
    RESISTOR = 'R'
    CAPACITOR = 'C'
    INDUCTOR = 'L'
    VOLTAGE_SOURCE = 'V'
    CURRENT_SOURCE = 'I'
    DIODE = 'D'
    BJT = 'Q'
    MOSFET = 'M'
    JFET = 'J'
    SUBCIRCUIT = 'X'
    VCVS = 'E'  # Voltage Controlled Voltage Source
    CCCS = 'F'  # Current Controlled Current Source
    VCCS = 'G'  # Voltage Controlled Current Source
    CCVS = 'H'  # Current Controlled Voltage Source
    SWITCH = 'S'
    UNKNOWN = 'U'


@dataclass
class Component:
    """Represents a SPICE component"""
    name: str
    type: str
    nodes: List[str]
    value: Optional[str] = None
    model: Optional[str] = None
    parameters: Dict[str, str] = field(default_factory=dict)
    line_number: int = 0
    
    def to_spice(self) -> str:
        """Convert component back to SPICE format"""
        parts = [self.name] + self.nodes
        if self.value:
            parts.append(self.value)
        if self.model:
            parts.append(self.model)
        for key, val in self.parameters.items():
            parts.append(f"{key}={val}")
        return ' '.join(parts)


@dataclass
class Subcircuit:
    """Represents a SPICE subcircuit definition"""
    name: str
    ports: List[str]
    components: List[Component] = field(default_factory=list)
    models: List[Dict[str, Any]] = field(default_factory=list)
    parameters: Dict[str, str] = field(default_factory=dict)
    
    def to_spice(self) -> str:
        """Convert subcircuit back to SPICE format"""
        lines = [f".subckt {self.name} {' '.join(self.ports)}"]
        for comp in self.components:
            lines.append(comp.to_spice())
        lines.append(".ends")
        return '\n'.join(lines)


@dataclass
class Model:
    """Represents a SPICE model definition"""
    name: str
    model_type: str
    parameters: Dict[str, str] = field(default_factory=dict)
    
    def to_spice(self) -> str:
        """Convert model back to SPICE format"""
        params = ' '.join(f"{k}={v}" for k, v in self.parameters.items())
        return f".model {self.name} {self.model_type} {params}"


class SpiceNetlist:
    """Main class representing a complete SPICE netlist"""
    
    def __init__(self):
        self.title: str = ""
        self.components: List[Component] = []
        self.subcircuits: Dict[str, Subcircuit] = {}
        self.models: Dict[str, Model] = {}
        self.control_statements: List[str] = []
        self.comments: List[str] = []
        self.includes: List[str] = []
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert netlist to dictionary for JSON serialization"""
        return {
            'title': self.title,
            'components': [asdict(c) for c in self.components],
            'subcircuits': {name: asdict(sc) for name, sc in self.subcircuits.items()},
            'models': {name: asdict(m) for name, m in self.models.items()},
            'control_statements': self.control_statements,
            'comments': self.comments,
            'includes': self.includes
        }
    
    def to_json(self, filepath: str, indent: int = 2):
        """Export netlist to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=indent)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SpiceNetlist':
        """Create netlist from dictionary"""
        netlist = cls()
        netlist.title = data.get('title', '')
        netlist.components = [Component(**c) for c in data.get('components', [])]
        netlist.subcircuits = {
            name: Subcircuit(**sc) for name, sc in data.get('subcircuits', {}).items()
        }
        netlist.models = {
            name: Model(**m) for name, m in data.get('models', {}).items()
        }
        netlist.control_statements = data.get('control_statements', [])
        netlist.comments = data.get('comments', [])
        netlist.includes = data.get('includes', [])
        return netlist
    
    @classmethod
    def from_json(cls, filepath: str) -> 'SpiceNetlist':
        """Import netlist from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def to_spice(self) -> str:
        """Convert netlist back to SPICE format"""
        lines = [self.title]
        
        for comment in self.comments:
            lines.append(f"* {comment}")
        
        for include in self.includes:
            lines.append(f".include {include}")
        
        for model in self.models.values():
            lines.append(model.to_spice())
        
        for subcircuit in self.subcircuits.values():
            lines.append(subcircuit.to_spice())
        
        for component in self.components:
            lines.append(component.to_spice())
        
        for statement in self.control_statements:
            lines.append(statement)
        
        lines.append(".end")
        return '\n'.join(lines)


class SpiceParser:
    """Parser for SPICE netlist files"""
    
    def __init__(self):
        self.netlist = SpiceNetlist()
        self.current_subcircuit: Optional[Subcircuit] = None
        
    def parse_file(self, filepath: str) -> SpiceNetlist:
        """Parse a SPICE netlist file"""
        with open(filepath, 'r') as f:
            content = f.read()
        return self.parse(content)
    
    def parse(self, content: str) -> SpiceNetlist:
        """Parse SPICE netlist content"""
        lines = self._preprocess_lines(content)
        
        if lines:
            self.netlist.title = lines[0]
            lines = lines[1:]
        
        for line_num, line in enumerate(lines, start=2):
            self._parse_line(line, line_num)
        
        return self.netlist
    
    def _preprocess_lines(self, content: str) -> List[str]:
        """Preprocess netlist content: handle continuations and remove empty lines"""
        lines = []
        current_line = ""
        
        for raw_line in content.split('\n'):
            # Remove inline comments (after $)
            if '$' in raw_line:
                raw_line = raw_line.split('$')[0]
            
            line = raw_line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Handle continuation lines
            if line.startswith('+'):
                current_line += ' ' + line[1:].strip()
            else:
                if current_line:
                    lines.append(current_line)
                current_line = line
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def _parse_line(self, line: str, line_num: int):
        """Parse a single line of the netlist"""
        # Skip comments
        if line.startswith('*'):
            self.netlist.comments.append(line[1:].strip())
            return
        
        # Handle control statements (start with .)
        if line.startswith('.'):
            self._parse_control_statement(line, line_num)
        else:
            # Parse component
            self._parse_component(line, line_num)
    
    def _parse_control_statement(self, line: str, line_num: int):
        """Parse control statements (.model, .subckt, .ends, etc.)"""
        parts = line.split()
        command = parts[0].lower()
        
        if command == '.subckt':
            name = parts[1]
            ports = parts[2:]
            self.current_subcircuit = Subcircuit(name=name, ports=ports)
        
        elif command == '.ends':
            if self.current_subcircuit:
                self.netlist.subcircuits[self.current_subcircuit.name] = self.current_subcircuit
                self.current_subcircuit = None
        
        elif command == '.model':
            name = parts[1]
            model_type = parts[2]
            params = self._parse_parameters(' '.join(parts[3:]))
            model = Model(name=name, model_type=model_type, parameters=params)
            self.netlist.models[name] = model
        
        elif command == '.include':
            self.netlist.includes.append(' '.join(parts[1:]))
        
        elif command == '.end':
            pass  # End of netlist
        
        else:
            # Other control statements (analysis commands, etc.)
            self.netlist.control_statements.append(line)
    
    def _parse_component(self, line: str, line_num: int):
        """Parse a component line"""
        parts = line.split()
        
        if len(parts) < 2:
            return
        
        name = parts[0]
        comp_type = name[0].upper()
        
        # Determine component type and parse accordingly
        component = self._create_component(name, comp_type, parts[1:], line_num)
        
        if self.current_subcircuit:
            self.current_subcircuit.components.append(component)
        else:
            self.netlist.components.append(component)
    
    def _create_component(self, name: str, comp_type: str, parts: List[str], line_num: int) -> Component:
        """Create a component based on its type"""
        component = Component(name=name, type=comp_type, nodes=[], line_number=line_num)
        
        if comp_type in ['R', 'C', 'L']:
            # Passive components: name node1 node2 value
            if len(parts) >= 3:
                component.nodes = parts[:2]
                component.value = parts[2]
                component.parameters = self._parse_parameters(' '.join(parts[3:]))
        
        elif comp_type in ['V', 'I']:
            # Sources: name node+ node- value [AC] [DC] [TRAN]
            if len(parts) >= 3:
                component.nodes = parts[:2]
                component.value = parts[2]
                component.parameters = self._parse_parameters(' '.join(parts[3:]))
        
        elif comp_type == 'D':
            # Diode: name anode cathode model
            if len(parts) >= 3:
                component.nodes = parts[:2]
                component.model = parts[2]
                component.parameters = self._parse_parameters(' '.join(parts[3:]))
        
        elif comp_type == 'Q':
            # BJT: name collector base emitter [substrate] model
            if len(parts) >= 4:
                component.nodes = parts[:3]
                idx = 3
                # Check if substrate is present
                if len(parts) > 4 and '=' not in parts[3]:
                    component.nodes.append(parts[3])
                    idx = 4
                component.model = parts[idx] if idx < len(parts) else None
                component.parameters = self._parse_parameters(' '.join(parts[idx+1:]))
        
        elif comp_type == 'M':
            # MOSFET: name drain gate source bulk model [L=] [W=]
            if len(parts) >= 5:
                component.nodes = parts[:4]
                component.model = parts[4]
                component.parameters = self._parse_parameters(' '.join(parts[5:]))
        
        elif comp_type == 'X':
            # Subcircuit instance: name node1 node2 ... subckt_name
            if len(parts) >= 2:
                # Last non-parameter item is subcircuit name
                param_start = len(parts)
                for i, part in enumerate(parts):
                    if '=' in part:
                        param_start = i
                        break
                component.nodes = parts[:param_start-1]
                component.model = parts[param_start-1]
                component.parameters = self._parse_parameters(' '.join(parts[param_start:]))
        
        else:
            # Generic component
            component.nodes = parts[:2] if len(parts) >= 2 else parts
            component.value = parts[2] if len(parts) > 2 else None
            component.parameters = self._parse_parameters(' '.join(parts[3:]))
        
        return component
    
    def _parse_parameters(self, param_str: str) -> Dict[str, str]:
        """Parse parameter strings like 'L=1u W=2u'"""
        params = {}
        if not param_str:
            return params
        
        # Match key=value pairs
        pattern = r'(\w+)\s*=\s*([^\s]+)'
        matches = re.findall(pattern, param_str)
        
        for key, value in matches:
            params[key.upper()] = value
        
        return params


# Example usage and testing
if __name__ == "__main__":
    # Example SPICE netlist
    example_netlist = """
* Example SPICE Netlist
* Simple RC Circuit
.title RC Low-Pass Filter

* Voltage source
Vin input 0 DC 5V AC 1V

* Components
R1 input output 1k
C1 output 0 10u

* Analysis
.ac dec 10 1 100k
.print ac v(output)
.end
"""
    
    # Parse the netlist
    parser = SpiceParser()
    netlist = parser.parse(example_netlist)
    
    # Export to JSON
    netlist.to_json("circuit.json")
    print("Exported to circuit.json")
    
    # Print parsed components
    print(f"\nTitle: {netlist.title}")
    print(f"\nComponents ({len(netlist.components)}):")
    for comp in netlist.components:
        print(f"  {comp.name}: {comp.type} {comp.nodes} = {comp.value}")
    
    # Load from JSON
    loaded_netlist = SpiceNetlist.from_json("circuit.json")
    print(f"\nLoaded from JSON: {len(loaded_netlist.components)} components")
    
    # Convert back to SPICE
    print("\nConverted back to SPICE:")
    print(loaded_netlist.to_spice())