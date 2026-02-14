"""
simulation/waveform_math.py

Evaluate user-supplied math expressions over simulation result vectors.

Expressions use Python-style syntax with simulation variable references:
    v(out) - v(in)
    abs(v(out))
    20 * log10(abs(v(out)))
    v(out) * i(R1)
    (v(out) - v(in)) / v(in) * 100

Pure Python — no Qt dependencies.
"""

import ast
import logging
import math
import operator
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Safe math functions available in expressions
_MATH_FUNCTIONS = {
    "abs": abs,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "pow": pow,
    "max": max,
    "min": min,
    "pi": math.pi,
    "e": math.e,
}

# Safe binary operators
_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

# Safe unary operators
_UNARYOPS = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Pattern matching v(name) or i(name) references in expression text
_VAR_REF_PATTERN = re.compile(r"\b([vi])\(([^)]+)\)")


def _normalize_var_ref(match: re.Match) -> str:
    """Convert v(out) -> __v_out__, i(R1) -> __i_R1__ for valid Python identifiers."""
    prefix = match.group(1)
    name = match.group(2)
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    return f"__{prefix}_{safe_name}__"


def _preprocess_expression(expr: str) -> str:
    """Convert SPICE-style variable references to Python identifiers."""
    return _VAR_REF_PATTERN.sub(_normalize_var_ref, expr)


def extract_variable_refs(expr: str) -> list[str]:
    """
    Extract all v(...) and i(...) references from an expression.

    Returns a list of original reference strings, e.g. ["v(out)", "i(R1)"].
    """
    return [f"{m.group(1)}({m.group(2)})" for m in _VAR_REF_PATTERN.finditer(expr)]


class _SafeEvaluator(ast.NodeVisitor):
    """
    Evaluate an AST safely with only whitelisted operations.

    Variables are resolved from a provided namespace dict.
    """

    def __init__(self, namespace: dict[str, float]):
        self._ns = namespace

    def visit_Expression(self, node: ast.Expression) -> float:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> float:
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")

    def visit_Name(self, node: ast.Name) -> float:
        name = node.id
        if name in self._ns:
            return self._ns[name]
        if name in _MATH_FUNCTIONS:
            return _MATH_FUNCTIONS[name]
        raise ValueError(f"Unknown variable: {name}")

    def visit_BinOp(self, node: ast.BinOp) -> float:
        op_type = type(node.op)
        if op_type not in _BINOPS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        left = self.visit(node.left)
        right = self.visit(node.right)
        return _BINOPS[op_type](left, right)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> float:
        op_type = type(node.op)
        if op_type not in _UNARYOPS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        return _UNARYOPS[op_type](self.visit(node.operand))

    def visit_Call(self, node: ast.Call) -> float:
        func = self.visit(node.func)
        if not callable(func):
            raise ValueError(f"Not a callable: {node.func}")
        args = [self.visit(arg) for arg in node.args]
        if node.keywords:
            raise ValueError("Keyword arguments are not supported")
        return func(*args)

    def generic_visit(self, node: ast.AST) -> float:
        raise ValueError(f"Unsupported expression element: {type(node).__name__}")


def evaluate_expression(
    expr: str,
    variables: dict[str, float],
) -> float:
    """
    Evaluate a single scalar expression.

    Args:
        expr: Math expression string, e.g. ``"v(out) - v(in)"``
        variables: Mapping of variable references to values.
                   Keys should be the original SPICE-style refs like ``"v(out)"``.

    Returns:
        The computed float result.

    Raises:
        ValueError: If the expression is invalid or references unknown variables.
    """
    # Build internal namespace: convert v(out) -> __v_out__ keys
    namespace: dict[str, float] = {}
    for ref, value in variables.items():
        m = _VAR_REF_PATTERN.fullmatch(ref)
        if m:
            internal = _normalize_var_ref(m)
            namespace[internal] = float(value)
        else:
            namespace[ref] = float(value)

    # Add math constants
    namespace["pi"] = math.pi
    namespace["e"] = math.e

    preprocessed = _preprocess_expression(expr)

    try:
        tree = ast.parse(preprocessed, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Invalid expression syntax: {e}") from e

    evaluator = _SafeEvaluator(namespace)
    return evaluator.visit(tree)


def evaluate_expression_over_vectors(
    expr: str,
    vector_data: dict[str, list[float]],
) -> list[float]:
    """
    Evaluate an expression point-by-point over aligned vectors.

    Args:
        expr: Math expression string, e.g. ``"v(out) - v(in)"``
        vector_data: Mapping of variable references to lists of float values.
                     All lists must have the same length.

    Returns:
        List of computed float values, one per data point.

    Raises:
        ValueError: If vectors have mismatched lengths, expression is invalid, etc.
    """
    if not vector_data:
        raise ValueError("No vector data provided")

    lengths = {k: len(v) for k, v in vector_data.items()}
    unique_lengths = set(lengths.values())
    if len(unique_lengths) > 1:
        raise ValueError(f"Vector length mismatch: {lengths}")

    n = next(iter(unique_lengths))
    results = []

    for i in range(n):
        point_vars = {k: v[i] for k, v in vector_data.items()}
        results.append(evaluate_expression(expr, point_vars))

    return results


def validate_expression(expr: str, available_vars: Optional[list[str]] = None) -> list[str]:
    """
    Check an expression for errors without evaluating it.

    Args:
        expr: The expression string to validate.
        available_vars: Optional list of variable names that are valid
                        (e.g. ``["v(out)", "v(in)", "i(R1)"]``).

    Returns:
        List of error strings. Empty list means the expression is valid.
    """
    errors = []

    if not expr or not expr.strip():
        return ["Expression is empty"]

    # Check for referenced variables
    refs = extract_variable_refs(expr)
    if available_vars is not None:
        for ref in refs:
            if ref not in available_vars:
                errors.append(f"Unknown variable: {ref}")

    # Check syntax
    preprocessed = _preprocess_expression(expr)
    try:
        tree = ast.parse(preprocessed, mode="eval")
    except SyntaxError as e:
        errors.append(f"Syntax error: {e}")
        return errors

    # Walk the AST to check for unsupported constructs
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and type(node.op) not in _BINOPS:
            errors.append(f"Unsupported operator: {type(node.op).__name__}")
        if isinstance(node, ast.UnaryOp) and type(node.op) not in _UNARYOPS:
            errors.append(f"Unsupported unary operator: {type(node.op).__name__}")

    return errors
