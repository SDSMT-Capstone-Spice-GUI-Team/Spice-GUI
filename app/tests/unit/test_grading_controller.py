"""Tests for the grading controller — MVC layer boundary enforcement.

Verifies that:
1. The grading controller correctly delegates to grading subsystem modules.
2. GUI files do not import directly from ``grading.*`` at runtime.
"""

import ast
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# 1. Controller delegation tests
# ---------------------------------------------------------------------------


class TestGradingControllerDelegation:
    """Verify that controller functions delegate correctly."""

    def test_load_rubric_delegates(self, tmp_path):
        """load_rubric should load and validate a rubric file."""
        import json

        from controllers.grading_controller import load_rubric

        rubric_data = {
            "title": "Test Rubric",
            "total_points": 10,
            "checks": [
                {
                    "check_id": "c1",
                    "check_type": "component_exists",
                    "points": 10,
                    "params": {"component_id": "R1"},
                    "feedback_pass": "ok",
                    "feedback_fail": "missing",
                }
            ],
        }
        path = tmp_path / "test.spice-rubric"
        path.write_text(json.dumps(rubric_data))

        rubric = load_rubric(str(path))
        assert rubric.title == "Test Rubric"
        assert rubric.total_points == 10
        assert len(rubric.checks) == 1

    def test_save_rubric_delegates(self, tmp_path):
        """save_rubric should write a valid rubric file."""
        import json

        from controllers.grading_controller import load_rubric, save_rubric
        from grading.rubric import Rubric, RubricCheck

        rubric = Rubric(
            title="Saved Rubric",
            total_points=5,
            checks=[
                RubricCheck(
                    check_id="c1",
                    check_type="ground",
                    points=5,
                    feedback_pass="ok",
                    feedback_fail="no ground",
                )
            ],
        )
        path = tmp_path / "out.spice-rubric"
        save_rubric(rubric, str(path))

        loaded = load_rubric(str(path))
        assert loaded.title == "Saved Rubric"

    def test_validate_rubric_returns_errors(self):
        """validate_rubric should return error list for bad input."""
        from controllers.grading_controller import validate_rubric

        errors = validate_rubric("", [])
        assert len(errors) >= 2  # title required, checks required

    def test_generate_check_id_unique(self):
        """generate_check_id should produce a unique ID."""
        from controllers.grading_controller import generate_check_id

        existing = {"check_1", "check_2"}
        new_id = generate_check_id(existing)
        assert new_id not in existing
        assert new_id == "check_3"

    def test_calculate_total_points(self):
        """calculate_total_points should sum points."""
        from controllers.grading_controller import calculate_total_points

        checks = [{"points": 5}, {"points": 10}, {"points": 3}]
        assert calculate_total_points(checks) == 18

    def test_build_rubric_creates_rubric(self):
        """build_rubric should construct a Rubric from check data."""
        from controllers.grading_controller import build_rubric

        checks_data = [
            {
                "check_id": "c1",
                "check_type": "ground",
                "points": 10,
                "params": {},
                "feedback_pass": "",
                "feedback_fail": "",
            }
        ]
        rubric = build_rubric("Test", checks_data)
        assert rubric.title == "Test"
        assert rubric.total_points == 10

    def test_get_check_type_params_returns_dict(self):
        """get_check_type_params should return the params mapping."""
        from controllers.grading_controller import get_check_type_params

        params = get_check_type_params()
        assert isinstance(params, dict)
        assert "component_exists" in params
        assert "topology" in params

    def test_extract_component_ids(self):
        """extract_component_ids should parse IDs from check strings."""
        from controllers.grading_controller import extract_component_ids

        ids = extract_component_ids("exists_R1")
        assert "R1" in ids

    def test_create_grader_returns_grader(self):
        """create_grader should return a CircuitGrader instance."""
        from controllers.grading_controller import create_grader

        grader = create_grader()
        assert hasattr(grader, "grade")

    def test_create_batch_grader_returns_grader(self):
        """create_batch_grader should return a BatchGrader instance."""
        from controllers.grading_controller import create_batch_grader

        grader = create_batch_grader()
        assert hasattr(grader, "grade_folder")

    def test_grade_circuit(self):
        """grade_circuit should produce a GradingResult."""
        from controllers.grading_controller import grade_circuit
        from grading.rubric import Rubric, RubricCheck
        from models.circuit import CircuitModel

        rubric = Rubric(
            title="Test",
            total_points=5,
            checks=[
                RubricCheck(
                    check_id="ground_exists",
                    check_type="ground",
                    points=5,
                    feedback_pass="ok",
                    feedback_fail="no ground",
                )
            ],
        )
        circuit = CircuitModel()
        result = grade_circuit(circuit, rubric, student_file="test.json")
        assert result.student_file == "test.json"
        assert result.total_points == 5

    def test_generate_rubric_from_circuit(self):
        """generate_rubric_from_circuit should produce a rubric skeleton."""
        from controllers.grading_controller import generate_rubric_from_circuit
        from models.circuit import CircuitModel
        from models.component import ComponentData

        circuit = CircuitModel()
        circuit.components["R1"] = ComponentData(
            component_id="R1",
            component_type="Resistor",
            value="1k",
            position=(100, 100),
        )
        rubric = generate_rubric_from_circuit(circuit)
        assert rubric.title == "Auto-Generated Rubric"
        assert len(rubric.checks) > 0

    def test_grades_extension_constant(self):
        """GRADES_EXTENSION should be the expected value."""
        from controllers.grading_controller import GRADES_EXTENSION

        assert GRADES_EXTENSION == ".spice-grades"


# ---------------------------------------------------------------------------
# 2. GUI import boundary tests
# ---------------------------------------------------------------------------

# GUI source files that must NOT import from grading.* at runtime
_GUI_DIR = Path(__file__).resolve().parent.parent.parent / "GUI"

_GUI_FILES_TO_CHECK = [
    "batch_grading_dialog.py",
    "grading_panel.py",
    "rubric_editor_dialog.py",
    "main_window_view.py",
]


def _get_runtime_grading_imports(filepath: Path) -> list[tuple[int, str]]:
    """Parse a Python file and return (line, module) for runtime grading imports.

    Ignores imports inside ``if TYPE_CHECKING:`` blocks.
    """
    source = filepath.read_text()
    tree = ast.parse(source, filename=str(filepath))

    violations: list[tuple[int, str]] = []

    # Track whether we are inside a TYPE_CHECKING block
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            # Check if this import is inside an `if TYPE_CHECKING:` block
            if _is_inside_type_checking(tree, node):
                continue

            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("grading.") or node.module == "grading":
                    violations.append((node.lineno, node.module))

    return violations


def _is_inside_type_checking(tree: ast.Module, target_node: ast.AST) -> bool:
    """Check if target_node is nested inside an ``if TYPE_CHECKING:`` block."""
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            # Check for `if TYPE_CHECKING:` pattern
            test = node.test
            is_type_checking = False
            if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
                is_type_checking = True
            elif isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
                is_type_checking = True

            if is_type_checking:
                # Check if target_node is in the body of this if block
                for child in ast.walk(node):
                    if child is target_node:
                        return True
    return False


@pytest.mark.parametrize("filename", _GUI_FILES_TO_CHECK)
def test_no_runtime_grading_imports(filename):
    """GUI files must not import from grading.* at runtime."""
    filepath = _GUI_DIR / filename
    if not filepath.exists():
        pytest.skip(f"{filepath} not found")

    violations = _get_runtime_grading_imports(filepath)
    if violations:
        lines = [f"  line {line}: from {mod}" for line, mod in violations]
        pytest.fail(
            f"{filename} has runtime imports from grading modules "
            f"(should use controllers.grading_controller instead):\n" + "\n".join(lines)
        )
