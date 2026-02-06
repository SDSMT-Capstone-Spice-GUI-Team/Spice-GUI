"""
Tests for model serialization round-trips (to_dict / from_dict).

Tests ComponentData and WireData without any Qt dependencies.
"""
import json
import pytest
from models.component import (
    ComponentData, COMPONENT_TYPES, DEFAULT_VALUES,
    _CLASS_TO_DISPLAY, _DISPLAY_TO_CLASS,
)
from models.wire import WireData
from tests.conftest import make_component, make_wire


# ── ComponentData round-trip ─────────────────────────────────────────

class TestComponentRoundTrip:

    @pytest.mark.parametrize("comp_type", [
        'Resistor', 'Capacitor', 'Inductor',
        'Voltage Source', 'Current Source', 'Ground', 'Op-Amp',
        'VCVS', 'CCVS', 'VCCS', 'CCCS',
    ])
    def test_round_trip_preserves_all_fields(self, comp_type):
        original = ComponentData(
            component_id='X1',
            component_type=comp_type,
            value=DEFAULT_VALUES.get(comp_type, '1'),
            position=(42.0, -17.5),
            rotation=90,
        )
        data = original.to_dict()
        restored = ComponentData.from_dict(data)

        assert restored.component_id == original.component_id
        assert restored.component_type == original.component_type
        assert restored.value == original.value
        assert restored.position == original.position
        assert restored.rotation == original.rotation

    def test_json_serializable(self):
        comp = make_component('Resistor', 'R1', '10k', (50.0, 25.0))
        data = comp.to_dict()
        json_str = json.dumps(data)
        restored_data = json.loads(json_str)
        restored = ComponentData.from_dict(restored_data)
        assert restored.component_id == 'R1'
        assert restored.value == '10k'


class TestWaveformSourceRoundTrip:

    def test_waveform_params_preserved(self):
        comp = ComponentData(
            component_id='VW1',
            component_type='Waveform Source',
            value='SIN(0 5 1k 0 0 0)',
            position=(0.0, 0.0),
        )
        comp.waveform_type = 'SIN'
        comp.waveform_params['SIN']['amplitude'] = '10'

        data = comp.to_dict()
        restored = ComponentData.from_dict(data)

        assert restored.waveform_type == 'SIN'
        assert restored.waveform_params['SIN']['amplitude'] == '10'

    def test_waveform_default_params_initialized(self):
        comp = ComponentData(
            component_id='VW1',
            component_type='Waveform Source',
            value='SIN(0 5 1k)',
            position=(0.0, 0.0),
        )
        assert comp.waveform_type == 'SIN'
        assert 'SIN' in comp.waveform_params
        assert 'PULSE' in comp.waveform_params


# ── Type name mapping ────────────────────────────────────────────────

class TestTypeNameMapping:

    @pytest.mark.parametrize("class_name, display_name", [
        ('VoltageSource', 'Voltage Source'),
        ('CurrentSource', 'Current Source'),
        ('WaveformVoltageSource', 'Waveform Source'),
        ('OpAmp', 'Op-Amp'),
        ('VoltageControlledVoltageSource', 'VCVS'),
        ('CurrentControlledVoltageSource', 'CCVS'),
        ('VoltageControlledCurrentSource', 'VCCS'),
        ('CurrentControlledCurrentSource', 'CCCS'),
    ])
    def test_old_class_names_load_correctly(self, class_name, display_name):
        data = {
            'type': class_name,
            'id': 'X1',
            'value': '1',
            'pos': {'x': 0, 'y': 0},
            'rotation': 0,
        }
        comp = ComponentData.from_dict(data)
        assert comp.component_type == display_name

    def test_display_names_load_directly(self):
        data = {
            'type': 'Resistor',
            'id': 'R1',
            'value': '1k',
            'pos': {'x': 0, 'y': 0},
        }
        comp = ComponentData.from_dict(data)
        assert comp.component_type == 'Resistor'


# ── WireData round-trip ──────────────────────────────────────────────

class TestWireRoundTrip:

    def test_basic_round_trip(self):
        wire = WireData(
            start_component_id='R1',
            start_terminal=0,
            end_component_id='V1',
            end_terminal=1,
        )
        data = wire.to_dict()
        restored = WireData.from_dict(data)

        assert restored.start_component_id == 'R1'
        assert restored.start_terminal == 0
        assert restored.end_component_id == 'V1'
        assert restored.end_terminal == 1

    def test_json_serializable(self):
        wire = make_wire('R1', 0, 'C1', 1)
        json_str = json.dumps(wire.to_dict())
        restored = WireData.from_dict(json.loads(json_str))
        assert restored.start_component_id == 'R1'
        assert restored.end_component_id == 'C1'

    def test_connects_component(self):
        wire = make_wire('R1', 0, 'V1', 1)
        assert wire.connects_component('R1')
        assert wire.connects_component('V1')
        assert not wire.connects_component('C1')

    def test_connects_terminal(self):
        wire = make_wire('R1', 0, 'V1', 1)
        assert wire.connects_terminal('R1', 0)
        assert wire.connects_terminal('V1', 1)
        assert not wire.connects_terminal('R1', 1)


# ── Full circuit dict round-trip ─────────────────────────────────────

class TestCircuitDictRoundTrip:

    def test_components_and_wires(self):
        """Simulate the dict structure from CircuitCanvas.to_dict()."""
        components = [
            make_component('Voltage Source', 'V1', '5V', (0, 0)),
            make_component('Resistor', 'R1', '1k', (100, 0)),
            make_component('Ground', 'GND1', '0V', (100, 100)),
        ]
        wires = [
            make_wire('V1', 0, 'R1', 0),
            make_wire('R1', 1, 'GND1', 0),
            make_wire('V1', 1, 'GND1', 0),
        ]

        # Serialize
        circuit_data = {
            'components': [c.to_dict() for c in components],
            'wires': [w.to_dict() for w in wires],
        }

        # JSON round-trip
        json_str = json.dumps(circuit_data)
        loaded = json.loads(json_str)

        # Deserialize
        restored_comps = [ComponentData.from_dict(c) for c in loaded['components']]
        restored_wires = [WireData.from_dict(w) for w in loaded['wires']]

        assert len(restored_comps) == 3
        assert len(restored_wires) == 3

        # Verify component types preserved
        types = {c.component_type for c in restored_comps}
        assert 'Voltage Source' in types
        assert 'Resistor' in types
        assert 'Ground' in types

        # Verify wire connections preserved
        assert restored_wires[0].start_component_id == 'V1'
        assert restored_wires[0].end_component_id == 'R1'
