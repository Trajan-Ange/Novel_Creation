"""Unit tests for world_design skill."""

import pytest
from app.skills.world_design import run as world_design_run
from tests.conftest import MockLLMService


class TestWorldDesignCreate:
    @pytest.mark.asyncio
    async def test_create_returns_content(self, fm, sample_project):
        llm = MockLLMService(preset_response="## 世界背景\n\n测试世界设定内容。")
        result = await world_design_run(llm, fm, sample_project, {
            "action": "create",
            "instruction": "创建一个修仙世界",
        })
        assert result.success is True
        assert "测试世界设定内容" in result.content

    @pytest.mark.asyncio
    async def test_create_passes_instruction_to_llm(self, fm, sample_project):
        llm = MockLLMService()
        await world_design_run(llm, fm, sample_project, {
            "action": "create",
            "instruction": "设计魔法学院世界",
        })
        assert "设计魔法学院世界" in llm.last_call["user_message"]

    @pytest.mark.asyncio
    async def test_update_with_existing_content(self, fm, sample_project):
        llm = MockLLMService(preset_response="## 世界背景\n\n更新后的内容。")
        result = await world_design_run(llm, fm, sample_project, {
            "action": "update",
            "instruction": "添加新宗门",
            "existing_content": "## 世界背景\n\n旧内容。",
        })
        assert result.success is True
        assert len(llm.last_call["context_docs"]) == 1
        assert llm.last_call["context_docs"][0]["title"] == "当前世界设定（需要更新）"

    @pytest.mark.asyncio
    async def test_query_with_instruction(self, fm, sample_project):
        llm = MockLLMService(preset_response="灵气是这个世界的基础能量。")
        result = await world_design_run(llm, fm, sample_project, {
            "action": "query",
            "instruction": "灵气是什么？",
        })
        assert result.success is True
        assert "灵气是什么" in llm.last_call["user_message"]

    @pytest.mark.asyncio
    async def test_llm_error_returns_failure(self, fm, sample_project):
        llm = MockLLMService()
        original = llm.chat_with_context_and_json

        async def _raise(*args, **kwargs):
            raise RuntimeError("LLM timeout")

        llm.chat_with_context_and_json = _raise
        result = await world_design_run(llm, fm, sample_project, {
            "action": "create",
            "instruction": "测试",
        })
        assert result.success is False
        assert "LLM timeout" in result.error
