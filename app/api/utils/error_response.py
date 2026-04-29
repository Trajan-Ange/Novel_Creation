"""Standardized API error response format.

Replaces the three inconsistent patterns:
  1. {"success": False, "error": "..."}  (manual dict)
  2. HTTPException(status_code=..., detail=...)  (FastAPI built-in)
  3. SSE error event  (streaming)
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


def error_response(message: str, code: str = "", status_code: int = 400) -> dict[str, Any]:
    """Return a standardized error dict for non-streaming endpoints."""
    resp: dict[str, Any] = {"success": False, "error": message}
    if code:
        resp["code"] = code
    return resp


def http_error_detail(message: str, code: str = "") -> dict[str, Any]:
    """Return a standardized detail dict for use with HTTPException."""
    detail: dict[str, Any] = {"success": False, "error": message}
    if code:
        detail["code"] = code
    return detail


def sse_error(message: str, code: str = "") -> dict[str, Any]:
    """Return a standardized SSE error event payload."""
    payload: dict[str, Any] = {"type": "error", "message": message}
    if code:
        payload["code"] = code
    return payload
