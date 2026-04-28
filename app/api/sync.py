"""Knowledge sync and lore extraction API endpoints."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

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
    from app.skills.knowledge_sync import run
    llm = request.app.state.llm
    fm = request.app.state.fm

    chapter_content = fm.read_chapter(project, body.volume, body.chapter)
    if not chapter_content:
        raise HTTPException(status_code=404, detail={"success": False, "error": f"第{body.volume}卷第{body.chapter}章不存在"})

    result = {"success": False, "error": "同步未产生结果"}
    async for event in run(llm, fm, project, {
        "action": "sync",
        "volume": body.volume,
        "chapter": body.chapter,
        "chapter_content": chapter_content,
    }):
        if event["type"] == "result":
            result = event["result"]
    return result


@router.post("/{project}/lore-extract")
async def extract_lore(request: Request, project: str, body: LoreExtractRequest):
    """Extract and distill worldview from an existing IP (fan-fiction support)."""
    from app.skills.lore_extract import run
    llm = request.app.state.llm
    fm = request.app.state.fm
    result = await run(llm, fm, project, {
        "action": "extract",
        "source_name": body.source_name,
        "scope": body.scope,
        "custom_requirements": body.custom_requirements,
    })
    return result
