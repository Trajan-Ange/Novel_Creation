"""Pytest fixtures for Novel Creation tests."""

import os
import shutil
import sys
import tempfile

import pytest

# Add project root to path so app imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage.file_manager import FileManager
from main import app


@pytest.fixture
def temp_projects_root():
    """Create a temporary projects directory for isolated testing."""
    tmpdir = tempfile.mkdtemp(prefix="novel_test_")
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def fm(temp_projects_root):
    """Return a FileManager instance pointed at a temp directory."""
    return FileManager(temp_projects_root)


@pytest.fixture
def sample_project(fm):
    """Create a minimal test project."""
    fm.create_project("测试项目", "原创", "测试用项目")
    return "测试项目"


@pytest.fixture(autouse=True)
def setup_app_state(temp_projects_root):
    """Set up app.state.fm for API tests that use TestClient."""
    app.state.fm = FileManager(temp_projects_root)
    # Ensure app.state.llm is not None (some imports may reference it)
    if not hasattr(app.state, 'llm') or app.state.llm is None:
        app.state.llm = None
