"""
WaveformExpressionManager - Manages user-defined computed plot expressions.

This module contains no Qt dependencies. It stores math expressions
(e.g. V(out) - V(in), dB(V(out)/V(in))) that are passed to ngspice
via let directives in the .control block.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

# Pattern to extract node voltage references: V(name) or v(name)
NODE_REF_PATTERN = re.compile(r"[vV]\(([^)]+)\)")

# Pattern to extract component current references: I(name) or i(name)
CURRENT_REF_PATTERN = re.compile(r"[iI]\(([^)]+)\)")


@dataclass
class WaveformExpression:
    """A user-defined computed waveform expression.

    Attributes:
        name: Display name / alias for the expression (e.g. "gain_db").
        expression: The ngspice expression string (e.g. "db(v(out)/v(in))").
        description: Optional human-readable description.
    """

    name: str
    expression: str
    description: str = ""

    def to_dict(self) -> dict:
        data = {"name": self.name, "expression": self.expression}
        if self.description:
            data["description"] = self.description
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "WaveformExpression":
        return cls(
            name=data["name"],
            expression=data["expression"],
            description=data.get("description", ""),
        )

    def get_node_references(self) -> set[str]:
        """Extract node names referenced in V() calls."""
        return set(NODE_REF_PATTERN.findall(self.expression))

    def get_current_references(self) -> set[str]:
        """Extract component names referenced in I() calls."""
        return set(CURRENT_REF_PATTERN.findall(self.expression))

    def get_all_references(self) -> set[str]:
        """Extract all node and component references."""
        return self.get_node_references() | self.get_current_references()


# Common preset expressions
EXPRESSION_PRESETS = [
    WaveformExpression(
        name="differential",
        expression="v({node_p}) - v({node_n})",
        description="Differential voltage between two nodes",
    ),
    WaveformExpression(
        name="gain",
        expression="v({output}) / v({input})",
        description="Voltage gain (linear)",
    ),
    WaveformExpression(
        name="gain_db",
        expression="db(v({output}) / v({input}))",
        description="Voltage gain in decibels",
    ),
    WaveformExpression(
        name="power",
        expression="v({node_p}) * i({component})",
        description="Power dissipation in a component",
    ),
]


def get_preset_names() -> list[str]:
    """Return names of all available preset expressions."""
    return [p.name for p in EXPRESSION_PRESETS]


def get_preset(name: str) -> Optional[WaveformExpression]:
    """Get a preset expression by name, or None if not found."""
    for p in EXPRESSION_PRESETS:
        if p.name == name:
            return WaveformExpression(
                name=p.name,
                expression=p.expression,
                description=p.description,
            )
    return None


@dataclass
class WaveformExpressionManager:
    """Manages user-defined waveform expressions.

    Expressions are stored in insertion order and can be added/removed.
    Each expression generates a `let` directive in the ngspice .control
    block and is included in the print/wrdata output.
    """

    expressions: list[WaveformExpression] = field(default_factory=list)

    def add_expression(self, name: str, expression: str, description: str = "") -> WaveformExpression:
        """Add a new expression.

        Args:
            name: Alias for the expression (used as ngspice variable name).
            expression: The ngspice math expression.
            description: Optional human-readable description.

        Raises:
            ValueError: If the name is empty or already exists.

        Returns:
            The created WaveformExpression.
        """
        if not name:
            raise ValueError("Expression name cannot be empty.")
        if any(e.name == name for e in self.expressions):
            raise ValueError(f"Expression '{name}' already exists.")
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
            raise ValueError(f"Invalid expression name '{name}': must be a valid identifier.")
        expr = WaveformExpression(name=name, expression=expression, description=description)
        self.expressions.append(expr)
        return expr

    def remove_expression(self, name: str) -> WaveformExpression:
        """Remove an expression by name.

        Raises:
            KeyError: If the expression does not exist.
        """
        for i, e in enumerate(self.expressions):
            if e.name == name:
                return self.expressions.pop(i)
        raise KeyError(f"Expression '{name}' not found.")

    def get_expression(self, name: str) -> Optional[WaveformExpression]:
        """Get an expression by name, or None if not found."""
        for e in self.expressions:
            if e.name == name:
                return e
        return None

    def get_all(self) -> list[WaveformExpression]:
        """Return all expressions in insertion order."""
        return list(self.expressions)

    def clear(self) -> None:
        """Remove all expressions."""
        self.expressions.clear()

    def generate_let_directives(self) -> list[str]:
        """Generate ngspice let directives for the .control block.

        Returns:
            List of strings like ["let gain_db = db(v(out)/v(in))"].
        """
        return [f"let {e.name} = {e.expression}" for e in self.expressions]

    def get_print_variables(self) -> list[str]:
        """Return variable names for use in print/wrdata commands."""
        return [e.name for e in self.expressions]

    def validate_references(self, available_nodes: set[str], available_components: set[str]) -> list[str]:
        """Check that all node/component references in expressions are valid.

        Args:
            available_nodes: Set of valid node label strings.
            available_components: Set of valid component ID strings.

        Returns:
            List of error messages for invalid references.
        """
        errors = []
        for expr in self.expressions:
            for node_ref in expr.get_node_references():
                if node_ref not in available_nodes:
                    errors.append(f"Expression '{expr.name}': unknown node '{node_ref}'")
            for comp_ref in expr.get_current_references():
                if comp_ref not in available_components:
                    errors.append(f"Expression '{expr.name}': unknown component '{comp_ref}'")
        return errors

    def to_dict(self) -> list[dict]:
        """Serialize expressions to a list of dicts."""
        return [e.to_dict() for e in self.expressions]

    @classmethod
    def from_dict(cls, data: list[dict]) -> "WaveformExpressionManager":
        """Deserialize expressions from a list of dicts."""
        mgr = cls()
        for item in data:
            expr = WaveformExpression.from_dict(item)
            mgr.expressions.append(expr)
        return mgr
