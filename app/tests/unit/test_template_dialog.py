"""Tests for NewFromTemplateDialog after MVC refactor (#602).

The dialog now receives a pre-fetched list of TemplateInfo objects and an
optional delete callback, instead of directly holding a TemplateManager
reference.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from controllers.template_manager import TemplateInfo


def _make_templates():
    """Return a small list of TemplateInfo objects for testing."""
    return [
        TemplateInfo(
            name="Voltage Divider",
            description="Basic voltage divider",
            category="Passives",
            filepath=Path("/builtin/voltage_divider.json"),
            is_builtin=True,
        ),
        TemplateInfo(
            name="RC Filter",
            description="Simple RC low-pass filter",
            category="Passives",
            filepath=Path("/builtin/rc_filter.json"),
            is_builtin=True,
        ),
        TemplateInfo(
            name="My Custom",
            description="User-created template",
            category="User",
            filepath=Path("/user/my_custom.json"),
            is_builtin=False,
        ),
    ]


@pytest.fixture
def templates():
    return _make_templates()


@pytest.fixture
def dialog(qtbot, templates):
    from GUI.template_dialog import NewFromTemplateDialog

    dlg = NewFromTemplateDialog(templates)
    qtbot.addWidget(dlg)
    return dlg


class TestNewFromTemplateDialogConstruction:
    """Dialog construction and template population."""

    def test_no_template_manager_attribute(self, dialog):
        """Dialog must not store a TemplateManager reference."""
        assert not hasattr(dialog, "template_manager")

    def test_stores_template_list(self, dialog, templates):
        """Dialog stores a copy of the template list."""
        assert dialog._templates == templates
        # Must be a copy, not the same object
        assert dialog._templates is not templates

    def test_populates_list_widget(self, dialog):
        """Template list widget has items for each template plus headers."""
        # 2 category headers (Passives, User) + 3 template items = 5
        assert dialog.template_list.count() == 5

    def test_ok_button_disabled_initially(self, dialog):
        """OK button is disabled until a template is selected."""
        assert not dialog.ok_button.isEnabled()

    def test_delete_button_disabled_initially(self, dialog):
        """Delete button is disabled until a user template is selected."""
        assert not dialog.delete_btn.isEnabled()

    def test_empty_template_list(self, qtbot):
        """Dialog handles an empty template list gracefully."""
        from GUI.template_dialog import NewFromTemplateDialog

        dlg = NewFromTemplateDialog([])
        qtbot.addWidget(dlg)
        assert dlg.template_list.count() == 0


class TestNewFromTemplateDialogSelection:
    """Template selection behaviour."""

    def test_select_builtin_template(self, dialog):
        """Selecting a built-in template enables OK but not delete."""
        # Item at index 1 is the first template (index 0 is the category header)
        dialog.template_list.setCurrentRow(1)
        assert dialog.ok_button.isEnabled()
        assert not dialog.delete_btn.isEnabled()

    def test_select_user_template(self, dialog):
        """Selecting a user template enables both OK and delete."""
        # Category headers at 0, 3; user template at index 4
        dialog.template_list.setCurrentRow(4)
        assert dialog.ok_button.isEnabled()
        assert dialog.delete_btn.isEnabled()

    def test_get_selected_template(self, dialog, templates):
        """get_selected_template returns the correct TemplateInfo."""
        dialog.template_list.setCurrentRow(1)
        selected = dialog.get_selected_template()
        assert selected is not None
        assert selected.name == "Voltage Divider"


class TestNewFromTemplateDialogDelete:
    """Delete callback integration."""

    def test_delete_callback_called(self, qtbot, templates, monkeypatch):
        """Clicking delete invokes the callback with the correct filepath."""
        from GUI.template_dialog import NewFromTemplateDialog

        callback = MagicMock(return_value=True)
        dlg = NewFromTemplateDialog(templates, delete_callback=callback)
        qtbot.addWidget(dlg)

        # Select the user template (index 4)
        dlg.template_list.setCurrentRow(4)

        # Monkeypatch QMessageBox to auto-confirm
        monkeypatch.setattr(
            "GUI.template_dialog.QMessageBox.question",
            lambda *a, **kw: QMessageBox.StandardButton.Yes,
        )
        from PyQt6.QtWidgets import QMessageBox

        monkeypatch.setattr(
            "GUI.template_dialog.QMessageBox.question",
            lambda *a, **kw: QMessageBox.StandardButton.Yes,
        )

        dlg._on_delete()
        callback.assert_called_once_with(Path("/user/my_custom.json"))

    def test_delete_removes_from_list(self, qtbot, templates, monkeypatch):
        """Successful delete removes the template from the list widget."""
        from GUI.template_dialog import NewFromTemplateDialog
        from PyQt6.QtWidgets import QMessageBox

        callback = MagicMock(return_value=True)
        dlg = NewFromTemplateDialog(templates, delete_callback=callback)
        qtbot.addWidget(dlg)

        dlg.template_list.setCurrentRow(4)
        monkeypatch.setattr(
            "GUI.template_dialog.QMessageBox.question",
            lambda *a, **kw: QMessageBox.StandardButton.Yes,
        )

        count_before = dlg.template_list.count()
        dlg._on_delete()
        # Removed the template and its category header (User was the only one)
        assert dlg.template_list.count() < count_before

    def test_delete_callback_returning_false_keeps_list(self, qtbot, templates, monkeypatch):
        """If the callback returns False, the list is unchanged."""
        from GUI.template_dialog import NewFromTemplateDialog
        from PyQt6.QtWidgets import QMessageBox

        callback = MagicMock(return_value=False)
        dlg = NewFromTemplateDialog(templates, delete_callback=callback)
        qtbot.addWidget(dlg)

        dlg.template_list.setCurrentRow(4)
        monkeypatch.setattr(
            "GUI.template_dialog.QMessageBox.question",
            lambda *a, **kw: QMessageBox.StandardButton.Yes,
        )

        count_before = dlg.template_list.count()
        dlg._on_delete()
        assert dlg.template_list.count() == count_before

    def test_no_callback_skips_delete(self, qtbot, templates):
        """Without a delete callback, _on_delete is a no-op."""
        from GUI.template_dialog import NewFromTemplateDialog

        dlg = NewFromTemplateDialog(templates, delete_callback=None)
        qtbot.addWidget(dlg)

        dlg.template_list.setCurrentRow(4)
        count_before = dlg.template_list.count()
        dlg._on_delete()
        assert dlg.template_list.count() == count_before

    def test_cannot_delete_builtin(self, qtbot, templates):
        """_on_delete is a no-op for built-in templates."""
        from GUI.template_dialog import NewFromTemplateDialog

        callback = MagicMock(return_value=True)
        dlg = NewFromTemplateDialog(templates, delete_callback=callback)
        qtbot.addWidget(dlg)

        # Select built-in template
        dlg.template_list.setCurrentRow(1)
        dlg._on_delete()
        callback.assert_not_called()
