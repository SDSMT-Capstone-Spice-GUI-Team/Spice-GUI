"""Tests for file size validation on load paths (#766)."""

import json

import pytest
from controllers.file_controller import MAX_FILE_SIZE, FileController, check_file_size


class TestCheckFileSize:
    """Verify check_file_size rejects oversized files."""

    def test_small_file_passes(self, tmp_path):
        f = tmp_path / "small.json"
        f.write_text("{}")
        check_file_size(f)  # should not raise

    def test_oversized_file_raises(self, tmp_path):
        f = tmp_path / "big.json"
        f.write_bytes(b"x" * (MAX_FILE_SIZE + 1))
        with pytest.raises(ValueError, match="too large"):
            check_file_size(f)

    def test_custom_limit(self, tmp_path):
        f = tmp_path / "medium.json"
        f.write_bytes(b"x" * 1001)
        with pytest.raises(ValueError, match="too large"):
            check_file_size(f, max_size=1000)

    def test_exact_limit_passes(self, tmp_path):
        f = tmp_path / "exact.json"
        f.write_bytes(b"x" * 1000)
        check_file_size(f, max_size=1000)  # should not raise


class TestLoadCircuitFileSizeValidation:
    """Verify load_circuit rejects oversized files."""

    def test_oversized_circuit_rejected(self, tmp_path):
        from unittest.mock import patch

        ctrl = FileController()
        f = tmp_path / "big.json"
        data = {"components": [], "wires": [], "counters": {}, "pad": "x" * 2000}
        f.write_text(json.dumps(data))

        with patch(
            "controllers.file_controller.check_file_size",
            side_effect=ValueError("File is too large"),
        ):
            with pytest.raises(ValueError, match="too large"):
                ctrl.load_circuit(f)
