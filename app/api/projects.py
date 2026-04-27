"""Project CRUD API endpoints."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""
    type: str = "原创"
    source: str = ""


@router.get("")
async def list_projects(request: Request):
    return request.app.state.fm.list_projects()


@router.post("")
async def create_project(request: Request, body: CreateProjectRequest):
    fm = request.app.state.fm
    try:
        state = fm.create_project(body.name, body.type, body.source)
        return {"success": True, "project": state}
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail={"success": False, "error": str(e)})
    except ValueError as e:
        raise HTTPException(status_code=422, detail={"success": False, "error": str(e)})


@router.delete("/{name}")
async def delete_project(request: Request, name: str):
    request.app.state.fm.delete_project(name)
    return {"success": True}
