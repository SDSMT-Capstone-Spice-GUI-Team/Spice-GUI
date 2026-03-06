"""
Smoke test: run a trivial DC netlist through NgspiceRunner and verify success.
"""

import os
import tempfile

import pytest
from simulation.ngspice_runner import NgspiceRunner


@pytest.mark.ngspice
class TestNgspiceSmoke:
    def test_dc_resistor_netlist(self):
        """NgspiceRunner should complete a simple V-R-GND DC operating-point sim."""
        netlist = "* DC smoke test\nV1 1 0 DC 5\nR1 1 0 1k\n.op\n.end\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            runner = NgspiceRunner(output_dir=tmpdir)
            success, output_file, stdout, stderr = runner.run_simulation(netlist)

            assert success, f"ngspice failed: {stderr}"
            assert output_file is not None
            assert os.path.isfile(output_file)
