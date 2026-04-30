"""Novel Creation & Management System — FastAPI entry point."""

import logging
import os
import sys
import json
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.utils.error_response import sanitize_error
from app.services.llm import LLMService, load_config
from app.storage.file_manager import FileManager

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _is_frozen() -> bool:
    """Detect whether running as a PyInstaller-frozen executable."""
    return getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS')


def _get_user_data_dir() -> str:
    """Return the user data directory for config and projects.

    Windows: %APPDATA%/NovelCreation/
    Linux/macOS: ~/.novel/
    """
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
        return os.path.join(base, 'NovelCreation')
    return os.path.expanduser('~/.novel')


def _get_config_path() -> str:
    """Return config.json path. In frozen mode, uses user data dir."""
    if _is_frozen():
        user_dir = _get_user_data_dir()
        os.makedirs(user_dir, exist_ok=True)
        user_config = os.path.join(user_dir, 'config.json')
        # Auto-migrate config from project root on first frozen launch
        bundled_config = os.path.join(BASE_DIR, 'config.json')
        if not os.path.exists(user_config) and os.path.exists(bundled_config):
            try:
                shutil.copy2(bundled_config, user_config)
                logger.info(f"Migrated config to {user_config}")
            except OSError:
                pass
        return user_config
    return os.path.join(BASE_DIR, 'config.json')


def _get_projects_root() -> str:
    """Return projects directory. In frozen mode, uses user data dir."""
    if _is_frozen():
        user_dir = _get_user_data_dir()
        projects_dir = os.path.join(user_dir, 'projects')
        os.makedirs(projects_dir, exist_ok=True)
        return projects_dir
    return os.path.join(BASE_DIR, 'projects')


def _get_static_dir() -> str:
    """Return static files directory. In frozen mode, resolved via sys._MEIPASS."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'app', 'static')
    return os.path.join(BASE_DIR, 'app', 'static')


def _check_single_instance(port: int = 8000) -> bool:
    """Check if another instance is already running on the given port.
    Returns True if port is available, False if already in use.
    """
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect(('127.0.0.1', port))
        s.close()
        return False
    except (socket.timeout, ConnectionRefusedError, OSError):
        return True


CONFIG_PATH = _get_config_path()
PROJECTS_ROOT = _get_projects_root()
STATIC_DIR = _get_static_dir()

IS_PRODUCTION = os.environ.get('NOVEL_ENV', '').lower() == 'production'


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_level = logging.WARNING if IS_PRODUCTION else logging.INFO
    logging.basicConfig(
        level=log_level,
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
if os.path.exists(STATIC_DIR):
    app.mount("/js", StaticFiles(directory=os.path.join(STATIC_DIR, "js")), name="js")
    app.mount("/css", StaticFiles(directory=os.path.join(STATIC_DIR, "css")), name="css")

    # Vendor directory (marked.js, etc.)
    vendor_dir = os.path.join(STATIC_DIR, "vendor")
    if os.path.exists(vendor_dir):
        app.mount("/vendor", StaticFiles(directory=vendor_dir), name="vendor")

    # SPA catch-all: serve index.html for any unmatched GET (must be last)
    from fastapi.responses import FileResponse
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"detail": "Not Found"}


if __name__ == "__main__":
    import uvicorn

    if not _check_single_instance(8000):
        print("ERROR: Another instance is already running on port 8000.")
        print("Close the existing instance first, or visit http://127.0.0.1:8000")
        sys.exit(1)

    reload = not IS_PRODUCTION and not _is_frozen()
    log_level = "warning" if (IS_PRODUCTION or _is_frozen()) else "info"

    if _is_frozen():
        # Desktop mode: start server in background thread, open native window
        import threading, time
        config = uvicorn.Config(
            app=app, host="127.0.0.1", port=8000,
            log_level=log_level, reload=False,
        )
        server = uvicorn.Server(config)

        t = threading.Thread(target=server.run, daemon=True)
        t.start()

        # Wait briefly for the server to be ready
        time.sleep(1)

        import webview
        window = webview.create_window(
            "小说创作管理系统 v0.3.0",
            "http://127.0.0.1:8000",
            width=1280, height=800,
            min_size=(900, 600),
        )
        webview.start()

        # Clean up when window closes
        server.should_exit = True
        sys.exit(0)
    else:
        # Dev mode: standard uvicorn server with browser access
        print(f"Novel Creation System v0.3.0")
        print(f"Open http://127.0.0.1:8000 in your browser")
        uvicorn.run(
            "main:app",
            host="127.0.0.1",
            port=8000,
            reload=reload,
            log_level=log_level,
        )
