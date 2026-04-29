"""Programmatic markdown manipulation utilities for Phase 3 knowledge sync.

All functions operate on markdown strings and return updated strings.
They do NOT perform file I/O — that remains the caller's responsibility.

Each function returns a sentinel value (empty string or same-as-input) when
it cannot safely parse the format. The caller falls back to LLM in that case.
"""

import re
from typing import Optional


def append_table_rows(existing: str, header_pattern: str, new_rows: list[str]) -> str:
    """Append rows to the first markdown table matching `header_pattern`.

    Returns the updated markdown string, or `existing` unchanged if the
    table header is not found.
    """
    header_idx = existing.find(header_pattern)
    if header_idx == -1:
        return existing

    # Find end of header line
    line_start = existing.rfind("\n", 0, header_idx)
    if line_start == -1:
        line_start = 0
    header_end = existing.find("\n", header_idx)
    if header_end == -1:
        header_end = len(existing)

    # Find separator line (| --- | --- |)
    sep_start = existing.find("\n", header_end)
    if sep_start == -1:
        return existing
    sep_end = existing.find("\n", sep_start + 1)
    if sep_end == -1:
        sep_end = len(existing)
    sep_line = existing[sep_start + 1:sep_end]
    if "|" not in sep_line or "-" not in sep_line:
        return existing

    # Walk forward from separator to find the last data row of this table
    pos = sep_end + 1
    last_data_end = sep_end
    while pos < len(existing):
        next_nl = existing.find("\n", pos)
        if next_nl == -1:
            next_nl = len(existing)
        line = existing[pos:next_nl]
        stripped = line.strip()
        if stripped.startswith("|") and "|" in stripped[1:]:
            last_data_end = next_nl
            pos = next_nl + 1
        else:
            break

    # Determine indentation from the first data row after separator
    first_data_pos = sep_end + 1
    if first_data_pos < len(existing):
        indent = " " * (len(existing[first_data_pos:]) - len(existing[first_data_pos:].lstrip()))
    else:
        indent = ""

    new_text = "\n".join(f"{indent}{row}" for row in new_rows)
    return existing[:last_data_end + 1] + new_text + "\n" + existing[last_data_end + 1:]


def append_section(existing: str, heading: str, new_content: str) -> str:
    """Append content under a markdown heading section.

    If the heading exists, content is appended after the section's existing
    content (before the next heading of equal or higher level).
    If the heading does not exist, it is created at the end of the document.

    Returns updated markdown string.
    """
    heading_level = heading.count("#", 0, heading.find(" ") if " " in heading else len(heading))
    if heading_level == 0:
        heading_level = 2  # default to ##

    # Try to find the heading
    pattern = re.compile(rf"^{re.escape(heading)}", re.MULTILINE)
    match = pattern.search(existing)
    if match:
        # Find the next heading of same or higher level
        insert_pos = len(existing)
        next_heading = re.compile(rf"^#{{{1,{heading_level}}}}\s", re.MULTILINE)
        next_match = next_heading.search(existing, match.end())
        if next_match:
            insert_pos = next_match.start()
        # Insert before next heading, with newlines as needed
        before = existing[:insert_pos].rstrip()
        after = existing[insert_pos:]
        return before + "\n\n" + new_content.strip() + "\n\n" + after.lstrip()

    # Heading doesn't exist — create at end
    prefix = "\n\n" if existing and not existing.endswith("\n\n") else "\n"
    return existing + prefix + heading + "\n\n" + new_content.strip() + "\n"


def append_list_item(existing: str, heading: str, new_item: str) -> str:
    """Append a bullet list item under a markdown heading section.

    Finds the heading, then finds the nearest list item block after it
    and appends. If no list exists under the heading, creates one.

    Returns updated markdown string.
    """
    heading_level = heading.count("#", 0, heading.find(" ") if " " in heading else len(heading))
    if heading_level == 0:
        heading_level = 2

    pattern = re.compile(rf"^{re.escape(heading)}", re.MULTILINE)
    match = pattern.search(existing)
    if not match:
        # Heading doesn't exist — delegate to append_section
        return append_section(existing, heading, new_item)

    # Find scope: everything from heading to next heading of same/higher level
    next_heading = re.compile(rf"^#{{{1,{heading_level}}}}\s", re.MULTILINE)
    next_match = next_heading.search(existing, match.end())
    section_end = next_match.start() if next_match else len(existing)
    section_text = existing[match.start():section_end]

    # Find the last list item in this section
    list_item_pattern = re.compile(r"^- .+$", re.MULTILINE)
    list_items = list(list_item_pattern.finditer(section_text))
    if list_items:
        last_item = list_items[-1]
        insert_pos = match.start() + last_item.end()
        before = existing[:insert_pos]
        after = existing[insert_pos:]
        return before + "\n" + new_item + after

    # No list exists — append after heading line
    heading_end = existing.find("\n", match.start())
    if heading_end == -1:
        heading_end = match.end()
    before = existing[:heading_end + 1]
    after = existing[heading_end + 1:]
    return before + new_item + "\n" + after


def build_character_template(name: str, description: str, faction: str,
                             chapter: int) -> str:
    """Generate a minimal character markdown file for sync-auto-created characters."""
    desc_line = description if description else "待补充"
    faction_line = faction if faction else "待补充"
    return (
        f"# {name}\n\n"
        f"## 基本信息\n"
        f"- 姓名：{name}\n"
        f"- 身份/职业：待补充\n"
        f"- 阵营/所属势力：{faction_line}\n\n"
        f"## 外貌特征\n"
        f"{desc_line}\n\n"
        f"## 性格特点\n"
        f"待补充\n\n"
        f"## 能力设定\n"
        f"待补充\n\n"
        f"## 物品装备\n"
        f"待补充\n\n"
        f"## 重要经历\n"
        f"| 时间/章节 | 事件 | 状态变化 |\n"
        f"|----------|------|---------|\n"
        f"| 第{chapter}章 | 首次登场 | - |\n\n"
        f"## 当前状态\n"
        f"- 所在地：待补充\n"
        f"- 健康状况：待补充\n"
        f"- 心理状态：待补充\n\n"
        f"## 人物关系\n"
        f"待补充\n\n"
        f"## 成长轨迹\n"
        f"待补充\n\n"
        f"---\n"
        f"> 此角色由知识同步自动创建于第{chapter}章。请根据需要完善。\n"
    )


def build_timeline_rows(events: list[dict], chapter: int) -> list[str]:
    """Convert Phase 2 event extraction JSON into timeline markdown table rows."""
    rows = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        event_text = ev.get("event", "")
        if not event_text:
            continue
        time = ev.get("time", f"第{chapter}章")
        chars = ev.get("characters", [])
        char_text = "、".join(chars) if chars else "-"
        scope = ev.get("scope", "个人")
        rows.append(f"| {time} | 第{chapter}章 | {event_text} | {char_text} | {scope} |")
    return rows


def build_relationship_change_rows(changes: list[dict], chapter: int) -> list[str]:
    """Convert Phase 2 relationship change JSON into relationship table rows."""
    rows = []
    for ch in changes:
        if not isinstance(ch, dict):
            continue
        char_a = ch.get("char_a", "?")
        char_b = ch.get("char_b", "?")
        change = ch.get("status", ch.get("type", "?"))
        trigger = ch.get("trigger_event", "-")
        rows.append(f"| 第{chapter}章 | {char_a}, {char_b} | {change} | 第{chapter}章 |")
    return rows


def extract_key_terms(text: str) -> set[str]:
    """Extract key named entities from text for conflict detection.
    Returns a set of 2+ character Chinese/English proper nouns.
    """
    terms = set()
    # Extract from bold markers: **Name**
    for m in re.finditer(r'\*\*(.+?)\*\*', text):
        term = m.group(1).strip()
        if 2 <= len(term) <= 30:
            terms.add(term)
    # Extract key-value pairs: name/character/place: Value
    for m in re.finditer(r'(?:姓名|名称|角色名|character|name|地点|place|事件)[：:]\s*([^\n]{2,30})', text, re.IGNORECASE):
        term = m.group(1).strip()
        if term:
            terms.add(term)
    # Filter out generic terms
    _generic = {"未知", "无", "暂无", "待定", "N/A", "none", "unknown", "——", "--"}
    return {t for t in terms if t not in _generic}


def find_conflicts(new_terms: set[str], existing_text: str) -> list[str]:
    """Check if any new terms overlap with existing settings content.
    Returns a list of conflict descriptions."""
    conflicts = []
    for term in new_terms:
        if len(term) < 2:
            continue
        if term in existing_text:
            conflicts.append(f"'{term}' 在已有设定中已存在，新内容可能与之冲突")
    return conflicts
