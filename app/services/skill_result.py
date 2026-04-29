"""Unified return type for all skill run() functions.

A dict subclass so existing result["success"] access continues to work,
while also supporting result.success / result.content attribute access.
"""


class SkillResult(dict):
    """Unified skill execution result — dict subclass for backward compatibility.

    Usage:
        # Construction
        SkillResult(success=True, content="...", data={"json": ...})
        SkillResult(success=False, error="something went wrong")

        # Dict access (backward compatible)
        result["success"]  → True
        result["content"]  → "..."

        # Attribute access (new, preferred)
        result.success     → True
        result.content     → "..."
        result.data        → {"json": ...}
    """

    def __init__(self, success: bool, content: str | None = None,
                 data: dict | None = None, error: str | None = None, **kwargs):
        super().__init__(success=success)
        if content is not None:
            self["content"] = content
        if data is not None:
            self["data"] = data
        if error is not None:
            self["error"] = error
        # Merge any extra keyword keys (for timeline's background/story etc.)
        for k, v in kwargs.items():
            self[k] = v

    @property
    def success(self) -> bool:
        return self.get("success", False)

    @property
    def content(self) -> str | None:
        return self.get("content")

    @property
    def data(self) -> dict | None:
        return self.get("data")

    @property
    def error(self) -> str | None:
        return self.get("error")
