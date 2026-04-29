"""Unit tests for FileManager — no LLM dependency."""

import os
import pytest

from app.storage.file_manager import FileManager


class TestProjectCRUD:
    """Project create / list / delete."""

    def test_create_project(self, fm):
        fm.create_project("仙侠世界", "原创", "测试")
        names = [p["name"] for p in fm.list_projects()]
        assert "仙侠世界" in names

    def test_create_duplicate_project(self, fm):
        fm.create_project("测试", "原创", "")
        with pytest.raises(FileExistsError):
            fm.create_project("测试", "原创", "")

    def test_delete_project(self, fm):
        fm.create_project("待删除", "原创", "")
        fm.delete_project("待删除")
        names = [p["name"] for p in fm.list_projects()]
        assert "待删除" not in names

    def test_list_projects_empty(self, fm):
        assert fm.list_projects() == []

    def test_project_name_validation(self, fm):
        with pytest.raises(ValueError):
            fm.create_project("", "原创", "")
        with pytest.raises(ValueError):
            fm.create_project("name/with/slash", "原创", "")

    def test_project_state_read_write(self, fm, sample_project):
        state = fm.read_project_state(sample_project)
        assert isinstance(state, dict)
        fm.write_project_state(sample_project, {"volume_count": 1})
        state2 = fm.read_project_state(sample_project)
        assert state2["volume_count"] == 1


class TestSettingsCRUD:
    """World / Characters / Timeline / Relationship / Style read/write."""

    def test_write_and_read_world_setting(self, fm, sample_project):
        fm.write_world_setting(sample_project, "# 世界设定\n测试内容")
        content = fm.read_world_setting(sample_project)
        assert "世界设定" in content

    def test_read_world_setting_not_exists(self, fm, sample_project):
        assert fm.read_world_setting(sample_project) is None

    def test_write_and_read_character(self, fm, sample_project):
        fm.write_character(sample_project, "主角", "## 基本信息\n测试")
        content = fm.read_character(sample_project, "主角")
        assert "基本信息" in content

    def test_list_characters(self, fm, sample_project):
        fm.write_character(sample_project, "角色A", "内容")
        fm.write_character(sample_project, "角色B", "内容")
        chars = fm.list_characters(sample_project)
        assert "角色A" in chars
        assert "角色B" in chars

    def test_list_characters_filters_backup_files(self, fm, sample_project):
        fm.write_character(sample_project, "角色C", "内容")
        # Simulate a backup file
        backup_path = os.path.join(
            fm.projects_root, sample_project, "创作依据", "人物设定", "角色C---.md"
        )
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write("备份内容")
        chars = fm.list_characters(sample_project)
        assert "角色C" in chars
        assert "角色C---" not in chars

    def test_delete_character(self, fm, sample_project):
        fm.write_character(sample_project, "路人甲", "内容")
        fm.delete_character(sample_project, "路人甲")
        chars = fm.list_characters(sample_project)
        assert "路人甲" not in chars

    def test_character_name_validation(self, fm, sample_project):
        with pytest.raises(ValueError):
            fm.write_character(sample_project, "../escape", "内容")
        with pytest.raises(ValueError):
            fm.write_character(sample_project, "has/slash", "内容")

    def test_timeline_read_write(self, fm, sample_project):
        fm.write_background_timeline(sample_project, "# 背景时间线\n测试")
        fm.write_story_timeline(sample_project, "# 故事时间线\n测试")
        assert "背景时间线" in fm.read_background_timeline(sample_project)
        assert "故事时间线" in fm.read_story_timeline(sample_project)

    def test_relationship_read_write(self, fm, sample_project):
        fm.write_relationship(sample_project, "# 人物关系\n测试")
        assert "人物关系" in fm.read_relationship(sample_project)

    def test_style_guide_read_write(self, fm, sample_project):
        fm.write_style_guide(sample_project, "# 风格指南\n测试")
        assert "风格指南" in fm.read_style_guide(sample_project)

    def test_get_all_settings(self, fm, sample_project):
        fm.write_world_setting(sample_project, "世界")
        fm.write_character(sample_project, "角色1", "内容")
        fm.write_background_timeline(sample_project, "背景")
        fm.write_story_timeline(sample_project, "故事")
        docs = fm.get_all_settings(sample_project)
        titles = [d["title"] for d in docs]
        assert "世界设定" in titles
        assert "人物设定：角色1" in titles
        assert "背景时间线" in titles
        assert "故事时间线" in titles

    def test_get_all_settings_cache_invalidation(self, fm, sample_project):
        docs1 = fm.get_all_settings(sample_project)
        fm.write_character(sample_project, "新角色", "内容")
        docs2 = fm.get_all_settings(sample_project)
        assert docs1 != docs2  # Cache should be invalidated after write


class TestOutlineCRUD:
    """Book / Volume / Chapter outline read/write."""

    def test_book_outline(self, fm, sample_project):
        fm.write_book_outline(sample_project, "# 全书大纲\n测试")
        content = fm.read_book_outline(sample_project)
        assert "全书大纲" in content

    def test_volume_outline(self, fm, sample_project):
        fm.write_volume_outline(sample_project, 1, "# 第一卷\n测试")
        content = fm.read_volume_outline(sample_project, 1)
        assert "第一卷" in content
        assert 1 in fm.list_volume_outlines(sample_project)

    def test_chapter_outline(self, fm, sample_project):
        fm.ensure_volume_dir(sample_project, 1)
        fm.write_chapter_outline(sample_project, 1, 1, "# 第一章大纲\n测试")
        content = fm.read_chapter_outline(sample_project, 1, 1)
        assert "第一章大纲" in content

    def test_book_outline_not_exists(self, fm, sample_project):
        assert fm.read_book_outline(sample_project) is None


class TestChapterCRUD:
    """Chapter content read/write."""

    def test_write_and_read_chapter(self, fm, sample_project):
        fm.write_chapter(sample_project, 1, 1, "第一章正文内容")
        content = fm.read_chapter(sample_project, 1, 1)
        assert "第一章正文内容" == content

    def test_list_chapters(self, fm, sample_project):
        fm.write_chapter(sample_project, 1, 1, "正文1")
        fm.write_chapter(sample_project, 1, 2, "正文2")
        chaps = fm.list_chapters(sample_project, 1)
        assert 1 in chaps
        assert 2 in chaps

    def test_read_chapter_not_exists(self, fm, sample_project):
        assert fm.read_chapter(sample_project, 1, 99) is None
