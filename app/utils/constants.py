"""
utils/constants.py

Application-wide constants that are independent of any specific layer.

Constants that belong here are those needed by more than one layer
(e.g. both simulation and GUI) and have no dependency on Qt or other
layer-specific packages.
"""

# Simulation settings
SIMULATION_TIMEOUT = 60  # Seconds before ngspice is killed
