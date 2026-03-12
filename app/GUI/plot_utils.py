"""
GUI/plot_utils.py — Shared matplotlib utilities for plot dialogs.

Centralises matplotlib backend configuration and theme application
so individual dialog modules don't duplicate this logic.
"""

import matplotlib

from .styles import theme_manager

# Configure matplotlib backend once at import time.
# Guard against repeated calls (harmless but noisy).
matplotlib.use("QtAgg")


def apply_mpl_theme(fig):
    """Apply the current application theme colors to a matplotlib figure.

    On dark themes, sets figure and axes background colours, tick/label
    foreground, and spine borders to match the app palette.  On light
    themes this is a no-op — matplotlib defaults work fine.
    """
    theme = theme_manager.current_theme
    if theme.is_dark:
        bg = theme.color_hex("background_primary")
        fg = theme.color_hex("text_primary")
        bg2 = theme.color_hex("background_secondary")
        from PyQt6.QtGui import QColor

        border = QColor(bg2).lighter(150).name()
        fig.patch.set_facecolor(bg)
        for ax in fig.axes:
            ax.set_facecolor(bg2)
            ax.tick_params(colors=fg)
            ax.xaxis.label.set_color(fg)
            ax.yaxis.label.set_color(fg)
            ax.title.set_color(fg)
            for spine in ax.spines.values():
                spine.set_edgecolor(border)


def build_analysis_base_form(form_layout, field_widgets_dict, analysis_combo):
    """Populate *form_layout* with fields for the currently-selected analysis type.

    Shared between the Monte Carlo and Parameter Sweep configuration dialogs.

    Args:
        form_layout: QFormLayout to populate (cleared first).
        field_widgets_dict: dict that will be updated with ``{key: (widget, field_type)}``
            entries.  Cleared before populating.
        analysis_combo: QComboBox whose ``currentText()`` selects the analysis config.
    """
    from PyQt6.QtWidgets import QComboBox, QLineEdit

    # Clear existing widgets
    while form_layout.count():
        item = form_layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
    field_widgets_dict.clear()

    from .analysis_dialog import AnalysisDialog

    analysis_type = analysis_combo.currentText()
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

        field_widgets_dict[key] = (widget, field_config[2])
        form_layout.addRow(f"{label}:", widget)
