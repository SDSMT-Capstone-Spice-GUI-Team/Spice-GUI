"""
Integration-test fixtures.

The session-scoped ``require_ngspice`` guard automatically skips every test
in this package when ngspice is not available on the PATH.
"""

import shutil

import pytest


@pytest.fixture(scope="session", autouse=True)
def require_ngspice():
    if shutil.which("ngspice") is None:
        pytest.skip("ngspice not installed", allow_module_level=True)
