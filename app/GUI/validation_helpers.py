"""Shared validation helpers for dialog input fields.

Provides functions to highlight invalid fields with a red border and
display an error label, plus a function to clear the error state.
"""

# AUDIT(testing): no unit tests for validation helper functions; add tests covering set_field_error, clear_field_error, clear_all_field_errors, show_validation_error

from PyQt6.QtWidgets import QLabel, QLineEdit, QWidget

# Stylesheet applied to fields with validation errors
_ERROR_STYLE = "border: 1.5px solid red; border-radius: 3px;"
_NORMAL_STYLE = ""

# Object name used to locate dynamically-created error labels
_ERROR_LABEL_NAME = "_validation_error_label"


def set_field_error(widget: QLineEdit, message: str) -> None:
    """Highlight *widget* with a red border and show *message* below it.

    If an error label already exists for this widget it is updated rather
    than duplicated.
    """
    widget.setStyleSheet(_ERROR_STYLE)

    parent: QWidget | None = widget.parentWidget()
    if parent is None:
        return

    # Look for an existing error label attached to this widget
    label = widget.property(_ERROR_LABEL_NAME)
    if isinstance(label, QLabel) and label.parent() == parent:
        label.setText(message)
        label.show()
        return

    # Create a new error label and insert it right after the widget
    label = QLabel(message, parent)
    label.setStyleSheet("color: red; font-size: 9pt; margin: 0; padding: 0;")
    label.setWordWrap(True)
    label.setObjectName(_ERROR_LABEL_NAME)
    widget.setProperty(_ERROR_LABEL_NAME, label)

    # Try to insert into the parent's layout after the widget
    layout = parent.layout()
    if layout is not None:
        from PyQt6.QtWidgets import QFormLayout

        if isinstance(layout, QFormLayout):
            # In a form layout, add the label as a spanning row after the widget's row
            for row in range(layout.rowCount()):
                item = layout.itemAt(row, QFormLayout.ItemRole.FieldRole)
                if item and item.widget() is widget:
                    layout.insertRow(row + 1, "", label)
                    return
        # Fallback: just add the label to the layout
        layout.addWidget(label)


def clear_field_error(widget: QLineEdit) -> None:
    """Remove the red border and error label from *widget*."""
    widget.setStyleSheet(_NORMAL_STYLE)
    label = widget.property(_ERROR_LABEL_NAME)
    if isinstance(label, QLabel):
        label.hide()
        label.setText("")


def clear_all_field_errors(*widgets: QLineEdit) -> None:
    """Remove error state from multiple widgets."""
    for w in widgets:
        clear_field_error(w)


def show_validation_error(parent: QWidget, message: str) -> None:
    """Show a QMessageBox with a validation error message."""
    from PyQt6.QtWidgets import QMessageBox

    QMessageBox.warning(parent, "Validation Error", message)
