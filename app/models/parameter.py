"""
ParameterManager - Manages SPICE .param directives.

This module contains no Qt dependencies. It stores named parameters
that can be referenced in component values using {param_name} syntax
and emitted as .param directives in the netlist.
"""

import re
from dataclasses import dataclass, field

# Pattern matching {param_name} or {expression} references in component values
PARAM_REF_PATTERN = re.compile(r"\{([^}]+)\}")

# Valid parameter name: starts with letter/underscore, followed by alphanumerics/underscores
PARAM_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass
class Parameter:
    """A single named SPICE parameter."""

    name: str
    value: str  # Default value, e.g. "1k", "5", "{R_fb / R_in}"

    def to_dict(self) -> dict:
        return {"name": self.name, "value": self.value}

    @classmethod
    def from_dict(cls, data: dict) -> "Parameter":
        return cls(name=data["name"], value=data["value"])


@dataclass
class ParameterManager:
    """Manages a collection of named SPICE parameters.

    Parameters are stored in insertion order and can be referenced
    in component values using {param_name} syntax.
    """

    parameters: dict[str, Parameter] = field(default_factory=dict)

    def add_parameter(self, name: str, value: str) -> None:
        """Add or update a named parameter.

        Args:
            name: Parameter name (must be a valid identifier).
            value: Default value string (e.g. "1k", "5", "{R_fb/R_in}").

        Raises:
            ValueError: If the name is not a valid identifier.
        """
        if not PARAM_NAME_PATTERN.match(name):
            raise ValueError(
                f"Invalid parameter name '{name}': must start with a letter "
                f"or underscore and contain only alphanumerics/underscores."
            )
        self.parameters[name] = Parameter(name=name, value=value)

    def remove_parameter(self, name: str) -> None:
        """Remove a parameter by name.

        Raises:
            KeyError: If the parameter does not exist.
        """
        if name not in self.parameters:
            raise KeyError(f"Parameter '{name}' not found.")
        del self.parameters[name]

    def get_parameter(self, name: str) -> Parameter | None:
        """Get a parameter by name, or None if not found."""
        return self.parameters.get(name)

    def get_all_parameters(self) -> list[Parameter]:
        """Return all parameters in insertion order."""
        return list(self.parameters.values())

    def clear(self) -> None:
        """Remove all parameters."""
        self.parameters.clear()

    def generate_directives(self) -> list[str]:
        """Generate .param directive lines for the netlist.

        Returns:
            List of strings like [".param R_load = 1k", ".param Vdd = 5"].
        """
        return [f".param {p.name} = {p.value}" for p in self.parameters.values()]

    def find_references(self, value: str) -> list[str]:
        """Extract parameter reference names from a component value string.

        Args:
            value: A component value that may contain {param_name} references.

        Returns:
            List of referenced names (may include expressions, not just names).
        """
        return PARAM_REF_PATTERN.findall(value)

    def extract_param_names(self, value: str) -> set[str]:
        """Extract just the parameter names referenced in a value string.

        Handles both simple references like {R_load} and expressions
        like {R_fb / R_in} by extracting all identifier tokens.

        Args:
            value: A component value string.

        Returns:
            Set of parameter name strings found in the references.
        """
        names = set()
        for ref in self.find_references(value):
            # Extract identifiers from the expression
            tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", ref)
            names.update(tokens)
        return names

    def validate_references(self, component_values: dict[str, str]) -> list[str]:
        """Check that all parameter references in component values are defined.

        Args:
            component_values: Dict mapping component_id to its value string.

        Returns:
            List of error messages for undefined parameter references.
        """
        defined = set(self.parameters.keys())
        errors = []
        for comp_id, value in component_values.items():
            referenced = self.extract_param_names(value)
            undefined = referenced - defined
            for name in sorted(undefined):
                errors.append(f"Component {comp_id}: undefined parameter '{name}'")
        return errors

    def has_param_reference(self, value: str) -> bool:
        """Check if a value string contains any {param} references."""
        return bool(PARAM_REF_PATTERN.search(value))

    def to_dict(self) -> list[dict]:
        """Serialize parameters to a list of dicts."""
        return [p.to_dict() for p in self.parameters.values()]

    @classmethod
    def from_dict(cls, data: list[dict]) -> "ParameterManager":
        """Deserialize parameters from a list of dicts."""
        mgr = cls()
        for item in data:
            param = Parameter.from_dict(item)
            mgr.parameters[param.name] = param
        return mgr
