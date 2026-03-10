# SDM Spice Class Diagram

## Main Architecture

```mermaid
classDiagram
    direction TB

    %% Main Window
    class CircuitDesignGUI {
        +canvas: CircuitCanvas
        +palette: ComponentPalette
        +properties_panel: PropertiesPanel
        +results_text: QTextEdit
        +analysis_type: str
        +analysis_params: dict
        -_ngspice_runner: NgspiceRunner
        +init_ui()
        +create_menu_bar()
        +save_circuit()
        +load_circuit()
        +generate_netlist()
        +run_simulation()
        +toggle_component_labels()
        +toggle_component_values()
        +toggle_node_labels()
    }
    CircuitDesignGUI --|> QMainWindow

    %% Canvas
    class CircuitCanvas {
        +scene: QGraphicsScene
        +components: dict
        +wires: list~WireItem~
        +nodes: list~Node~
        +terminal_to_node: dict
        +layer_manager: AlgorithmLayerManager
        +show_component_labels: bool
        +show_component_values: bool
        +show_node_labels: bool
        +node_voltages: dict
        +add_component_at_center()
        +delete_component()
        +rotate_selected()
        +update_nodes_for_wire()
        +rebuild_all_nodes()
        +draw_grid()
        +set_node_voltages()
        +to_dict()
        +from_dict()
        signal componentAdded(str)
        signal wireAdded(str, str)
        signal selectionChanged(object)
    }
    CircuitCanvas --|> QGraphicsView

    %% Relationships from main window
    CircuitDesignGUI *-- CircuitCanvas
    CircuitDesignGUI *-- ComponentPalette
    CircuitDesignGUI *-- PropertiesPanel
    CircuitDesignGUI ..> NgspiceRunner : lazy init
    CircuitDesignGUI ..> AnalysisDialog : creates
    CircuitDesignGUI ..> WaveformDialog : creates
```

## Component Hierarchy

```mermaid
classDiagram
    direction TB

    class ComponentItem {
        <<abstract>>
        +component_id: str
        +component_type: str
        +value: str
        +rotation_angle: float
        +terminals: list~QPointF~
        +connections: dict
        +paint()*
        +draw_component_body()*
        +update_terminals()
        +rotate_component()
        +get_terminal_pos()
        +get_obstacle_shape()
        +to_dict()
        +from_dict()
    }
    ComponentItem --|> QGraphicsItem

    class Resistor {
        +SYMBOL = "R"
        +TERMINALS = 2
        +draw_component_body()
    }
    Resistor --|> ComponentItem

    class Capacitor {
        +SYMBOL = "C"
        +TERMINALS = 2
        +draw_component_body()
    }
    Capacitor --|> ComponentItem

    class Inductor {
        +SYMBOL = "L"
        +TERMINALS = 2
        +draw_component_body()
    }
    Inductor --|> ComponentItem

    class VoltageSource {
        +SYMBOL = "V"
        +TERMINALS = 2
        +draw_component_body()
    }
    VoltageSource --|> ComponentItem

    class CurrentSource {
        +SYMBOL = "I"
        +TERMINALS = 2
        +draw_component_body()
    }
    CurrentSource --|> ComponentItem

    class WaveformVoltageSource {
        +SYMBOL = "VW"
        +waveform_type: str
        +waveform_params: dict
        +get_spice_value()
    }
    WaveformVoltageSource --|> VoltageSource

    class Ground {
        +SYMBOL = "GND"
        +TERMINALS = 1
        +paint()
    }
    Ground --|> ComponentItem

    class OpAmp {
        +SYMBOL = "OA"
        +TERMINALS = 5
        +draw_component_body()
    }
    OpAmp --|> ComponentItem
```

## Wire and Node System

```mermaid
classDiagram
    direction LR

    class WireItem {
        +start_comp: ComponentItem
        +start_term: int
        +end_comp: ComponentItem
        +end_term: int
        +node: Node
        +algorithm: str
        +layer_color: QColor
        +waypoints: list~QPointF~
        +runtime: float
        +iterations: int
        +update_position()
        +paint()
        +shape()
        +get_terminals()
        +to_dict()
    }
    WireItem --|> QGraphicsPathItem

    class Node {
        +terminals: set
        +wires: set~WireItem~
        +is_ground: bool
        +custom_label: str
        +auto_label: str
        -_node_counter: int
        +add_terminal()
        +remove_terminal()
        +add_wire()
        +merge_with()
        +set_as_ground()
        +get_label()
        +get_position()
    }

    WireItem "*" --> "1" Node : belongs to
    WireItem --> ComponentItem : connects
    Node o-- WireItem : contains
```

## Simulation Classes

```mermaid
classDiagram
    direction TB

    class NetlistGenerator {
        +components: dict
        +wires: list
        +nodes: list
        +terminal_to_node: dict
        +analysis_type: str
        +analysis_params: dict
        +generate() str
        -_generate_analysis_commands()
    }

    class NgspiceRunner {
        +output_dir: str
        +ngspice_cmd: str
        +find_ngspice()
        +run_simulation()
        +read_output()
    }

    class ResultParser {
        +parse_op_results()$
        +parse_dc_results()$
        +parse_ac_results()$
        +parse_transient_results()$
        +format_results_as_table()$
    }

    CircuitDesignGUI ..> NetlistGenerator : creates
    CircuitDesignGUI o-- NgspiceRunner : owns
    CircuitDesignGUI ..> ResultParser : uses
```

## Theme System

```mermaid
classDiagram
    direction TB

    class ThemeManager {
        <<singleton>>
        -_instance: ThemeManager
        -_theme: ThemeProtocol
        -_listeners: list
        +set_theme()
        +current_theme()
        +color(key)
        +pen(key)
        +brush(key)
        +font(key)
        +stylesheet(key)
        +get_component_color()
        +get_algorithm_color()
    }

    class ThemeProtocol {
        <<protocol>>
        +color(key)*
        +pen(key)*
        +brush(key)*
        +font(key)*
        +stylesheet(key)*
    }

    class LightTheme {
        +color(key)
        +pen(key)
        +brush(key)
        +font(key)
        +stylesheet(key)
    }

    ThemeManager --> ThemeProtocol : uses
    LightTheme ..|> ThemeProtocol : implements
```

## Algorithm Layer System

```mermaid
classDiagram
    direction TB

    class AlgorithmLayerManager {
        +layers: dict~str, AlgorithmLayer~
        +active_algorithms: list
        +get_layer()
        +set_active_algorithms()
        +add_wire_to_layer()
        +clear_all_wires()
        +get_performance_report()
    }

    class AlgorithmLayer {
        +name: str
        +algorithm_type: str
        +color: QColor
        +z_value: int
        +visible: bool
        +wires: list~WireItem~
        +total_runtime: float
        +total_iterations: int
        +add_wire()
        +remove_wire()
        +update_visibility()
        +get_performance_summary()
    }

    AlgorithmLayerManager "1" *-- "*" AlgorithmLayer
    AlgorithmLayer o-- WireItem
    CircuitCanvas *-- AlgorithmLayerManager
```

## UI Widgets

```mermaid
classDiagram
    direction TB

    class ComponentPalette {
        +componentDoubleClicked: Signal
        +startDrag()
        -_on_item_double_clicked()
    }
    ComponentPalette --|> QListWidget

    class PropertiesPanel {
        +current_component: ComponentItem
        +value_input: QLineEdit
        +property_changed: Signal
        +show_component()
        +show_no_selection()
        +apply_changes()
        +configure_waveform()
    }
    PropertiesPanel --|> QWidget

    class AnalysisDialog {
        +ANALYSIS_CONFIGS: dict
        +analysis_type: str
        +field_widgets: dict
        +get_parameters()
        +get_ngspice_command()
    }
    AnalysisDialog --|> QDialog

    class WaveformDialog {
        +full_data: dict
        +view_data: dict
        +canvas: MplCanvas
        +table: QTableWidget
        +plot_data()
        +apply_filters()
        +apply_highlight()
    }
    WaveformDialog --|> QDialog

    class MplCanvas {
        +fig: Figure
        +axes: Axes
    }
    MplCanvas --|> FigureCanvas
    WaveformDialog *-- MplCanvas
```

## Signal Flow

```mermaid
flowchart LR
    subgraph Palette
        CP[ComponentPalette]
    end

    subgraph Canvas
        CC[CircuitCanvas]
    end

    subgraph Properties
        PP[PropertiesPanel]
    end

    subgraph Main
        GUI[CircuitDesignGUI]
    end

    CP -->|componentDoubleClicked| CC
    CC -->|selectionChanged| PP
    CC -->|componentRightClicked| GUI
    CC -->|canvasClicked| GUI
    PP -->|property_changed| GUI
```

## Data Flow

```mermaid
flowchart TB
    subgraph Circuit Design
        Canvas[CircuitCanvas]
        Components[ComponentItem instances]
        Wires[WireItem instances]
        Nodes[Node instances]
    end

    subgraph Serialization
        ToDict[to_dict]
        FromDict[from_dict]
        JSON[JSON File]
    end

    subgraph Simulation
        NetGen[NetlistGenerator]
        Netlist[SPICE Netlist]
        NgSpice[NgspiceRunner]
        Parser[ResultParser]
        Results[Simulation Results]
    end

    Canvas --> ToDict
    ToDict --> JSON
    JSON --> FromDict
    FromDict --> Canvas

    Canvas --> NetGen
    Components --> NetGen
    Wires --> NetGen
    Nodes --> NetGen
    NetGen --> Netlist
    Netlist --> NgSpice
    NgSpice --> Parser
    Parser --> Results
    Results --> Canvas
```
