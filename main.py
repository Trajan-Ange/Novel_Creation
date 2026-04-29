"""Novel Creation & Management System — FastAPI entry point."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.utils.error_response import sanitize_error
from app.services.llm import LLMService, load_config
from app.storage.file_manager import FileManager

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
PROJECTS_ROOT = os.path.join(BASE_DIR, "projects")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    config = load_config(CONFIG_PATH)
    app.state.llm = LLMService(config)
    app.state.fm = FileManager(PROJECTS_ROOT)
    app.state.config_path = CONFIG_PATH
    yield


app = FastAPI(title="小说创作管理系统", lifespan=lifespan)

_default_origins = [
    "http://127.0.0.1:8000", "http://localhost:8000",
    "http://127.0.0.1:3000", "http://localhost:3000",
]
_cors_env = os.environ.get("NOVEL_CORS_ORIGINS")
if _cors_env:
    _default_origins.extend(o.strip() for o in _cors_env.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return sanitized error responses."""
    logger.error(f"Unhandled error: {type(exc).__name__}: {exc}", exc_info=True)
    sanitized = sanitize_error(exc)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": sanitized, "code": "INTERNAL_ERROR"},
    )


# Register API routers
from app.api.config import router as config_router
from app.api.projects import router as projects_router
from app.api.settings import router as settings_router
from app.api.outline import router as outline_router
from app.api.chapters import router as chapters_router
from app.api.sync import router as sync_router

app.include_router(config_router)
app.include_router(projects_router)
app.include_router(settings_router)
app.include_router(outline_router)
app.include_router(chapters_router)
app.include_router(sync_router)

# Serve static files — mount specific dirs, NOT root (avoids catching API routes)
static_dir = os.path.join(BASE_DIR, "app", "static")
if os.path.exists(static_dir):
    app.mount("/js", StaticFiles(directory=os.path.join(static_dir, "js")), name="js")
    app.mount("/css", StaticFiles(directory=os.path.join(static_dir, "css")), name="css")

    # SPA catch-all: serve index.html for any unmatched GET (must be last)
    from fastapi.responses import FileResponse
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"detail": "Not Found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
