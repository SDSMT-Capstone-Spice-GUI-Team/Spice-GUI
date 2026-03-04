"""Shared helpers for building and parsing analysis parameter form fields.

Both the Monte Carlo dialog, Parameter Sweep dialog, and Analysis dialog
share the same pattern for building form fields from ``ANALYSIS_CONFIGS``
and parsing/validating the resulting widget values.  This module
consolidates that logic so it lives in exactly one place.

No simulation dependencies — only PyQt6 and format_utils.
"""

from PyQt6.QtWidgets import QComboBox, QFormLayout, QLineEdit

from .format_utils import parse_value


def build_analysis_fields(
    form_layout: QFormLayout,
    analysis_type: str,
    field_widgets: dict,
) -> None:
    """Populate *form_layout* with widgets for *analysis_type*.

    Clears the existing layout first, then creates one widget per field
    defined in ``AnalysisDialog.ANALYSIS_CONFIGS[analysis_type]``.

    Args:
        form_layout: The QFormLayout to populate.
        analysis_type: Key into ``AnalysisDialog.ANALYSIS_CONFIGS``.
        field_widgets: Mutable dict that will be **cleared** and filled
            with ``{key: (widget, field_type)}`` entries.
    """
    # Clear existing widgets
    while form_layout.count():
        item = form_layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
    field_widgets.clear()

    from .analysis_dialog import AnalysisDialog

    config = AnalysisDialog.ANALYSIS_CONFIGS.get(analysis_type, {})

    tooltips = config.get("tooltips", {})
    for field_config in config.get("fields", []):
        if field_config[2] == "combo":
            label, key, _, options, default = field_config
            widget = QComboBox()
            widget.addItems(options)
            widget.setCurrentText(default)
        else:
            label, key, field_type, default = field_config
            widget = QLineEdit(str(default))

        tooltip = tooltips.get(key)
        if tooltip:
            widget.setToolTip(tooltip)

        field_widgets[key] = (widget, field_config[2])
        form_layout.addRow(f"{label}:", widget)


def parse_field_widgets(field_widgets: dict) -> dict:
    """Read values from *field_widgets* and return a parsed params dict.

    Args:
        field_widgets: ``{key: (QWidget, field_type)}`` where
            *field_type* is ``"combo"``, ``"float"``, ``"int"``, or
            ``"text"``.

    Returns:
        Dict of ``{key: parsed_value}``.

    Raises:
        ValueError, TypeError: If a numeric field contains an
            unparseable value.
    """
    params: dict = {}
    for key, (widget, field_type) in field_widgets.items():
        if field_type == "combo":
            params[key] = widget.currentText()
        elif field_type == "float":
            params[key] = parse_value(widget.text())
        elif field_type == "int":
            params[key] = int(parse_value(widget.text()))
        else:
            params[key] = widget.text()
    return params
