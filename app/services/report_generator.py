"""Report data assembly for circuit reports.

Provides ReportConfig (what to include), ReportData (assembled content),
and ReportDataBuilder (model-to-text logic).  Pure Python — no Qt or GUI
dependencies.  The actual PDF rendering lives in GUI.report_renderer.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ReportConfig:
    """Configuration for which sections to include in a circuit report."""

    include_title: bool = True
    include_schematic: bool = True
    include_netlist: bool = True
    include_analysis: bool = True
    include_results: bool = True
    student_name: str = ""
    circuit_name: str = ""


@dataclass
class ReportData:
    """Assembled report content ready for rendering.

    All fields are plain strings / ints so that any renderer (Qt, PIL,
    ReportLab, …) can consume them without importing model classes.
    """

    config: ReportConfig = field(default_factory=ReportConfig)
    title: str = ""
    subtitle: str = "Circuit Analysis Report"
    analysis_type: str = ""
    component_count: int = 0
    date_str: str = ""
    analysis_text: str = ""
    netlist: str = ""
    results_text: str = ""


class ReportDataBuilder:
    """Assembles plain-text report content from model objects.

    This is the services-layer piece: it reads model data and produces
    a ReportData bundle that any renderer can consume.
    """

    @staticmethod
    def build(
        config: ReportConfig,
        model=None,
        netlist: str = "",
        results_text: str = "",
    ) -> ReportData:
        """Build a ReportData from a config, optional model, and text blobs."""
        data = ReportData(config=config)
        data.title = config.circuit_name or "Circuit Report"
        data.date_str = datetime.now().strftime("%B %d, %Y")

        if model is not None:
            data.analysis_type = getattr(model, "analysis_type", "") or ""
            data.component_count = len(getattr(model, "components", {}) or {})
            data.analysis_text = ReportDataBuilder._format_analysis_config(model)

        data.netlist = netlist
        data.results_text = results_text
        return data

    @staticmethod
    def _format_analysis_config(model) -> str:
        """Format analysis type and parameters as readable text."""
        lines = []
        lines.append(f"Analysis Type: {model.analysis_type}")
        lines.append("")

        if model.analysis_params:
            lines.append("Parameters:")
            for key, value in model.analysis_params.items():
                display_key = key.replace("_", " ").title()
                lines.append(f"  {display_key}: {value}")
        else:
            lines.append("Parameters: (default)")

        lines.append("")
        lines.append(f"Total Components: {len(model.components)}")
        lines.append(f"Total Wires: {len(model.wires)}")

        if model.components:
            lines.append("")
            lines.append("Component Summary:")
            type_counts: dict[str, int] = {}
            for comp in model.components.values():
                ctype = comp.component_type
                type_counts[ctype] = type_counts.get(ctype, 0) + 1
            for ctype, count in sorted(type_counts.items()):
                lines.append(f"  {ctype}: {count}")

        return "\n".join(lines)
