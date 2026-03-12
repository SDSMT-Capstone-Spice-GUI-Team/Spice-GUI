"""
Integration-test fixtures.

The session-scoped ``require_ngspice`` guard automatically skips every test
in this package when ngspice is not available on the PATH.
"""

import shutil

import pytest


# AUDIT(testing): require_ngspice guard also skips test_save_load.py and non-ngspice tests in test_phase4_mvc_integration.py; move those files to unit/ or use per-file skip markers so they run without ngspice
@pytest.fixture(scope="session", autouse=True)
def require_ngspice():
    if shutil.which("ngspice") is None:
        pytest.skip("ngspice not installed", allow_module_level=True)
