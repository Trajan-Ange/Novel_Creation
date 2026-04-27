"""SSE streaming helpers shared across API endpoints."""
import json

from fastapi import Request


def create_sse_sender():
    """Return a send() closure for SSE event streaming.

    Usage:
        send = create_sse_sender()
        yield send("status", {"message": "processing..."})
        yield send("text_chunk", {"text": chunk})
    """
    def send(event_type: str, data: dict = None):
        payload = {"type": event_type}
        if data:
            payload.update(data)
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
    return send


async def check_disconnected(request: Request) -> bool:
    """Return True if the SSE client has disconnected."""
    return await request.is_disconnected()
