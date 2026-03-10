# ADR 003: JSON Circuit File Format

**Date:** 2024-10-28 (Implemented)
**Status:** Accepted
**Deciders:** Development Team
**Related Commits:** 60a0c52, 00670ea

---

## Context

The application needs to save and load circuit designs persistently. Circuit data includes:
- Component list (type, ID, value, position, rotation)
- Wire connections (component endpoints, terminals, waypoints)
- Node graph (electrical connectivity)
- Analysis configuration (type, parameters)

### Requirements
- **Human-readable:** Students/instructors should be able to inspect files
- **Version control friendly:** Text-based for Git diffs
- **Portable:** Share via email, LMS, file sharing
- **Validatable:** Detect corrupted or incompatible files
- **Extensible:** Support adding new component types/properties

---

## Decision

**We will use JSON as the circuit file format with schema validation on load.**

### File Structure

```json
{
  "components": [
    {
      "id": "R1",
      "type": "resistor",
      "value": "1k",
      "pos": {"x": 100, "y": 200},
      "rotation": 0
    }
  ],
  "wires": [
    {
      "start_comp": "R1",
      "start_term": 0,
      "end_comp": "V1",
      "end_term": 1,
      "waypoints": [[120, 200], [120, 300]]
    }
  ],
  "annotations": [
    {
      "type": "text",
      "content": "Power Supply",
      "pos": {"x": 50, "y": 50}
    }
  ],
  "analysis": {
    "type": "transient",
    "tstop": "10m",
    "tstep": "100u"
  }
}
```

### Validation Rules

On load, validate:
- Top-level keys exist: `components`, `wires`
- Each component has: `id`, `type`, `value`, `pos`
- Position has numeric `x`, `y`
- Each wire has: `start_comp`, `end_comp`, `start_term`, `end_term`
- Wire references point to existing component IDs

Validation implemented in: `file_controller.py::validate_circuit_data()`

---

## Consequences

### Positive

✅ **Human-readable:** Can inspect/debug files in text editor
✅ **Git-friendly:** Text diffs show what changed between versions
✅ **Portable:** Works on any platform, no binary compatibility issues
✅ **Debugging:** Students can hand-edit files to test edge cases
✅ **Interoperability:** Easy to parse with scripts, other tools
✅ **Standard library:** Python's `json` module, no external dependencies
✅ **Extensible:** Add new fields without breaking old files

### Negative

❌ **File size:** Larger than binary formats (not significant for circuits)
❌ **Parse speed:** Slower than binary (negligible for typical circuits)
❌ **Precision:** Floating-point representation can lose precision
❌ **No compression:** Files not compressed by default
❌ **Verbosity:** Repetitive structure (many components)

### Mitigation Strategies

**File size:**
- Not a concern: 100-component circuit = ~30KB
- Can add compression later if needed (gzip wrapper)

**Parse performance:**
- JSON parsing is fast enough: <50ms for large circuits
- Lazy loading optimizes startup time

**Precision:**
- Grid-aligned layout uses integers for positions
- Component values stored as strings (preserve "1.5k" exactly)

**Versioning:**
- Include optional `"version": "1.0"` field for future format changes
- Backward compatibility: New fields optional, old fields preserved

---

## Alternatives Considered

### Alternative 1: XML Format
**Approach:**
```xml
<circuit>
  <component id="R1" type="resistor" value="1k">
    <position x="100" y="200"/>
  </component>
</circuit>
```

**Rejected because:**
- More verbose than JSON
- Less common in Python ecosystem
- Harder to hand-edit
- No significant advantage over JSON

### Alternative 2: Binary Format (Protocol Buffers, MessagePack)
**Approach:** Compiled schema, binary serialization

**Rejected because:**
- Not human-readable (major drawback for education)
- Can't inspect in text editor
- Requires schema compiler
- Poor Git diff support
- Overkill for file sizes we're dealing with

### Alternative 3: YAML Format
**Approach:**
```yaml
components:
  - id: R1
    type: resistor
    value: 1k
    pos: {x: 100, y: 200}
```

**Rejected because:**
- Requires PyYAML dependency
- Indentation-sensitive (error-prone for hand editing)
- Slower parsing than JSON
- JSON is more universal

### Alternative 4: Custom DSL (Domain-Specific Language)
**Approach:**
```
R1 resistor 1k at (100, 200)
V1 vsource 5 at (300, 200)
wire R1.0 to V1.1
```

**Rejected because:**
- Must write custom parser (maintenance burden)
- No tooling support (syntax highlighting, validation)
- Harder to extend
- JSON provides structure without complexity

### Alternative 5: SQLite Database
**Approach:** Embedded database file with tables for components, wires, etc.

**Rejected because:**
- Binary format (not human-readable)
- Poor version control (binary diffs)
- Overkill for single-circuit storage
- Would need export/import anyway
- Better suited for multi-circuit library (future consideration)

---

## Implementation Details

### Serialization (Model → JSON)
```python
# CircuitModel.to_dict()
def to_dict(self) -> dict:
    return {
        'components': [c.to_dict() for c in self.components],
        'wires': [w.to_dict() for w in self.wires],
        'analysis': self.analysis_config
    }
```

### Deserialization (JSON → Model)
```python
# CircuitModel.from_dict()
@classmethod
def from_dict(cls, data: dict) -> 'CircuitModel':
    model = cls()
    model.components = [Component.from_dict(c) for c in data['components']]
    model.wires = [Wire.from_dict(w) for w in data['wires']]
    model.rebuild_nodes()  # Reconstruct node graph
    return model
```

### Validation
```python
def validate_circuit_data(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("Invalid circuit file")

    if 'components' not in data:
        raise ValueError("Missing 'components' list")

    comp_ids = {c['id'] for c in data['components']}

    for wire in data.get('wires', []):
        if wire['start_comp'] not in comp_ids:
            raise ValueError(f"Wire references unknown component")
```

---

## Backward Compatibility Strategy

When adding new features:
1. **Optional fields:** New properties default if missing
2. **Version field:** Add `"version": "1.0"` to detect format
3. **Migration:** Old files load without version, assumed v1.0
4. **Deprecation:** Support old format for at least 2 major versions

Example:
```python
# Adding rotation (new field)
rotation = comp_data.get('rotation', 0)  # Default to 0 if missing

# Handling version
version = data.get('version', '1.0')
if version == '1.0':
    # Handle legacy format
```

---

## Format Evolution

### Current Version: 1.0 (Implicit)
- Components with basic properties
- Wires with waypoints
- Analysis configuration

### Potential Future Enhancements
- **Version 1.1:** Add annotations, net labels (already implemented)
- **Version 2.0:** Hierarchical circuits (subcircuits)
- **Version 2.1:** Simulation results embedded in file
- **Version 3.0:** Multi-page schematics

---

## Security Considerations

**Safe loading:**
```python
# Don't use eval() or exec() on file contents
# Use json.load() only - safe by design
with open(filepath, 'r') as f:
    data = json.load(f)  # Safe: no code execution
```

**Validation before trust:**
- Validate schema before deserializing objects
- Check component references before creating model
- Sanitize file paths in future multi-file circuits

---

## Related Decisions

- [ADR 001](001-local-first-no-user-accounts.md) - Local files, no database backend
- [ADR 002](002-mvc-architecture-zero-qt-dependencies.md) - Model serialization design

---

## References

- Validation implementation: [file_controller.py](../../app/controllers/file_controller.py)
- Model serialization: [circuit.py](../../app/models/circuit.py)
- Tests: [test_file_controller.py](../../app/tests/unit/test_file_controller.py)
- Example circuits: [0-CDR-Demo/](../../0-CDR-Demo/)

---

## Review and Revision

This decision should be reviewed if:
- File sizes become problematic (>1MB for typical circuits)
- Parse performance becomes a bottleneck
- Need binary embedding (images, compiled models)
- Moving to database-backed storage

**Status:** Working well, widely adopted for circuit sharing
