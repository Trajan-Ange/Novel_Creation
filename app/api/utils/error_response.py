"""Standardized API error response format.

Replaces the three inconsistent patterns:
  1. {"success": False, "error": "..."}  (manual dict)
  2. HTTPException(status_code=..., detail=...)  (FastAPI built-in)
  3. SSE error event  (streaming)
"""

from typing import Any


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
