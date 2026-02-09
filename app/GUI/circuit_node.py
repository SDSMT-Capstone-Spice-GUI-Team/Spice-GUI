from PyQt6.QtCore import QPointF

# Component definitions
COMPONENTS = {
    'Resistor': {'symbol': 'R', 'terminals': 2, 'color': '#2196F3'},
    'Capacitor': {'symbol': 'C', 'terminals': 2, 'color': '#4CAF50'},
    'Inductor': {'symbol': 'L', 'terminals': 2, 'color': '#FF9800'},
    'Voltage Source': {'symbol': 'V', 'terminals': 2, 'color': '#F44336'},
    'Current Source': {'symbol': 'I', 'terminals': 2, 'color': '#9C27B0'},
    'Ground': {'symbol': 'GND', 'terminals': 1, 'color': '#000000'},
}

class Node:
    """Represents an electrical node - a set of electrically connected terminals"""
    
    _node_counter = 0  # Class variable for generating node labels
    
    def __init__(self, is_ground=False, custom_label=None):
        self.terminals = set()  # Set of (component_id, terminal_index) tuples
        self.wires = set()  # Set of WireGraphicsItem objects
        self.is_ground = is_ground
        self.custom_label = custom_label
        
        if is_ground:
            self.auto_label = "0"
        elif custom_label:
            self.auto_label = custom_label
        else:
            # Generate auto label: nodeA, nodeB, nodeC...
            Node._node_counter += 1
            label_index = Node._node_counter - 1
            self.auto_label = self._generate_label(label_index)
    
    @staticmethod
    def _generate_label(index):
        """Generate label like nodeA, nodeB, ..., nodeZ, nodeAA, nodeAB..."""
        label = "node"
        if index < 26:
            label += chr(ord('A') + index)
        else:
            # For more than 26 nodes, use AA, AB, AC...
            first = (index // 26) - 1
            second = index % 26
            label += chr(ord('A') + first) + chr(ord('A') + second)
        return label
    
    def set_custom_label(self, label):
        """Set a custom label for this node"""
        self.custom_label = label
    
    def get_label(self):
        """Get the display label for this node"""
        if self.custom_label:
            if self.is_ground:
                return f"{self.custom_label} (ground)"
            return self.custom_label
        return self.auto_label
    
    def add_terminal(self, component_id, terminal_index):
        """Add a terminal to this node"""
        self.terminals.add((component_id, terminal_index))
    
    def remove_terminal(self, component_id, terminal_index):
        """Remove a terminal from this node"""
        self.terminals.discard((component_id, terminal_index))
    
    def add_wire(self, wire):
        """Add a wire to this node"""
        self.wires.add(wire)
    
    def remove_wire(self, wire):
        """Remove a wire from this node"""
        self.wires.discard(wire)
    
    def merge_with(self, other_node):
        """Merge another node into this one"""
        self.terminals.update(other_node.terminals)
        self.wires.update(other_node.wires)
        
        # Handle ground merging
        if other_node.is_ground:
            self.is_ground = True
            if self.custom_label:
                pass
            else:
                self.auto_label = "0"
    
    def set_as_ground(self):
        """Mark this node as ground (node 0)"""
        self.is_ground = True
        if not self.custom_label:
            self.auto_label = "0"
    
    def get_position(self, components):
        """Get a representative position for label placement (near a junction)"""
        if not self.terminals:
            return None
        
        # Find the average position of all terminals in this node
        positions = []
        for comp_id, term_idx in self.terminals:
            if comp_id in components:
                comp = components[comp_id]
                pos = comp.get_terminal_pos(term_idx)
                positions.append(pos)
        
        if not positions:
            return None
        
        # Return average position
        avg_x = sum(p.x() for p in positions) / len(positions)
        avg_y = sum(p.y() for p in positions) / len(positions)
        return QPointF(avg_x, avg_y)

    # Phase 5: Helper methods for observer pattern
    @staticmethod
    def from_node_data(node_data):
        """
        Create Qt Node from NodeData (Phase 5).

        Args:
            node_data: NodeData from models.node

        Returns:
            Node: Qt-based Node object
        """
        node = Node(is_ground=node_data.is_ground, custom_label=node_data.custom_label)
        for terminal in node_data.terminals:
            node.add_terminal(*terminal)
        node.auto_label = node_data.auto_label
        return node

    def matches_node_data(self, node_data) -> bool:
        """
        Check if this Node corresponds to NodeData (Phase 5).

        Args:
            node_data: NodeData from models.node

        Returns:
            bool: True if terminals match
        """
        return self.terminals == node_data.terminals
