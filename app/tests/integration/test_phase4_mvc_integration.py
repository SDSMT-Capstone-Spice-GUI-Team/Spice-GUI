"""
Integration tests for MVC that require ngspice.

Non-ngspice tests have been moved to app/tests/unit/test_phase4_mvc.py
as part of #772 to avoid silent CI skips.
"""

import pytest
from controllers.simulation_controller import SimulationController
from models.circuit import CircuitModel
from models.component import ComponentData


class TestMVCSimulationWithNgspice:
    """Tests that actually invoke the ngspice simulation engine."""

    @pytest.mark.ngspice
    def test_simulation_validation_errors(self):
        """Test that simulation validation errors are captured"""
        # Create invalid circuit (no ground)
        model = CircuitModel()
        model.components = {"R1": ComponentData("R1", "Resistor", "1k", (0, 0))}
        model.analysis_type = "DC Operating Point"

        sim_ctrl = SimulationController(model)

        # Run simulation (should fail validation)
        result = sim_ctrl.run_simulation()

        # Verify validation error is reported
        assert result.success is False or len(result.errors) > 0
