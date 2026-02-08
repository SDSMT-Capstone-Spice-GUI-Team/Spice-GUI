"""
algorithm_layers.py

Layer management system for multi-algorithm wire routing visualization.
Each algorithm gets its own layer with distinct visual appearance.
"""
from .styles import theme_manager


class AlgorithmLayer:
    """Represents a single algorithm layer with its visual properties"""

    def __init__(self, name, algorithm_type, color, z_value=0, visible=True):
        """
        Initialize an algorithm layer

        Args:
            name: Display name for the layer (e.g., "A*", "IDA*", "Dijkstra")
            algorithm_type: Internal algorithm identifier ('astar', 'idastar', 'dijkstra')
            color: QColor for wires in this layer
            z_value: Z-order for rendering (higher = on top)
            visible: Whether the layer is initially visible
        """
        self.name = name
        self.algorithm_type = algorithm_type
        self.color = color
        self.z_value = z_value
        self.visible = visible
        self.wires = []  # List of WireItem objects in this layer

        # Performance metrics for this layer
        self.total_runtime = 0.0
        self.total_iterations = 0
        self.wire_count = 0
        self.avg_runtime = 0.0
        self.avg_iterations = 0.0

    def add_wire(self, wire):
        """Add a wire to this layer"""
        if wire not in self.wires:
            self.wires.append(wire)
            self.wire_count = len(self.wires)

    def remove_wire(self, wire):
        """Remove a wire from this layer"""
        if wire in self.wires:
            self.wires.remove(wire)
            self.wire_count = len(self.wires)

    def clear_wires(self):
        """Remove all wires from this layer"""
        self.wires.clear()
        self.wire_count = 0
        self._reset_metrics()

    def update_visibility(self, visible):
        """Update layer visibility and apply to all wires"""
        self.visible = visible
        for wire in self.wires:
            wire.setVisible(visible)

    def add_performance_data(self, runtime, iterations):
        """Add performance data from a routing operation"""
        self.total_runtime += runtime
        self.total_iterations += iterations
        if self.wire_count > 0:
            self.avg_runtime = self.total_runtime / self.wire_count
            self.avg_iterations = self.total_iterations / self.wire_count

    def _reset_metrics(self):
        """Reset performance metrics"""
        self.total_runtime = 0.0
        self.total_iterations = 0
        self.avg_runtime = 0.0
        self.avg_iterations = 0.0

    def get_performance_summary(self):
        """Get a formatted performance summary string"""
        if self.wire_count == 0:
            return f"{self.name}: No wires"

        return (f"{self.name}: {self.wire_count} wires, "
                f"Avg Runtime: {self.avg_runtime*1000:.2f}ms, "
                f"Avg Iterations: {self.avg_iterations:.0f}")


class AlgorithmLayerManager:
    """Manages multiple algorithm layers for wire routing comparison"""

    def __init__(self):
        """Initialize the layer manager with default algorithm layers"""
        self.layers = {}
        self.active_algorithms = []  # List of algorithms to run when routing

        # Define default layers with distinct colors
        self._create_default_layers()

    def _create_default_layers(self):
        """Create the default algorithm layers"""
        # A* - Primary algorithm (Blue)
        self.layers['astar'] = AlgorithmLayer(
            name="A*",
            algorithm_type='astar',
            color=theme_manager.get_algorithm_color('astar'),
            z_value=10,
            visible=True
        )

        # IDA* - Memory-efficient variant (Green)
        self.layers['idastar'] = AlgorithmLayer(
            name="IDA*",
            algorithm_type='idastar',
            color=theme_manager.get_algorithm_color('idastar'),
            z_value=9,
            visible=True
        )

        # Dijkstra - Guaranteed shortest path (Orange)
        self.layers['dijkstra'] = AlgorithmLayer(
            name="Dijkstra",
            algorithm_type='dijkstra',
            color=theme_manager.get_algorithm_color('dijkstra'),
            z_value=8,
            visible=True
        )

        # Set all algorithms as active by default
        self.active_algorithms = ['astar', 'idastar', 'dijkstra']

    def get_layer(self, algorithm_type):
        """Get a layer by algorithm type"""
        return self.layers.get(algorithm_type)

    def get_all_layers(self):
        """Get all layers as a list, sorted by name"""
        return sorted(self.layers.values(), key=lambda x: x.name)

    def set_layer_visibility(self, algorithm_type, visible):
        """Set visibility for a specific layer"""
        layer = self.layers.get(algorithm_type)
        if layer:
            layer.update_visibility(visible)

    def toggle_layer_visibility(self, algorithm_type):
        """Toggle visibility for a specific layer"""
        layer = self.layers.get(algorithm_type)
        if layer:
            layer.update_visibility(not layer.visible)
            return layer.visible
        return False

    def set_active_algorithms(self, algorithm_types):
        """
        Set which algorithms should be run during routing

        Args:
            algorithm_types: list of algorithm type strings (e.g., ['astar', 'dijkstra'])
        """
        self.active_algorithms = [alg for alg in algorithm_types if alg in self.layers]

    def clear_all_wires(self):
        """Clear all wires from all layers"""
        for layer in self.layers.values():
            layer.clear_wires()

    def get_performance_report(self):
        """
        Generate a comprehensive performance comparison report

        Returns:
            str: Formatted performance report
        """
        report_lines = ["=== Algorithm Performance Comparison ===\n"]

        for layer in self.get_all_layers():
            report_lines.append(layer.get_performance_summary())

        # Add comparison if multiple algorithms have data
        layers_with_data = [l for l in self.layers.values() if l.wire_count > 0]
        if len(layers_with_data) > 1:
            report_lines.append("\n=== Comparison ===")

            # Find fastest average runtime
            fastest = min(layers_with_data, key=lambda x: x.avg_runtime)
            report_lines.append(f"Fastest Avg Runtime: {fastest.name} ({fastest.avg_runtime*1000:.2f}ms)")

            # Find fewest average iterations
            least_iterations = min(layers_with_data, key=lambda x: x.avg_iterations)
            report_lines.append(f"Fewest Avg Iterations: {least_iterations.name} ({least_iterations.avg_iterations:.0f})")

        return "\n".join(report_lines)

    def add_wire_to_layer(self, wire, algorithm_type, runtime, iterations):
        """
        Add a wire to the appropriate layer and update metrics

        Args:
            wire: WireItem to add
            algorithm_type: Algorithm that generated this wire
            runtime: Time taken to generate path (seconds)
            iterations: Number of iterations used
        """
        layer = self.layers.get(algorithm_type)
        if layer:
            layer.add_wire(wire)
            layer.add_performance_data(runtime, iterations)
            # Apply layer properties to wire
            wire.setZValue(layer.z_value)
            wire.setVisible(layer.visible)

    def remove_wire_from_layer(self, wire, algorithm_type):
        """Remove a wire from a specific layer"""
        layer = self.layers.get(algorithm_type)
        if layer:
            layer.remove_wire(wire)
