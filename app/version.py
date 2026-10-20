"""Application version.

This module is the single source of truth for the running version used by both the
GUI entrypoint (:mod:`main`) and the command-line interface (:mod:`cli`).  Keep
``__version__`` in sync with the ``version`` field in :file:`pyproject.toml`
(the uv project's declared version).
"""

__version__ = "0.1.0"
