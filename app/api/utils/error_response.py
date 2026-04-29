"""Standardized API error response utilities.

Provides sanitize_error() for stripping internal paths and stack traces
from exception messages before sending to clients.
"""

import re
from typing import Any


def sanitize_error(error: Exception) -> str:
    """Strip internal paths and stack traces from error messages.
    Keeps the exception type name and first meaningful sentence."""
    msg = str(error)
    if not msg:
        return type(error).__name__
    # Strip absolute Windows and Unix paths
    msg = re.sub(r'[A-Za-z]:[\\/](?:\S+[\\/])*\S+\.py', '[path]', msg)
    msg = re.sub(r'/[^\s]*\.py(:\d+)?', '[path]', msg)
    # Truncate multi-line (stack traces)
    if "\n" in msg:
        msg = msg.split("\n")[0].strip()
    return msg
