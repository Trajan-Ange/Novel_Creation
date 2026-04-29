"""Knowledge sync and lore extraction API endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.api.utils.error_response import sanitize_error
from app.skills.knowledge_sync import run as knowledge_sync_run
from app.skills.lore_extract import run as lore_extract_run

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sync", tags=["sync"])


class SyncRequest(BaseModel):
    project: str
    volume: int = 1
    chapter: int = 1


class LoreExtractRequest(BaseModel):
    project: str
    source_name: str
    scope: list[str] = []
    custom_requirements: str = ""


@router.post("/{project}/trigger")
async def trigger_sync(request: Request, project: str, body: SyncRequest):
    """Manually trigger knowledge sync for a specific chapter."""
    llm = request.app.state.llm
    fm = request.app.state.fm

    chapter_content = fm.read_chapter(project, body.volume, body.chapter)
    if not chapter_content:
        raise HTTPException(status_code=404, detail={"success": False, "error": f"第{body.volume}卷第{body.chapter}章不存在"})

    result = {"success": False, "error": "同步未产生结果"}
    async for event in knowledge_sync_run(llm, fm, project, {
        "action": "sync",
        "volume": body.volume,
        "chapter": body.chapter,
        "chapter_content": chapter_content,
    }):
        if event["type"] == "result":
            result = event["result"]
    if not result.get("success"):
        logger.error(f"Sync failed: {result.get('error', 'unknown')}")
        result["error"] = sanitize_error(Exception(str(result.get("error", ""))))
    return result


@router.post("/{project}/lore-extract")
async def extract_lore(request: Request, project: str, body: LoreExtractRequest):
    """Extract and distill worldview from an existing IP (fan-fiction support)."""
    llm = request.app.state.llm
    fm = request.app.state.fm
    result = await lore_extract_run(llm, fm, project, {
        "action": "extract",
        "source_name": body.source_name,
        "scope": body.scope,
        "custom_requirements": body.custom_requirements,
    })
    if not result.get("success"):
        logger.error(f"Lore extract failed: {result.get('error', 'unknown')}")
        result["error"] = sanitize_error(Exception(str(result.get("error", ""))))
    return result
