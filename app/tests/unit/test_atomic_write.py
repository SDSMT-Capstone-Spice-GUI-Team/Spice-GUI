"""Tests for the atomic write utility (#765)."""

import os

from utils.atomic_write import atomic_write_text


class TestAtomicWriteText:
    """Verify atomic_write_text writes files safely."""

    def test_writes_content(self, tmp_path):
        target = tmp_path / "test.json"
        atomic_write_text(target, '{"key": "value"}')
        assert target.read_text() == '{"key": "value"}'

    def test_overwrites_existing(self, tmp_path):
        target = tmp_path / "test.txt"
        target.write_text("old")
        atomic_write_text(target, "new")
        assert target.read_text() == "new"

    def test_no_temp_files_left(self, tmp_path):
        target = tmp_path / "test.txt"
        atomic_write_text(target, "content")
        files = list(tmp_path.iterdir())
        assert files == [target], f"Unexpected files: {files}"

    def test_creates_parent_directories(self, tmp_path):
        target = tmp_path / "sub" / "dir" / "test.txt"
        atomic_write_text(target, "deep")
        assert target.read_text() == "deep"

    def test_original_preserved_on_failure(self, tmp_path):
        """If the write fails, the original file should be untouched."""
        target = tmp_path / "test.txt"
        target.write_text("original")

        class FakeError(Exception):
            pass

        try:
            # Make a read-only subdirectory to force a failure
            # Instead, use a custom approach - mock os.replace to fail
            import unittest.mock

            with unittest.mock.patch("utils.atomic_write.os.replace", side_effect=FakeError("boom")):
                atomic_write_text(target, "corrupted")
        except FakeError:
            pass

        assert target.read_text() == "original"

    def test_no_temp_file_after_failure(self, tmp_path):
        """Temp file should be cleaned up after a failure."""
        target = tmp_path / "test.txt"

        class FakeError(Exception):
            pass

        try:
            import unittest.mock

            with unittest.mock.patch("utils.atomic_write.os.replace", side_effect=FakeError("boom")):
                atomic_write_text(target, "content")
        except FakeError:
            pass

        files = list(tmp_path.iterdir())
        assert len(files) == 0, f"Temp file not cleaned up: {files}"

    def test_encoding_parameter(self, tmp_path):
        target = tmp_path / "test.txt"
        atomic_write_text(target, "héllo wörld", encoding="utf-8")
        assert target.read_text(encoding="utf-8") == "héllo wörld"
