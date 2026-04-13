"""Atomic file write utility for crash-safe persistence.

Writes data to a temporary file in the same directory, then atomically
replaces the target file via ``os.replace()``.  This ensures the target
file is never left in a partially-written state after a crash or power loss.
"""

import os
import tempfile
from pathlib import Path


def atomic_write_text(filepath, content: str, encoding: str = "utf-8", newline=None) -> None:
    """Atomically write *content* to *filepath*.

    Creates a temporary file in the same directory as *filepath*,
    writes *content* to it, then atomically replaces *filepath*.
    On failure, the temporary file is removed.

    Args:
        filepath: Target file path (str or Path).
        content: Text content to write.
        encoding: Text encoding (default utf-8).
        newline: Newline translation mode (passed to open). Use ``""``
            for CSV files to prevent ``\\r\\n`` doubling on Windows.

    Raises:
        OSError: If the write or replace fails.
    """
    filepath = Path(filepath)
    fd, tmp = tempfile.mkstemp(dir=filepath.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline=newline) as f:
            f.write(content)
        os.replace(tmp, filepath)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
