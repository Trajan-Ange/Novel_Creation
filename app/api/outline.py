"""Outline generation API endpoints."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.skills.outline import run as outline_skill_run

router = APIRouter(prefix="/api/outline", tags=["outline"])


class OutlineGenerateRequest(BaseModel):
    project: str
    level: str = "book"  # book, volume, chapter
    volume: int = 1
    chapter: int = 1
    instruction: str = ""


class OutlineSaveRequest(BaseModel):
    project: str
    content: str


@router.get("/{project}/book")
async def get_book_outline(request: Request, project: str):
    content = request.app.state.fm.read_book_outline(project)
    return {"content": content or ""}


@router.put("/{project}/book")
async def save_book_outline(request: Request, project: str, body: OutlineSaveRequest):
    request.app.state.fm.write_book_outline(project, body.content)
    return {"success": True}


@router.post("/{project}/book/generate")
async def generate_book_outline(request: Request, project: str, body: OutlineGenerateRequest):
    llm = request.app.state.llm
    fm = request.app.state.fm
    result = await outline_skill_run(llm, fm, project, {
        "action": "create_book",
        "instruction": body.instruction,
    })
    if result.get("success"):
        fm.write_book_outline(project, result["content"])
    return result


@router.get("/{project}/volume/{volume}")
async def get_volume_outline(request: Request, project: str, volume: int):
    content = request.app.state.fm.read_volume_outline(project, volume)
    return {"content": content or "", "volume": volume}


@router.put("/{project}/volume/{volume}")
async def save_volume_outline(request: Request, project: str, volume: int, body: OutlineSaveRequest):
    request.app.state.fm.write_volume_outline(project, volume, body.content)
    return {"success": True}


@router.post("/{project}/volume/{volume}/generate")
async def generate_volume_outline(request: Request, project: str, volume: int, body: OutlineGenerateRequest):
    llm = request.app.state.llm
    fm = request.app.state.fm
    result = await outline_skill_run(llm, fm, project, {
        "action": "create_volume",
        "volume": volume,
        "instruction": body.instruction,
    })
    if result.get("success"):
        fm.write_volume_outline(project, volume, result["content"])
    return result


@router.get("/{project}/volume/{volume}/chapter/{chapter}")
async def get_chapter_outline(request: Request, project: str, volume: int, chapter: int):
    content = request.app.state.fm.read_chapter_outline(project, volume, chapter)
    return {"content": content or "", "volume": volume, "chapter": chapter}


@router.put("/{project}/volume/{volume}/chapter/{chapter}")
async def save_chapter_outline(request: Request, project: str, volume: int, chapter: int, body: OutlineSaveRequest):
    fm = request.app.state.fm
    fm.ensure_volume_dir(project, volume)
    fm.write_chapter_outline(project, volume, chapter, body.content)
    return {"success": True}


@router.post("/{project}/volume/{volume}/chapter/{chapter}/generate")
async def generate_chapter_outline(request: Request, project: str, volume: int, chapter: int, body: OutlineGenerateRequest):
    llm = request.app.state.llm
    fm = request.app.state.fm
    fm.ensure_volume_dir(project, volume)
    result = await outline_skill_run(llm, fm, project, {
        "action": "create_chapter",
        "volume": volume,
        "chapter": chapter,
        "instruction": body.instruction,
    })
    if result.get("success"):
        fm.write_chapter_outline(project, volume, chapter, result["content"])
    return result


@router.get("/{project}/volumes")
async def list_volumes(request: Request, project: str):
    vols = request.app.state.fm.list_volume_outlines(project)
    return {"volumes": vols}


@router.get("/{project}/volume/{volume}/chapters")
async def list_chapter_outlines(request: Request, project: str, volume: int):
    chaps = request.app.state.fm.list_chapter_outlines(project, volume)
    return {"chapters": chaps}
