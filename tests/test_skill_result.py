"""Unit tests for SkillResult dict subclass."""

import pytest
from app.services.skill_result import SkillResult


class TestSkillResultSuccess:
    def test_dict_access(self):
        result = SkillResult(success=True, content="Hello")
        assert result["success"] is True
        assert result["content"] == "Hello"

    def test_attribute_access(self):
        result = SkillResult(success=True, content="World", data={"json": {"k": "v"}})
        assert result.success is True
        assert result.content == "World"
        assert result.data == {"json": {"k": "v"}}

    def test_error_access(self):
        result = SkillResult(success=False, error="Something broke")
        assert result.success is False
        assert result.error == "Something broke"
        assert result.content is None

    def test_extra_kwargs_merged_as_dict_items(self):
        result = SkillResult(success=True, content="X", background="Bg", story="St")
        assert result["background"] == "Bg"
        assert result["story"] == "St"

    def test_missing_fields_return_none(self):
        result = SkillResult(success=True)
        assert result.content is None
        assert result.data is None
        assert result.error is None

    def test_falsy_success(self):
        result = SkillResult(success=False)
        assert result.success is False
        assert bool(result.success) is False
