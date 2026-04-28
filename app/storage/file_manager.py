"""File-based storage manager.

All file I/O flows through this module. Handles directory creation,
path validation, markdown read/write, JSON serialization, and keyword search.
"""

import json
import os
import re
from datetime import datetime
from typing import Optional


class FileManager:
    """Manages all file operations for novel projects."""

    def __init__(self, projects_root: str):
        self.projects_root = os.path.abspath(projects_root)
        os.makedirs(self.projects_root, exist_ok=True)

    def _project_path(self, name: str) -> str:
        raw = os.path.join(self.projects_root, name)
        return self._validate_path(raw)

    def _validate_name(self, name: str):
        """Project names: alphanumeric, underscores, Chinese characters, spaces."""
        if not name or not re.match(r'^[\w一-鿿\s\-]+$', name):
            raise ValueError(f"Invalid project name: {name}")

    def _validate_char_name(self, name: str):
        """Character names: must not contain path separators or special filesystem chars."""
        if not name or not re.match(r'^[^\x00-\x1f\\/:*?"<>|]+$', name):
            raise ValueError(f"Invalid character name: {name}")
        if len(name) > 100:
            raise ValueError("Character name too long (max 100 characters)")

    def _validate_path(self, path: str) -> str:
        """Resolve real path and verify it stays under projects_root.
        Prevents symlink and directory traversal attacks.
        """
        real = os.path.realpath(path)
        root_real = os.path.realpath(self.projects_root)
        if os.path.commonpath([real, root_real]) != root_real:
            raise ValueError(f"Path traversal detected: {path}")
        return real

    def _read_file(self, path: str) -> Optional[str]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return None

    def _write_file(self, path: str, content: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)

    def _read_json(self, path: str) -> dict:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _write_json(self, path: str, data: dict):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

    # ── Project lifecycle ──────────────────────────────────────

    def create_project(self, name: str, proj_type: str = "原创", source: str = "") -> dict:
        self._validate_name(name)
        proj_path = self._project_path(name)
        if os.path.exists(proj_path):
            raise FileExistsError(f"Project '{name}' already exists.")

        dirs = [
            "创作依据/人物设定",
            "创作依据/时间线",
            "大纲/第一卷/章节大纲",
            "正文/第一卷",
            "伏笔管理/伏笔详情",
            "版本历史",
        ]
        for d in dirs:
            os.makedirs(os.path.join(proj_path, d), exist_ok=True)

        state = {
            "项目名称": name,
            "创作类型": proj_type,
            "源作品信息": source if proj_type == "二创" else None,
            "当前进度": {"当前卷": 1, "当前章": 0, "总卷数": None, "总章数": None},
            "阶段": "初次创建",
            "创作模式": "交互式",
            "待回收伏笔": [],
            "创作依据版本": {
                "世界设定": "v1.0",
                "人物设定": "v1.0",
                "时间线": "v1.0",
                "人物关系": "v1.0",
                "风格指南": "v1.0",
            },
            "最近更新时间": datetime.now().isoformat(),
            "创建时间": datetime.now().isoformat(),
        }
        self.save_project_state(name, state)
        return state

    def list_projects(self) -> list[dict]:
        projects = []
        if not os.path.exists(self.projects_root):
            return projects
        for name in os.listdir(self.projects_root):
            proj_path = self._project_path(name)
            if os.path.isdir(proj_path):
                state = self.get_project_state(name)
                projects.append({
                    "name": name,
                    "type": state.get("创作类型", "原创"),
                    "stage": state.get("阶段", ""),
                    "volume": state.get("当前进度", {}).get("当前卷", 1),
                    "chapter": state.get("当前进度", {}).get("当前章", 0),
                    "updated": state.get("最近更新时间", ""),
                })
        return sorted(projects, key=lambda p: p.get("updated", ""), reverse=True)

    def delete_project(self, name: str) -> None:
        import shutil
        self._validate_name(name)
        proj_path = self._project_path(name)
        if os.path.exists(proj_path):
            try:
                shutil.rmtree(proj_path)
            except OSError as e:
                raise RuntimeError(f"无法删除项目 '{name}'：{e}")

    def get_project_state(self, name: str) -> dict:
        path = os.path.join(self._project_path(name), "项目状态.json")
        return self._read_json(path)

    def save_project_state(self, name: str, state: dict):
        state["最近更新时间"] = datetime.now().isoformat()
        path = os.path.join(self._project_path(name), "项目状态.json")
        self._write_json(path, state)

    # ── Settings read/write ────────────────────────────────────

    def _settings_path(self, project: str, subpath: str) -> str:
        return os.path.join(self._project_path(project), "创作依据", subpath)

    def read_world_setting(self, project: str) -> Optional[str]:
        return self._read_file(self._settings_path(project, "世界设定.md"))

    def write_world_setting(self, project: str, content: str):
        self._write_file(self._settings_path(project, "世界设定.md"), content)

    def read_character(self, project: str, char_name: str) -> Optional[str]:
        self._validate_char_name(char_name)
        return self._read_file(self._settings_path(project, f"人物设定/{char_name}.md"))

    def write_character(self, project: str, char_name: str, content: str):
        self._validate_char_name(char_name)
        self._write_file(self._settings_path(project, f"人物设定/{char_name}.md"), content)

    def list_characters(self, project: str) -> list[str]:
        chars_dir = self._settings_path(project, "人物设定")
        if not os.path.exists(chars_dir):
            return []
        return [
            f.replace(".md", "")
            for f in os.listdir(chars_dir)
            if f.endswith(".md")
        ]

    def delete_character(self, project: str, char_name: str):
        self._validate_char_name(char_name)
        path = self._settings_path(project, f"人物设定/{char_name}.md")
        if os.path.exists(path):
            os.remove(path)

    def read_background_timeline(self, project: str) -> Optional[str]:
        return self._read_file(self._settings_path(project, "时间线/背景时间线.md"))

    def write_background_timeline(self, project: str, content: str):
        self._write_file(self._settings_path(project, "时间线/背景时间线.md"), content)

    def read_story_timeline(self, project: str) -> Optional[str]:
        return self._read_file(self._settings_path(project, "时间线/故事时间线.md"))

    def write_story_timeline(self, project: str, content: str):
        self._write_file(self._settings_path(project, "时间线/故事时间线.md"), content)

    def read_relationship(self, project: str) -> Optional[str]:
        return self._read_file(self._settings_path(project, "人物关系.md"))

    def write_relationship(self, project: str, content: str):
        self._write_file(self._settings_path(project, "人物关系.md"), content)

    def read_style_guide(self, project: str) -> Optional[str]:
        return self._read_file(self._settings_path(project, "风格指南.md"))

    def write_style_guide(self, project: str, content: str):
        self._write_file(self._settings_path(project, "风格指南.md"), content)

    # ── Outline read/write ─────────────────────────────────────

    def _outline_path(self, project: str, subpath: str) -> str:
        return os.path.join(self._project_path(project), "大纲", subpath)

    def read_book_outline(self, project: str) -> Optional[str]:
        return self._read_file(self._outline_path(project, "全书大纲.md"))

    def write_book_outline(self, project: str, content: str):
        self._write_file(self._outline_path(project, "全书大纲.md"), content)

    def read_volume_outline(self, project: str, volume: int) -> Optional[str]:
        return self._read_file(self._outline_path(project, f"第{volume}卷/卷大纲.md"))

    def write_volume_outline(self, project: str, volume: int, content: str):
        self._write_file(self._outline_path(project, f"第{volume}卷/卷大纲.md"), content)

    def read_chapter_outline(self, project: str, volume: int, chapter: int) -> Optional[str]:
        return self._read_file(
            self._outline_path(project, f"第{volume}卷/章节大纲/第{chapter}章.md")
        )

    def write_chapter_outline(self, project: str, volume: int, chapter: int, content: str):
        self._write_file(
            self._outline_path(project, f"第{volume}卷/章节大纲/第{chapter}章.md"), content
        )

    def list_volume_outlines(self, project: str) -> list[int]:
        outline_dir = self._outline_path(project, "")
        if not os.path.exists(outline_dir):
            return []
        vols = []
        for d in os.listdir(outline_dir):
            if d.startswith("第") and d.endswith("卷") and os.path.isdir(os.path.join(outline_dir, d)):
                try:
                    num = int(re.search(r'\d+', d).group())
                    vols.append(num)
                except (ValueError, AttributeError):
                    pass
        return sorted(vols)

    def list_chapter_outlines(self, project: str, volume: int) -> list[int]:
        chapters_dir = self._outline_path(project, f"第{volume}卷/章节大纲")
        if not os.path.exists(chapters_dir):
            return []
        chaps = []
        for f in os.listdir(chapters_dir):
            m = re.match(r'第(\d+)章\.md', f)
            if m:
                chaps.append(int(m.group(1)))
        return sorted(chaps)

    def ensure_volume_dir(self, project: str, volume: int):
        dirs = [
            self._outline_path(project, f"第{volume}卷/章节大纲"),
            self._chapter_path(project, f"第{volume}卷"),
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)

    # ── Chapter read/write ─────────────────────────────────────

    def _chapter_path(self, project: str, subpath: str) -> str:
        return os.path.join(self._project_path(project), "正文", subpath)

    def read_chapter(self, project: str, volume: int, chapter: int) -> Optional[str]:
        return self._read_file(
            self._chapter_path(project, f"第{volume}卷/第{chapter}章.md")
        )

    def write_chapter(self, project: str, volume: int, chapter: int, content: str):
        self._write_file(
            self._chapter_path(project, f"第{volume}卷/第{chapter}章.md"), content
        )

    def list_chapters(self, project: str, volume: int) -> list[int]:
        chaps_dir = self._chapter_path(project, f"第{volume}卷")
        if not os.path.exists(chaps_dir):
            return []
        chaps = []
        for f in os.listdir(chaps_dir):
            m = re.match(r'第(\d+)章\.md', f)
            if m:
                chaps.append(int(m.group(1)))
        return sorted(chaps)

    # ── Foreshadowing read/write ───────────────────────────────

    def _fb_path(self, project: str, subpath: str = "") -> str:
        return os.path.join(self._project_path(project), "伏笔管理", subpath)

    def read_foreshadowing_list(self, project: str) -> Optional[str]:
        return self._read_file(self._fb_path(project, "伏笔清单.md"))

    def write_foreshadowing_list(self, project: str, content: str):
        self._write_file(self._fb_path(project, "伏笔清单.md"), content)

    def read_foreshadowing_detail(self, project: str, fb_id: str) -> Optional[str]:
        return self._read_file(self._fb_path(project, f"伏笔详情/{fb_id}.md"))

    def write_foreshadowing_detail(self, project: str, fb_id: str, content: str):
        self._write_file(self._fb_path(project, f"伏笔详情/{fb_id}.md"), content)

    # ── Search ─────────────────────────────────────────────────

    def search(self, project: str, query: str) -> list[dict]:
        """Keyword search across all project files. Returns top snippets."""
        proj_path = self._project_path(project)
        results = []
        keywords = query.lower().split()

        for root, dirs, files in os.walk(proj_path):
            # Skip version history
            if "版本历史" in root:
                continue
            for fname in files:
                if not fname.endswith(".md"):
                    continue
                fpath = os.path.join(root, fname)
                content = self._read_file(fpath)
                if not content:
                    continue
                content_lower = content.lower()
                score = sum(1 for kw in keywords if kw in content_lower)
                if score > 0:
                    rel_path = os.path.relpath(fpath, proj_path)
                    snippet = content[:300]
                    results.append({
                        "file": rel_path,
                        "score": score,
                        "snippet": snippet,
                    })

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:10]

    # ── All settings snapshot ──────────────────────────────────

    def get_all_settings(self, project: str) -> list[dict]:
        """Return all current settings as context docs for LLM calls."""
        docs = []

        world = self.read_world_setting(project)
        if world:
            docs.append({"title": "世界设定", "content": world})

        for char in self.list_characters(project):
            content = self.read_character(project, char)
            if content:
                docs.append({"title": f"人物设定：{char}", "content": content})

        bg_tl = self.read_background_timeline(project)
        if bg_tl:
            docs.append({"title": "背景时间线", "content": bg_tl})

        st_tl = self.read_story_timeline(project)
        if st_tl:
            docs.append({"title": "故事时间线", "content": st_tl})

        rel = self.read_relationship(project)
        if rel:
            docs.append({"title": "人物关系", "content": rel})

        style = self.read_style_guide(project)
        if style:
            docs.append({"title": "风格指南", "content": style})

        return docs
