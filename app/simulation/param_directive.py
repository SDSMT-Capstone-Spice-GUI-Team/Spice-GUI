"""
simulation/param_directive.py

Parse, resolve, and emit SPICE .param directives for parametric netlists.

Supports:
    .param Rval = 1k
    .param gain = {Rfeedback / Rinput}
    .param BW = {1 / (2 * pi * R * C)}
    Component values like {Rval} or {gain * 2}

Pure Python — no Qt dependencies.
"""

import ast
import logging
import math
import operator
import re

logger = logging.getLogger(__name__)

# Pattern for .param directives: .param name = value_or_expression
_PARAM_LINE_RE = re.compile(
    r"^\s*\.param\s+(\w+)\s*=\s*(.+?)\s*$",
    re.IGNORECASE,
)

# Pattern for braced expressions in component values: {expr}
_BRACE_EXPR_RE = re.compile(r"\{([^}]+)\}")

# SPICE suffix multipliers
_SPICE_SUFFIXES = {
    "t": 1e12,
    "g": 1e9,
    "meg": 1e6,
    "k": 1e3,
    "m": 1e-3,
    "u": 1e-6,
    "n": 1e-9,
    "p": 1e-12,
    "f": 1e-15,
}

# Safe operators for expression evaluation
_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}

_UNARYOPS = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Built-in constants and functions
_BUILTINS = {
    "pi": math.pi,
    "e": math.e,
    "sqrt": math.sqrt,
    "abs": abs,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "pow": pow,
    "min": min,
    "max": max,
}


def parse_spice_value(s: str) -> float:
    """
    Parse a SPICE value string with optional SI suffix.

    Examples:
        "1k"   -> 1000.0
        "4.7u" -> 4.7e-6
        "10"   -> 10.0
        "2.2meg" -> 2.2e6
    """
    s = s.strip()
    if not s:
        raise ValueError("Empty value string")

    # Try direct float first
    try:
        return float(s)
    except ValueError:
        pass

    # Try suffix matching (longest suffix first)
    s_lower = s.lower()
    for suffix, mult in sorted(_SPICE_SUFFIXES.items(), key=lambda x: -len(x[0])):
        if s_lower.endswith(suffix):
            num_part = s[: -len(suffix)]
            try:
                return float(num_part) * mult
            except ValueError:
                continue

    raise ValueError(f"Cannot parse SPICE value: {s!r}")


class _ParamEvaluator(ast.NodeVisitor):
    """Evaluate an expression AST with parameter namespace."""

    def __init__(self, namespace: dict[str, float]):
        self._ns = namespace

    def visit_Expression(self, node: ast.Expression) -> float:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> float:
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError(f"Unsupported constant: {node.value!r}")

    def visit_Name(self, node: ast.Name) -> float:
        name = node.id
        if name in self._ns:
            val = self._ns[name]
            if callable(val):
                return val
            return val
        raise ValueError(f"Undefined parameter: {name!r}")

    def visit_BinOp(self, node: ast.BinOp) -> float:
        op_type = type(node.op)
        if op_type not in _BINOPS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        return _BINOPS[op_type](self.visit(node.left), self.visit(node.right))

    def visit_UnaryOp(self, node: ast.UnaryOp) -> float:
        op_type = type(node.op)
        if op_type not in _UNARYOPS:
            raise ValueError(f"Unsupported unary op: {op_type.__name__}")
        return _UNARYOPS[op_type](self.visit(node.operand))

    def visit_Call(self, node: ast.Call) -> float:
        func = self.visit(node.func)
        if not callable(func):
            raise ValueError(f"Not callable: {node.func}")
        args = [self.visit(a) for a in node.args]
        return func(*args)

    def generic_visit(self, node: ast.AST) -> float:
        raise ValueError(f"Unsupported AST node: {type(node).__name__}")


def _eval_expr(expr_str: str, namespace: dict[str, float]) -> float:
    """Safely evaluate a math expression with a parameter namespace."""
    try:
        tree = ast.parse(expr_str, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Invalid expression: {expr_str!r} — {e}") from e
    return _ParamEvaluator(namespace).visit(tree)


class ParamDirectiveProcessor:
    """
    Manages .param directive definitions and resolves parametric values.

    Usage:
        proc = ParamDirectiveProcessor()
        proc.define("Rval", "1k")
        proc.define("gain", "{Rfeedback / Rval}")
        proc.define("Rfeedback", "10k")
        proc.resolve_all()
        value = proc.substitute("{gain * 2}")
    """

    def __init__(self):
        self._raw_params: dict[str, str] = {}  # name -> raw value string
        self._resolved: dict[str, float] = {}  # name -> resolved float

    @property
    def params(self) -> dict[str, float]:
        """Resolved parameter values (read-only copy)."""
        return dict(self._resolved)

    @property
    def raw_params(self) -> dict[str, str]:
        """Raw parameter definitions (read-only copy)."""
        return dict(self._raw_params)

    def define(self, name: str, value: str) -> None:
        """
        Define a parameter.

        Args:
            name: Parameter name (valid identifier).
            value: Raw value — either a SPICE value like ``"1k"`` or a
                   braced expression like ``"{R2 / R1}"``.
        """
        self._raw_params[name] = value.strip()
        # Invalidate resolved cache
        self._resolved.clear()

    def parse_directives(self, netlist_text: str) -> list[str]:
        """
        Extract .param directives from netlist text.

        Returns the list of parameter names found.
        """
        names = []
        for line in netlist_text.splitlines():
            m = _PARAM_LINE_RE.match(line)
            if m:
                name, value = m.group(1), m.group(2)
                self.define(name, value)
                names.append(name)
        return names

    def resolve_all(self) -> dict[str, float]:
        """
        Resolve all parameters, handling dependencies between them.

        Uses iterative resolution: each pass resolves parameters whose
        dependencies are already known. Raises ValueError if there are
        circular dependencies or undefined references.

        Returns:
            Dict mapping parameter names to resolved float values.
        """
        self._resolved.clear()

        # Build namespace with builtins
        namespace = dict(_BUILTINS)

        remaining = dict(self._raw_params)
        max_iterations = len(remaining) + 1

        for _ in range(max_iterations):
            if not remaining:
                break

            progress = False
            still_remaining = {}

            for name, raw_val in remaining.items():
                try:
                    value = self._try_resolve(raw_val, namespace)
                    self._resolved[name] = value
                    namespace[name] = value
                    progress = True
                except ValueError:
                    still_remaining[name] = raw_val

            remaining = still_remaining
            if not progress:
                # No progress — either circular deps or undefined refs
                break

        if remaining:
            raise ValueError(
                f"Cannot resolve parameters (circular or undefined): {', '.join(sorted(remaining.keys()))}"
            )

        return dict(self._resolved)

    def _try_resolve(self, raw_val: str, namespace: dict[str, float]) -> float:
        """
        Try to resolve a single raw value string.

        Handles both plain SPICE values and braced expressions.
        """
        raw_val = raw_val.strip()

        # Check for braced expression: {expr}
        brace_match = _BRACE_EXPR_RE.fullmatch(raw_val)
        if brace_match:
            return _eval_expr(brace_match.group(1), namespace)

        # Also allow unbraced expression if it starts with a letter
        # (parameter reference) or contains operators
        try:
            return parse_spice_value(raw_val)
        except ValueError:
            # Try as expression
            return _eval_expr(raw_val, namespace)

    def substitute(self, text: str) -> str:
        """
        Replace ``{expr}`` placeholders in text with evaluated values.

        Args:
            text: String potentially containing ``{param}`` or ``{expr}``
                  placeholders.

        Returns:
            String with all braced expressions replaced by their numeric values.

        Raises:
            ValueError: If resolution fails (e.g., undefined parameter).
        """
        namespace = dict(_BUILTINS)
        namespace.update(self._resolved)

        def _replace(m: re.Match) -> str:
            expr = m.group(1)
            value = _eval_expr(expr, namespace)
            return format_param_value(value)

        return _BRACE_EXPR_RE.sub(_replace, text)

    def is_parametric(self, value: str) -> bool:
        """Check if a value string contains parametric expressions."""
        return bool(_BRACE_EXPR_RE.search(value))

    def emit_directives(self) -> list[str]:
        """
        Generate .param directive lines for inclusion in a netlist.

        Returns lines like ``.param Rval = 1k``.
        """
        lines = []
        for name, raw_val in sorted(self._raw_params.items()):
            lines.append(f".param {name} = {raw_val}")
        return lines


def format_param_value(value: float) -> str:
    """
    Format a resolved parameter value as a compact SPICE-compatible string.

    Uses SI suffixes where appropriate.
    """
    if value == 0:
        return "0"

    abs_val = abs(value)

    # Use suffix if it gives a cleaner representation
    for suffix, mult in sorted(_SPICE_SUFFIXES.items(), key=lambda x: -x[1]):
        if abs_val >= mult and abs_val < mult * 1000:
            scaled = value / mult
            # Use integer if it's clean
            if scaled == int(scaled):
                return f"{int(scaled)}{suffix}"
            return f"{scaled:.4g}{suffix}"

    # Fall back to scientific or plain notation
    if abs_val >= 1e-3 and abs_val < 1e6:
        if value == int(value):
            return str(int(value))
        return f"{value:.6g}"

    return f"{value:.4e}"
