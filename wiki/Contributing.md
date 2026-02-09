# Contributing to SDM Spice

Thank you for your interest in contributing to SDM Spice! This guide explains how to contribute to the project.

## Project Status

SDM Spice is an SDSMT Capstone project currently in active development. We welcome contributions from the community.

## Ways to Contribute

### Report Bugs
1. Check [existing issues](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues) to avoid duplicates
2. Create a new issue with the `bug` label
3. Include:
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - System information (OS, Python version)
   - Screenshots if applicable

### Request Features
1. Check [existing issues](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues) for similar requests
2. Create a new issue with the `enhancement` label
3. Describe:
   - The feature you'd like
   - Why it would be useful
   - Possible implementation approach

### Submit Code
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Development Setup

### Prerequisites
- Python 3.10+
- Git
- ngspice

### Clone and Setup

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR-USERNAME/Spice-GUI.git
cd Spice-GUI

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r app/requirements.txt

# Run the application
python app/main.py
```

### Create a Branch

```bash
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `docs/description` - Documentation updates

## Code Guidelines

### Python Style
- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to public functions and classes
- Keep functions focused and reasonably sized

### PyQt6 Conventions
- Use signals and slots for component communication
- Follow Qt naming conventions (camelCase for methods)
- Clean up resources properly

### Example Code Style

```python
def calculate_node_voltage(self, node_id: str) -> float:
    """
    Calculate the voltage at a specific node.

    Args:
        node_id: The identifier of the node

    Returns:
        The voltage at the node in volts

    Raises:
        NodeNotFoundError: If the node doesn't exist
    """
    if node_id not in self.nodes:
        raise NodeNotFoundError(f"Node {node_id} not found")

    return self._compute_voltage(node_id)
```

## Commit Messages

Use clear, descriptive commit messages:

```
Add DC sweep analysis dialog

- Create AnalysisDialog class for parameter input
- Add validation for start/stop/step values
- Connect dialog to simulation runner
```

Format:
- First line: Brief summary (50 chars or less)
- Blank line
- Detailed description (if needed)

## Pull Request Process

1. **Update documentation** if you changed functionality
2. **Test your changes** thoroughly
3. **Update the changelog** if applicable
4. **Create the PR** with a clear description

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
How was this tested?

## Screenshots
If applicable, add screenshots

## Checklist
- [ ] Code follows project style
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
```

## Testing

### Manual Testing
Currently, SDM Spice relies on manual testing. Before submitting:
1. Test the specific feature/fix
2. Verify existing functionality still works
3. Test on your platform

### Future: Automated Testing
We plan to add automated tests. Contributions to test infrastructure are welcome!

## Project Structure

```
Spice-GUI/
├── app/
│   ├── main.py              # Entry point
│   ├── requirements.txt     # Dependencies
│   ├── GUI/                  # UI components
│   │   ├── main_window.py
│   │   ├── circuit_canvas.py
│   │   ├── component_item.py
│   │   └── ...
│   └── simulation/           # SPICE integration
│       ├── netlist_generator.py
│       ├── ngspice_runner.py
│       └── result_parser.py
├── DiscoveryDocs/           # Project documentation
├── Doc/                     # Additional docs
└── README.md
```

## Labels

Issues and PRs use these labels:

| Label | Description |
|-------|-------------|
| `bug` | Something isn't working |
| `enhancement` | New feature request |
| `documentation` | Documentation improvements |
| `good first issue` | Good for newcomers |
| `help wanted` | Extra attention needed |
| `priority: critical` | Blocking issues |
| `priority: high` | Important issues |
| `priority: medium` | Should address soon |
| `priority: low` | Nice to have |
| `component` | Circuit component related |
| `analysis` | Simulation analysis related |
| `tech-debt` | Code cleanup/refactoring |
| `testing` | Test-related |
| `ui/ux` | User interface related |

## Getting Help

- **Questions**: Open a discussion or issue with `question` label
- **Bugs**: Create an issue with `bug` label
- **Features**: Create an issue with `enhancement` label

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help others learn

## Recognition

Contributors will be acknowledged in:
- Release notes
- Contributors list
- Project documentation

## Contact

For project-related questions, use GitHub Issues.

## See Also

- [[Technology Stack]] - Technical details
- [[Architecture Overview]] - System design
- [[Roadmap]] - Project timeline
