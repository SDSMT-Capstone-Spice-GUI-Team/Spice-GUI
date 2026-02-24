"""
Unit tests for the in-app help system (#241).

Tests HelpDialog topics, search filtering, HelpMixin integration,
and the guided tutorial step list.
"""

import pytest
from PyQt6.QtCore import Qt


@pytest.fixture
def help_dialog(qtbot):
    from GUI.main_window_help import HelpDialog

    d = HelpDialog()
    qtbot.addWidget(d)
    return d


class TestHelpDialogCreation:
    """Test that the help dialog initializes correctly."""

    def test_dialog_opens(self, help_dialog):
        assert help_dialog is not None

    def test_has_search_input(self, help_dialog):
        assert help_dialog._search is not None
        assert "search" in help_dialog._search.placeholderText().lower()

    def test_has_topic_list(self, help_dialog):
        assert help_dialog._topic_list is not None

    def test_has_content_browser(self, help_dialog):
        assert help_dialog._content is not None

    def test_topics_populated(self, help_dialog):
        from GUI.main_window_help import HELP_TOPICS

        assert help_dialog.topic_count() == len(HELP_TOPICS)

    def test_first_topic_selected(self, help_dialog):
        current = help_dialog._topic_list.currentItem()
        assert current is not None
        assert current.text() == "Getting Started"

    def test_content_shows_first_topic(self, help_dialog):
        html = help_dialog._content.toHtml()
        assert "Getting Started" in html


class TestHelpDialogSearch:
    """Test search/filter functionality in the help dialog."""

    def test_search_filters_topics(self, help_dialog):
        help_dialog._search.setText("wire")
        visible = help_dialog.visible_topic_count()
        assert visible >= 1  # At least "Drawing Wires"
        assert visible < help_dialog.topic_count()

    def test_search_case_insensitive(self, help_dialog):
        help_dialog._search.setText("SIMULATION")
        visible = help_dialog.visible_topic_count()
        assert visible >= 1

    def test_empty_search_shows_all(self, help_dialog):
        help_dialog._search.setText("wire")
        help_dialog._search.setText("")
        assert help_dialog.visible_topic_count() == help_dialog.topic_count()

    def test_no_match_hides_all(self, help_dialog):
        help_dialog._search.setText("xyznonexistent")
        assert help_dialog.visible_topic_count() == 0

    def test_search_matches_keywords(self, help_dialog):
        help_dialog._search.setText("shortcut")
        # "Keyboard Shortcuts" topic has "shortcut" as a keyword
        visible_titles = []
        for i in range(help_dialog._topic_list.count()):
            item = help_dialog._topic_list.item(i)
            if not item.isHidden():
                visible_titles.append(item.text())
        assert "Keyboard Shortcuts" in visible_titles


class TestHelpTopicContent:
    """Test that help topics contain expected content."""

    def test_getting_started_has_steps(self, help_dialog):
        # Select "Getting Started"
        help_dialog._topic_list.setCurrentRow(0)
        html = help_dialog._content.toHtml()
        assert "Add components" in html

    def test_keyboard_shortcuts_has_table(self, help_dialog):
        # Find and select "Keyboard Shortcuts"
        for i in range(help_dialog._topic_list.count()):
            item = help_dialog._topic_list.item(i)
            if item.text() == "Keyboard Shortcuts":
                help_dialog._topic_list.setCurrentRow(i)
                break
        html = help_dialog._content.toHtml()
        assert "Ctrl+S" in html


class TestGuidedTutorial:
    """Test the tutorial steps structure."""

    def test_tutorial_steps_not_empty(self):
        from GUI.main_window_help import TUTORIAL_STEPS

        assert len(TUTORIAL_STEPS) > 0

    def test_each_step_has_title_and_message(self):
        from GUI.main_window_help import TUTORIAL_STEPS

        for step in TUTORIAL_STEPS:
            assert "title" in step
            assert "message" in step
            assert len(step["title"]) > 0
            assert len(step["message"]) > 0

    def test_tutorial_starts_with_add_component(self):
        from GUI.main_window_help import TUTORIAL_STEPS

        assert "Add" in TUTORIAL_STEPS[0]["title"] or "Component" in TUTORIAL_STEPS[0]["message"]


class TestHelpMixin:
    """Test HelpMixin integration with MainWindow."""

    def test_mixin_importable(self):
        from GUI.main_window_help import HelpMixin

        assert HelpMixin is not None

    def test_mixin_has_show_help(self):
        from GUI.main_window_help import HelpMixin

        assert hasattr(HelpMixin, "_show_help")

    def test_mixin_has_start_tutorial(self):
        from GUI.main_window_help import HelpMixin

        assert hasattr(HelpMixin, "_start_tutorial")


class TestMainWindowHelpIntegration:
    """Test that MainWindow includes the HelpMixin."""

    def test_mainwindow_inherits_help_mixin(self):
        from GUI.main_window import MainWindow
        from GUI.main_window_help import HelpMixin

        assert issubclass(MainWindow, HelpMixin)

    def test_mainwindow_has_show_help(self):
        from GUI.main_window import MainWindow

        assert hasattr(MainWindow, "_show_help")

    def test_mainwindow_has_start_tutorial(self):
        from GUI.main_window import MainWindow

        assert hasattr(MainWindow, "_start_tutorial")
