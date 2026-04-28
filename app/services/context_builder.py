"""Centralized context assembly for LLM calls.

All context-building logic that was previously scattered across settings.py,
chapter_write.py, outline.py, and writing_assist.py lives here.
"""


def build_full_context(fm, project: str) -> str:
    """Build a complete context string from all project settings.

    Replaces the repeated inline pattern:
        context_docs = fm.get_all_settings(project)
        context_parts = [...]
        for doc in context_docs: ...
    """
    docs = fm.get_all_settings(project)
    parts = ["参考以下已有资料：\n"]
    for doc in docs:
        parts.append(f"【{doc['title']}】")
        parts.append(doc["content"])
        parts.append("")
    return "\n".join(parts)


def build_targeted_context(fm, project: str, setting_type: str, volume: int = 1) -> str:
    """Build a context string from settings relevant to the given type.

    Used by chat-based setting creation (settings.py _get_relevant_context
    replacement). Returns only what's useful for the target setting type.
    """
    parts = []

    if setting_type != "world":
        world = fm.read_world_setting(project)
        if world:
            parts.append(f"【世界设定（已完成）】\n{world}\n")

    if setting_type != "character":
        chars = fm.list_characters(project)
        if chars:
            char_texts = []
            char_limit = 2000 if setting_type == "relationship" else 800
            for c in chars[:8]:
                content = fm.read_character(project, c)
                if content:
                    char_texts.append(f"### {c}\n{content[:char_limit]}")
            if char_texts:
                parts.append("【人物设定（已完成）】\n" + "\n\n".join(char_texts) + "\n")

    if setting_type not in ("timeline", "world"):
        bg = fm.read_background_timeline(project)
        if bg:
            parts.append(f"【背景时间线（已完成）】\n{bg[:1500]}\n")
        story = fm.read_story_timeline(project)
        if story:
            parts.append(f"【故事时间线（已完成）】\n{story[:1500]}\n")

    if setting_type != "relationship":
        rel = fm.read_relationship(project)
        if rel:
            parts.append(f"【人物关系（已完成）】\n{rel[:1500]}\n")

    if setting_type != "style":
        style = fm.read_style_guide(project)
        if style:
            parts.append(f"【风格指南（已完成）】\n{style[:1000]}\n")

    if setting_type in ("volume_outline", "chapter_outline"):
        book = fm.read_book_outline(project)
        if book:
            parts.append(f"【全书大纲（已完成）】\n{book[:2000]}\n")
    if setting_type == "chapter_outline":
        vol = fm.read_volume_outline(project, volume)
        if vol:
            parts.append(f"【第{volume}卷大纲（已完成）】\n{vol[:2000]}\n")

    return "\n".join(parts)


def build_chapter_context(fm, project: str, volume: int, chapter: int) -> str:
    """Build context specific to chapter writing, including volume/book outlines."""
    parts = [build_full_context(fm, project)]

    chapter_outline = fm.read_chapter_outline(project, volume, chapter)
    if chapter_outline:
        parts.insert(0, f"【本章大纲】\n{chapter_outline}\n")

    return "\n".join(parts)
