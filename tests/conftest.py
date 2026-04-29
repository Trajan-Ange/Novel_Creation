"""Pytest fixtures for Novel Creation tests."""

import os
import shutil
import sys
import tempfile
from unittest.mock import AsyncMock

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
    if not hasattr(app.state, 'llm') or app.state.llm is None:
        app.state.llm = None


class MockLLMService:
    """Simulates LLMService for skill unit tests."""

    def __init__(self, preset_response: str = "Test response",
                 preset_json: dict | None = None):
        self.preset_response = preset_response
        self.preset_json = preset_json
        self.call_count = 0
        self.last_call = None

    async def chat_with_context_and_json(
        self, system_prompt: str = "",
        context_docs: list | None = None,
        user_message: str = "",
        **kwargs
    ) -> dict:
        self.call_count += 1
        self.last_call = {
            "system_prompt": system_prompt,
            "context_docs": context_docs or [],
            "user_message": user_message,
        }
        result = {"content": self.preset_response}
        if self.preset_json is not None:
            result["json"] = self.preset_json
        return result


@pytest.fixture
def mock_llm():
    """Return a MockLLMService with default response."""
    return MockLLMService()


@pytest.fixture
def mock_llm_with_json():
    """Return a MockLLMService that also returns JSON."""
    return MockLLMService(
        preset_response="## 测试响应\n\n测试内容。",
        preset_json={"terms": ["灵气", "修炼"], "concepts": ["修仙"]},
    )
