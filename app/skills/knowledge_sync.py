"""Knowledge sync engine — the core innovation of the system.

Workflow (v0.2.0 — optimized):
  Phase 0: Pre-load all settings once into session cache
  Phase 1: Text analysis (1 LLM call — free-text, no JSON)
  Phase 2: Parallel category extraction (5 LLM calls via asyncio.gather)
  Phase 3: File updates
    - Characters: programmatic template for simple new chars,
      single batch LLM call for all complex changes
    - Events: programmatic table-row append (LLM fallback)
    - World: programmatic section/list append (LLM fallback)
    - Relationships: programmatic table-row append (LLM fallback)
    - Foreshadowing: direct file I/O
  Phase 4: Update report

Total LLM calls: 2-4 (down from 12+). Wall time: 15-30s (down from 60-120s).
"""

import asyncio
import json
import logging
import os
import re
import time as _time

from app.skills.character_design import run as char_skill
from app.skills.timeline import run as timeline_skill
from app.skills.world_design import run as world_skill
from app.skills.relationship import run as rel_skill

SYNC_DEBUG_RETENTION = 5  # Keep last N sync debug file sets

# ══════════════════════════════════════════════════════════════════════════════
# Phase 1 — Text Analysis Prompt
# ══════════════════════════════════════════════════════════════════════════════

ANALYSIS_PROMPT = """你是一位资深小说编辑，专精于从章节文本中识别和梳理所有创作要素。

你的任务是：仔细阅读本章正文，输出一份完整的文字分析报告。

## 分析维度

### 1. 出场人物
列出本章中出现的所有人物。对每个人物，记录：
- 是否首次登场（与已有设定比对）
- 本章展现的能力、行为、对话特征
- 身体/心理/身份/所在地的任何变化
- 获得或失去的物品
- 人物性格的新表现

### 2. 地点场景
- 本章出现的所有地点名称
- 每个地点的环境特征
- 所属区域

### 3. 事件记录
按时间顺序列出本章发生的所有重要事件：
- 事件名称和简要描述
- 参与人物
- 影响范围（个人/团队/势力/地区/世界）

### 4. 关系变化
- 人物之间关系的建立/变化/深化
- 导致变化的关键事件

### 5. 伏笔线索
- 本章埋下的潜在伏笔（未解之谜、神秘物品、模糊预言等）
- 本章回收的前文伏笔（引用伏笔ID如 FB-001-01）

### 6. 新设定元素
- 新出现的能力规则、世界规则
- 新出现的重要物品
- 对已有设定的补充或修正

### 7. 潜在冲突
- 本章内容与已有设定矛盾的地方
- 不确定、需要后续确认的信息

## 输出要求
- 使用中文
- 按上述维度分节
- 尽量具体、详细，引用原文关键描述
- 不需要 JSON，纯文字分析即可
- 控制在 2000 字以内"""


# ══════════════════════════════════════════════════════════════════════════════
# Phase 2 — Category Extraction Prompts
# ══════════════════════════════════════════════════════════════════════════════

_FILTERING_PREAMBLE = """## 重要度筛选规则（严格遵守）
1. 只提取新增的、有实质性变化的信息。不确定是否重要的信息应当省略。
2. 角色：忽略仅作为背景出现的功能性路人（如"店小二端上茶水"、"守卫站在门口"）。只有有名字的角色，或虽无名但对情节有实际推动作用的角色，才需要提取。
3. 事件：忽略过渡性/背景性描述（如赶路、吃饭等日常活动）。只提取对主线或支线有实质推进的事件。重复或细化已有事件的信息应合并而非新增。
4. 世界设定：忽略无命名的背景景物（如"一片树林"、"某间客栈"）。只有具体命名的地点、或具有独特世界观意义的新元素才需要提取。

"""

CHARACTER_PROMPT = """你是一位角色设定管理员。根据章节分析报告，提取所有人物相关信息。

已有角色列表已提供。请区分"新角色"（不在列表中）和"角色更新"（已在列表中）。

输出 JSON 格式（用 ```json 包裹）：
```json
{
  "new_characters": [
    {"name": "角色名", "description": "外貌、性格、能力简述", "faction": "所属阵营"}
  ],
  "character_updates": [
    {"name": "角色名", "field": "变更领域（能力设定/身体状态/心理状态/物品/性格表现/身份/所在地）", "change": "简短标题", "detail": "详细描述"}
  ]
}
```
没有的字段返回空数组 []。"""


EVENT_PROMPT = """你是一位时间线管理员。根据章节分析报告，提取本章发生的所有重要事件。

输出 JSON 格式（用 ```json 包裹）：
```json
{
  "new_events": [
    {"time": "时间点或序号", "event": "事件描述（一句话）", "characters": ["参与人物"], "scope": "个人/团队/势力/地区/世界"}
  ]
}
```
没有事件则返回空数组 []。"""


WORLD_PROMPT = """你是一位世界设定管理员。根据章节分析报告，提取所有新地点和世界设定元素。

输出 JSON 格式（用 ```json 包裹）：
```json
{
  "new_locations": [
    {"name": "地点名", "description": "环境特征描述", "region": "所属区域"}
  ],
  "new_world_info": {
    "new_rules": ["新发现的世界规则或力量体系规则"],
    "new_items": ["新出现的重要物品及其描述"],
    "new_powers": ["新出现的能力或技能及其描述"]
  }
}
```
没有的字段返回空数组 [] 或空对象 {}。"""


RELATIONSHIP_PROMPT = """你是一位人物关系分析师。根据章节分析报告，提取本章中的人物关系变化。

输出 JSON 格式（用 ```json 包裹）：
```json
{
  "relationship_changes": [
    {"char_a": "角色A", "char_b": "角色B", "type": "关系类型", "status": "当前状态", "trigger_event": "触发事件", "previous": "之前状态"}
  ]
}
```
没有变化则返回空数组 []。"""


FORESHADOWING_PROMPT = """你是一位伏笔管理员。根据章节分析报告，提取伏笔信息。

输出 JSON 格式（用 ```json 包裹）：
```json
{
  "new_foreshadowing": [
    {"content": "伏笔内容描述", "related_characters": ["涉及人物"], "suggested_recovery_chapter": null}
  ],
  "recovered_foreshadowing": [
    {"id": "FB-001-01", "how": "回收方式描述"}
  ]
}
```
没有的字段返回空数组 []。"""


# ══════════════════════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════════════════════

_MAX_CONCURRENT_EXTRACTORS = 3  # Cap parallel Phase 2 calls to avoid API rate limits

_DOMAIN_LABELS = {
    "characters": "人物",
    "events": "事件",
    "world": "世界设定",
    "relationships": "人物关系",
    "foreshadowing": "伏笔",
}


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _save_debug(proj_path: str, chapter: int, phase: str, content: str, *, debug: bool = False):
    """Save intermediate results for diagnosis. No-op when debug=False."""
    if not debug:
        return
    try:
        debug_dir = os.path.join(proj_path, "调试")
        os.makedirs(debug_dir, exist_ok=True)
        path = os.path.join(debug_dir, f"同步_{phase}_第{chapter}章.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass


def _cleanup_old_debug_files(proj_path: str, retention: int = None):
    """Delete debug files older than the `retention` most recent sync batches."""
    if retention is None:
        retention = SYNC_DEBUG_RETENTION
    debug_dir = os.path.join(proj_path, "调试")
    if not os.path.exists(debug_dir):
        return
    # Group files by chapter (each chapter = one sync batch)
    chapter_groups: dict[int, list[str]] = {}
    for f in os.listdir(debug_dir):
        match = re.match(r'同步_.*_第(\d+)章\.txt', f)
        if match:
            ch = int(match.group(1))
            chapter_groups.setdefault(ch, []).append(f)
    # Keep only the most recent `retention` chapter groups
    sorted_chapters = sorted(chapter_groups.keys(), reverse=True)
    for old_ch in sorted_chapters[retention:]:
        for f in chapter_groups[old_ch]:
            try:
                os.remove(os.path.join(debug_dir, f))
            except OSError:
                pass


async def _call_llm(llm, system_prompt: str, context_docs: list, user_message: str,
                    max_tokens: int = 8192) -> dict:
    """Wrapper: call LLM, parse JSON, return {"content": str, "json": dict|None}."""
    try:
        return await llm.chat_with_context_and_json(
            system_prompt=system_prompt,
            context_docs=context_docs,
            user_message=user_message,
            max_tokens=max_tokens,
        )
    except Exception as e:
        logging.getLogger(__name__).warning(f"LLM call failed in sync phase: {e}")
        return {"content": "", "json": None}


def _preload_settings(fm, project: str) -> dict[str, str]:
    """Pre-load all project settings into a dict for sync session reuse.

    Returns a dict keyed by document title (e.g. "世界设定", "故事时间线",
    "人物设定：角色名").  All Phase 2 extractors and Phase 3 processors
    look up from this cache instead of re-reading from disk.
    """
    docs = fm.get_all_settings(project)
    return {doc["title"]: doc["content"] for doc in docs}


def _existing_char_names(fm, project: str) -> list[str]:
    """Get list of existing character names for the project."""
    return fm.list_characters(project)


# ══════════════════════════════════════════════════════════════════════════════
# Phase 1: Text Analysis
# ══════════════════════════════════════════════════════════════════════════════

async def _text_analysis(llm, fm, project: str, volume: int, chapter: int,
                         chapter_content: str, settings_cache: dict[str, str]) -> str:
    """Read chapter, produce detailed markdown analysis."""
    context_docs = [{"title": title, "content": content}
                    for title, content in settings_cache.items()]
    outline = fm.read_chapter_outline(project, volume, chapter)
    if outline:
        context_docs.insert(0, {"title": "本章大纲", "content": outline})

    user_msg = (
        f"请分析以下第{volume}卷第{chapter}章的正文，输出完整的创作要素分析报告。\n\n"
        f"已有角色列表：{', '.join(_existing_char_names(fm, project)) or '（暂无）'}\n\n"
        f"正文内容：\n\n{chapter_content}"
    )

    result = await llm.chat_with_context(
        system_prompt=ANALYSIS_PROMPT,
        context_docs=context_docs,
        user_message=user_msg,
        max_tokens=8192,
    )
    return result or ""


# ══════════════════════════════════════════════════════════════════════════════
# Phase 2: Category Extraction
# ══════════════════════════════════════════════════════════════════════════════

async def _extract_characters(llm, fm, project: str, volume: int, chapter: int,
                              analysis: str, settings_cache: dict[str, str]) -> dict:
    """Extract new characters and character updates from analysis."""
    existing_names = _existing_char_names(fm, project)
    context = [
        {"title": "章节分析报告", "content": analysis},
        {"title": "已有角色列表", "content": ", ".join(existing_names) if existing_names else "（暂无角色）"},
    ]
    user_msg = (
        f"请根据分析报告，提取第{volume}卷第{chapter}章中的新角色和角色变化。\n"
        f"已有角色：{', '.join(existing_names) or '无'}\n"
        f"不在已有列表中的角色归类为 new_characters，已在列表中的归类为 character_updates。"
    )
    result = await _call_llm(llm, _FILTERING_PREAMBLE + CHARACTER_PROMPT, context, user_msg, max_tokens=8192)
    return result.get("json") or {}


async def _extract_events(llm, fm, project: str, volume: int, chapter: int,
                          analysis: str, settings_cache: dict[str, str]) -> dict:
    """Extract timeline events from analysis."""
    existing_story = settings_cache.get("故事时间线", "")
    context = [
        {"title": "章节分析报告", "content": analysis},
    ]
    if existing_story:
        context.append({"title": "当前故事时间线（参考）", "content": existing_story[-2000:]})
    user_msg = f"请根据分析报告，提取第{volume}卷第{chapter}章中发生的重要事件。"
    result = await _call_llm(llm, _FILTERING_PREAMBLE + EVENT_PROMPT, context, user_msg, max_tokens=8192)
    return result.get("json") or {}


async def _extract_world(llm, fm, project: str, volume: int, chapter: int,
                         analysis: str, settings_cache: dict[str, str]) -> dict:
    """Extract new locations and world info from analysis."""
    existing_world = settings_cache.get("世界设定", "")
    context = [
        {"title": "章节分析报告", "content": analysis},
    ]
    if existing_world:
        context.append({"title": "当前世界设定（参考）", "content": existing_world[-3000:]})
    user_msg = f"请根据分析报告，提取第{volume}卷第{chapter}章中出现的新地点和世界设定元素。"
    result = await _call_llm(llm, _FILTERING_PREAMBLE + WORLD_PROMPT, context, user_msg, max_tokens=8192)
    return result.get("json") or {}


async def _extract_relationships(llm, fm, project: str, volume: int, chapter: int,
                                 analysis: str, settings_cache: dict[str, str]) -> dict:
    """Extract relationship changes from analysis."""
    existing_rel = settings_cache.get("人物关系", "")
    context = [
        {"title": "章节分析报告", "content": analysis},
    ]
    if existing_rel:
        context.append({"title": "当前人物关系（参考）", "content": existing_rel[-2000:]})
    user_msg = f"请根据分析报告，提取第{volume}卷第{chapter}章中的人物关系变化。"
    result = await _call_llm(llm, _FILTERING_PREAMBLE + RELATIONSHIP_PROMPT, context, user_msg, max_tokens=8192)
    return result.get("json") or {}


async def _extract_foreshadowing(llm, fm, project: str, volume: int, chapter: int,
                                 analysis: str, settings_cache: dict[str, str]) -> dict:
    """Extract foreshadowing from analysis."""
    existing_fb = fm.read_foreshadowing_list(project) or ""
    context = [
        {"title": "章节分析报告", "content": analysis},
    ]
    if existing_fb:
        context.append({"title": "当前伏笔清单（参考）", "content": existing_fb[-2000:]})
    user_msg = f"请根据分析报告，提取第{volume}卷第{chapter}章中埋设的新伏笔和回收的旧伏笔。"
    result = await _call_llm(llm, _FILTERING_PREAMBLE + FORESHADOWING_PROMPT, context, user_msg, max_tokens=8192)
    return result.get("json") or {}


# ══════════════════════════════════════════════════════════════════════════════
# Phase 3: File Updates
# ══════════════════════════════════════════════════════════════════════════════

async def _process_characters(llm, fm, project: str, chapter: int, data: dict,
                             settings_cache: dict[str, str]) -> tuple[list, bool]:
    """Process character changes: simple → programmatic, complex → batch LLM.

    - Simple new characters (name + brief description): programmatic template
    - Character updates and complex new characters: single batch LLM call
    """
    from app.services.markdown_utils import build_character_template

    lines = []
    changed = False

    new_chars = data.get("new_characters", [])
    updates = data.get("character_updates", [])

    # Separate simple new characters from ones needing LLM
    programmatic_new = []
    llm_new = []
    for nc in new_chars:
        name = nc.get("name", "") if isinstance(nc, dict) else str(nc)
        if not name:
            continue
        desc = nc.get("description", "") if isinstance(nc, dict) else ""
        # Simple if description is short and no faction complexity
        if len(desc) < 200:
            programmatic_new.append((name, desc, nc.get("faction", "") if isinstance(nc, dict) else ""))
        else:
            llm_new.append(nc)

    # Programmatic creation of simple new characters
    for name, desc, faction in programmatic_new:
        try:
            content = build_character_template(name, desc, faction, chapter)
            fm.write_character(project, name, content)
            changed = True
            lines.append(f"- 新人物（自动）：{name}")
        except Exception as e:
            lines.append(f"- 新人物创建失败（{name}）：{e}")

    # Collect updates that need LLM (existing char updates + complex new chars)
    llm_updates = list(updates)  # all updates go to LLM batch
    llm_new_names = {nc.get("name", "") if isinstance(nc, dict) else str(nc) for nc in llm_new}

    # Prepare existing files for characters needing LLM
    existing_files = {}
    for cu in llm_updates:
        name = cu.get("name", "") if isinstance(cu, dict) else str(cu)
        if not name:
            continue
        cache_key = f"人物设定：{name}"
        content = settings_cache.get(cache_key) or fm.read_character(project, name)
        if content:
            existing_files[name] = content
        elif name not in llm_new_names:
            # Character doesn't exist yet but wasn't in new_chars — quick create
            tmpl = build_character_template(name, "", "", chapter)
            fm.write_character(project, name, tmpl)
            existing_files[name] = tmpl
            lines.append(f"- 自动创建角色：{name}（原为更新目标）")
            changed = True

    for nc in llm_new:
        name = nc.get("name", "") if isinstance(nc, dict) else str(nc)
        if name:
            existing_files[name] = ""  # marker: needs full creation

    # Batch LLM call for all remaining character work
    if llm_updates or llm_new:
        try:
            batch_result = await _batch_character_update(
                llm, fm, project, chapter, llm_updates, llm_new, existing_files
            )
            if batch_result:
                summary_entries = batch_result.pop("_summary", []) or []
                for char_name, content in batch_result.items():
                    if content and isinstance(content, str):
                        fm.write_character(project, char_name, content)
                        changed = True
                lines.extend(f"- {n}: {d}" for n, d in summary_entries)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Batch character update failed: {e}")
            lines.append(f"- 批量角色更新失败：{e}，已跳过")
            # Fall back to individual updates
            for cu in llm_updates:
                try:
                    name = cu.get("name", "") if isinstance(cu, dict) else str(cu)
                    if not name or name not in existing_files:
                        continue
                    field = cu.get("field", "") if isinstance(cu, dict) else ""
                    change = cu.get("change", "") if isinstance(cu, dict) else ""
                    detail = cu.get("detail", "") if isinstance(cu, dict) else ""
                    result = await char_skill(llm, fm, project, {
                        "action": "update",
                        "instruction": f"更新{field}：{change}，详情：{detail}",
                        "char_name": name,
                        "existing_content": existing_files[name],
                    })
                    if result.get("success"):
                        fm.write_character(project, name, result["content"])
                        changed = True
                        lines.append(f"- {name}：{change}")
                except Exception as e2:
                    lines.append(f"- 人物更新失败（{cu}）：{e2}")

    return lines, changed


async def _batch_character_update(llm, fm, project: str, chapter: int,
                                  updates: list, new_chars: list,
                                  existing_files: dict) -> dict | None:
    """Single LLM call to process all complex character changes at once.

    Returns dict of {char_name: new_content} or None on failure.
    A special key "_summary" contains [(name, change_summary), ...] for reporting.
    """
    if not updates and not new_chars:
        return None

    change_descriptions = []
    for u in updates:
        name = u.get("name", "") if isinstance(u, dict) else str(u)
        field = u.get("field", "") if isinstance(u, dict) else ""
        change = u.get("change", "") if isinstance(u, dict) else ""
        detail = u.get("detail", "") if isinstance(u, dict) else ""
        change_descriptions.append(f"- {name}：{field} — {change}（{detail}）")

    for nc in new_chars:
        name = nc.get("name", "") if isinstance(nc, dict) else str(nc)
        desc = nc.get("description", "") if isinstance(nc, dict) else ""
        faction = nc.get("faction", "") if isinstance(nc, dict) else ""
        change_descriptions.append(f"- [新角色] {name}：{desc}，阵营：{faction}")

    context_docs = []
    for name, content in existing_files.items():
        if content:
            label = "新角色（待创建）" if not content.strip() else "当前设定"
            context_docs.append({"title": f"{label}：{name}", "content": content or "（待创建）"})

    user_msg = (
        f"请一次性处理以下所有角色变更（第{chapter}章）：\n\n"
        + "\n".join(change_descriptions)
        + "\n\n对每个角色，输出完整的更新后设定文件。"
        + "\n每个角色以 ---CHARACTER:角色名--- 开头。"
    )

    try:
        result = await llm.chat_with_context_and_json(
            system_prompt=(
                "你是一位角色设定批量更新专家。你将收到多个角色的变更请求。\n"
                "对每个角色，输出其完整的更新后Markdown设定文件。\n"
                "每个文件以 `---CHARACTER:角色名---` 单独一行开头。\n"
                "保留已有设定中未变更的部分，仅修改需要变更的领域。\n"
                "在重要经历表中追加新的经历行。\n"
                "使用中文。"
            ),
            context_docs=context_docs,
            user_message=user_msg,
            max_tokens=16384,
        )
    except Exception as e:
        logging.getLogger(__name__).warning(f"Batch character LLM call failed: {e}")
        return None

    content = result.get("content", "")
    if not content:
        return None

    # Split by separator
    parts = {}
    current_name = None
    current_lines = []
    for line in content.split("\n"):
        if line.startswith("---CHARACTER:"):
            if current_name and current_lines:
                parts[current_name] = "\n".join(current_lines).strip()
            current_name = line[len("---CHARACTER:"):].strip()
            current_lines = []
        elif current_name:
            current_lines.append(line)

    if current_name and current_lines:
        parts[current_name] = "\n".join(current_lines).strip()

    if not parts:
        return None

    # Build summary
    summary = []
    for name in parts:
        if name in existing_files and existing_files[name]:
            summary.append((name, "已更新"))
        else:
            summary.append((name, "已创建"))

    parts["_summary"] = summary
    return parts


async def _process_events(llm, fm, project: str, chapter: int, data: dict,
                         settings_cache: dict[str, str]) -> tuple[list, bool]:
    """Update story timeline — programmatic table append with LLM fallback."""
    from app.services.markdown_utils import append_table_rows, build_timeline_rows

    lines = []
    events = data.get("new_events", [])
    if not events:
        return lines, False

    existing = settings_cache.get("故事时间线") or fm.read_story_timeline(project) or ""
    new_rows = build_timeline_rows(events, chapter)

    if new_rows and existing:
        updated = append_table_rows(existing, "| 时间点 |", new_rows)
        if updated != existing:
            fm.write_story_timeline(project, updated)
            lines.append("- 故事时间线已更新（程序化）")
            return lines, True

    # LLM fallback
    try:
        result = await timeline_skill(llm, fm, project, {
            "action": "add_event",
            "instruction": f"添加以下事件：{json.dumps(events, ensure_ascii=False)}",
            "existing_bg": settings_cache.get("背景时间线"),
            "existing_story": existing,
        })
        if result.get("success"):
            if result.get("story"):
                fm.write_story_timeline(project, result["story"])
                lines.append("- 故事时间线已更新")
            if result.get("background"):
                fm.write_background_timeline(project, result["background"])
            return lines, bool(result.get("story"))
        else:
            lines.append(f"- 时间线更新失败：{result.get('error')}")
    except Exception as e:
        lines.append(f"- 时间线更新失败：{e}")

    return lines, False


async def _process_world(llm, fm, project: str, data: dict,
                       settings_cache: dict[str, str]) -> tuple[list, bool]:
    """Update world setting — programmatic section append with LLM fallback."""
    from app.services.markdown_utils import append_section, append_list_item

    lines = []
    new_world = data.get("new_world_info", {})
    new_locs = data.get("new_locations", [])

    existing = settings_cache.get("世界设定") or fm.read_world_setting(project) or ""
    updated = existing
    programmatic_ok = True

    # Programmatic: append new locations
    for nl in new_locs:
        name = nl.get("name", "") if isinstance(nl, dict) else str(nl)
        if not name:
            continue
        desc = nl.get("description", "待补充") if isinstance(nl, dict) else "待补充"
        region = nl.get("region", "待补充") if isinstance(nl, dict) else "待补充"
        loc_md = f"### {name}\n- 位置：{region}\n- 特征：{desc}\n- 势力分布：待补充\n- 资源特产：待补充\n- 特殊规则：待补充\n"
        result = append_section(updated, "## 地理区域", loc_md)
        if result != updated:
            updated = result
            lines.append(f"- 新区域：{name}")
        else:
            programmatic_ok = False

    # Programmatic: append new rules/items/powers
    if isinstance(new_world, dict):
        for rule in new_world.get("new_rules", []):
            result = append_list_item(updated, "## 世界规则", f"- {rule}")
            if result != updated:
                updated = result
            else:
                programmatic_ok = False
        for item in new_world.get("new_items", []):
            result = append_list_item(updated, "## 重要物品", f"- {item}")
            if result != updated:
                updated = result
            else:
                programmatic_ok = False
        for power in new_world.get("new_powers", []):
            result = append_list_item(updated, "## 特殊能力/技能", f"- {power}")
            if result != updated:
                updated = result
            else:
                programmatic_ok = False

    if updated != existing:
        fm.write_world_setting(project, updated)
        lines.append("- 世界设定已更新（程序化）")
        return lines, True

    if not new_locs and not (isinstance(new_world, dict) and (
        new_world.get("new_rules") or new_world.get("new_items") or
        new_world.get("new_powers")
    )):
        return lines, False

    # LLM fallback when programmatic append failed
    if not programmatic_ok:
        try:
            result = await world_skill(llm, fm, project, {
                "action": "update",
                "instruction": f"本章新增元素：{json.dumps(new_world, ensure_ascii=False)}",
                "existing_content": existing,
            })
            if result.get("success"):
                fm.write_world_setting(project, result["content"])
                lines.append("- 世界设定已更新（LLM）")
                return lines, True
        except Exception as e:
            lines.append(f"- 世界设定更新失败：{e}")

    return lines, bool(new_locs)


async def _process_relationships(llm, fm, project: str, chapter: int, data: dict,
                               settings_cache: dict[str, str]) -> tuple[list, bool]:
    """Update relationship map — programmatic table append with LLM fallback."""
    from app.services.markdown_utils import append_table_rows, build_relationship_change_rows

    lines = []
    changes = data.get("relationship_changes", [])
    if not changes:
        return lines, False

    existing = settings_cache.get("人物关系") or fm.read_relationship(project) or ""

    # Try programmatic append to "关系变化记录" table
    new_rows = build_relationship_change_rows(changes, chapter)
    if new_rows and existing:
        updated = append_table_rows(existing, "| 变化时间 |", new_rows)
        if updated != existing:
            fm.write_relationship(project, updated)
            lines.append("- 人物关系已更新（程序化）")
            return lines, True

    # LLM fallback
    try:
        result = await rel_skill(llm, fm, project, {
            "action": "update",
            "instruction": f"关系变化：{json.dumps(changes, ensure_ascii=False)}",
            "existing_content": existing,
        })
        if result.get("success"):
            fm.write_relationship(project, result["content"])
            lines.append("- 人物关系已更新")
            return lines, True
    except Exception as e:
        lines.append(f"- 人物关系更新失败：{e}")

    return lines, False


async def _process_foreshadowing(fm, project: str, volume: int, chapter: int,
                                 data: dict) -> tuple[list, bool]:
    """Write new foreshadowing files and update recovered ones. Returns summary lines."""
    lines = []

    # New foreshadowing
    for idx, fb in enumerate(data.get("new_foreshadowing", []), start=1):
        fb_content = fb.get("content", "") if isinstance(fb, dict) else str(fb)
        if fb_content:
            fb_id = f"FB-{volume:02d}-{chapter:03d}-{idx:02d}"
            related = fb.get("related_characters", []) if isinstance(fb, dict) else []
            suggested = fb.get("suggested_recovery_chapter", "待定") if isinstance(fb, dict) else "待定"
            detail = (
                f"# {fb_id}\n\n"
                f"- 内容：{fb_content}\n"
                f"- 埋设章节：第{chapter}章\n"
                f"- 状态：待回收\n"
                f"- 涉及人物：{', '.join(related) if related else '无'}\n"
                f"- 建议回收章节：{suggested}\n"
            )
            await asyncio.to_thread(fm.write_foreshadowing_detail, project, fb_id, detail)
            lines.append(f"- 伏笔埋设：{fb_content[:50]}...（{fb_id}）")

    # Recovered foreshadowing
    for rfb in data.get("recovered_foreshadowing", []):
        fb_id = rfb.get("id", "") if isinstance(rfb, dict) else str(rfb)
        if fb_id:
            existing = await asyncio.to_thread(fm.read_foreshadowing_detail, project, fb_id)
            if existing:
                how = rfb.get("how", "") if isinstance(rfb, dict) else ""
                updated = existing.replace("待回收", "已回收")
                updated += f"\n- 回收章节：第{chapter}章\n- 回收方式：{how}\n"
                await asyncio.to_thread(fm.write_foreshadowing_detail, project, fb_id, updated)
                lines.append(f"- 伏笔回收：{fb_id}（{how}）")
                state = await asyncio.to_thread(fm.get_project_state, project)
                pending = state.get("待回收伏笔", [])
                if fb_id in pending:
                    pending.remove(fb_id)
                    state["待回收伏笔"] = pending
                    await asyncio.to_thread(fm.save_project_state, project, state)

    return lines, bool(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Phase 4: Report Generation
# ══════════════════════════════════════════════════════════════════════════════

def _generate_report(volume: int, chapter: int, chapter_len: int,
                     analysis: str, phase_results: dict) -> str:
    """Compile all results into a final markdown summary."""
    parts = [f"# 第{chapter}章 更新摘要\n"]
    parts.append(f"**章节字数：** {chapter_len} 字符\n")

    # Phase 1 result
    if analysis:
        preview = analysis[:2000]
        if len(analysis) > 2000:
            preview += "\n\n...（完整分析见调试文件）"
        parts.append(f"## 文字分析\n{preview}\n")

    # Phase 2+3 results per category
    categories = [
        ("人物设定", "characters"),
        ("时间线", "events"),
        ("世界设定", "world"),
        ("人物关系", "relationships"),
        ("伏笔管理", "foreshadowing"),
    ]

    all_lines = []
    changed_cats = set()

    for cat_name, key in categories:
        info = phase_results.get(key, {})
        lines = info.get("lines", [])
        changed = info.get("changed", False)
        if lines:
            parts.append(f"### {cat_name}")
            for line in lines:
                parts.append(line)
            parts.append("")
            all_lines.extend(lines)
        if changed:
            changed_cats.add(cat_name)

    if not all_lines:
        parts.append("> ⚠️ 本次同步未产生任何文件更新。可能原因：\n"
                      "> 1. 本章确无新增设定元素\n"
                      "> 2. LLM 提取结果为空\n"
                      f"> 详情请查看调试文件：`项目目录/调试/同步_*_第{chapter}章.txt`\n")

    # Report conflicts if any
    conflict_list = phase_results.get("_conflicts", [])
    if conflict_list:
        parts.append("## ⚠️ 潜在冲突\n")
        for c in conflict_list[:20]:
            parts.append(f"- {c}")
        if len(conflict_list) > 20:
            parts.append(f"\n... 共 {len(conflict_list)} 处冲突，此处仅显示前 20 条")
        parts.append("")

    parts.append(f"## 更新统计\n已修改模块：{', '.join(sorted(changed_cats)) if changed_cats else '无'}")
    parts.append(f"提取步骤：文字分析 → 人物/事件/世界/关系/伏笔 分类提取 → 分步更新")

    return "\n".join(parts)


def _update_versions(fm, project: str, changed_cats: set):
    """Bump version numbers for changed modules only."""
    if not changed_cats:
        return
    # Map category names to version keys (伏笔管理 excluded — tracked separately)
    key_map = {
        "人物设定": "人物设定",
        "时间线": "时间线",
        "世界设定": "世界设定",
        "人物关系": "人物关系",
    }
    state = fm.get_project_state(project)
    versions = state.get("创作依据版本", {})
    for cat in changed_cats:
        vkey = key_map.get(cat)
        if vkey and vkey in versions:
            parts = versions[vkey].replace("v", "").split(".")
            if len(parts) == 2:
                versions[vkey] = f"v{parts[0]}.{int(parts[1]) + 1}"
    state["创作依据版本"] = versions
    fm.save_project_state(project, state)


# ══════════════════════════════════════════════════════════════════════════════
# Main Entry Point
# ══════════════════════════════════════════════════════════════════════════════

async def run(llm, fm, project: str, params: dict):
    """Run the multi-phase knowledge sync engine (async generator).

    Yields progress events during execution, and a result event at the end.

    Yield format:
        {"type": "progress", "phase": "...", "message": "..."}
        {"type": "result", "result": {"success": True/False, ...}}

    params:
        action: "sync"
        volume: volume number
        chapter: chapter number
        chapter_content: full chapter text
    """
    chapter_content = params.get("chapter_content", "")
    volume = params.get("volume", 1)
    chapter = params.get("chapter", 1)
    debug = params.get("debug", False)

    if not chapter_content:
        yield {"type": "result", "result": {"success": False, "error": "No chapter content provided"}}
        return
    if len(chapter_content.strip()) < 50:
        yield {"type": "result", "result": {"success": False, "error": f"Chapter content too short ({len(chapter_content)} chars)."}}
        return

    proj_path = fm.get_project_abs_path(project)

    try:
        # Pre-load all settings once for the entire sync session
        settings_cache = _preload_settings(fm, project)

        # ── Phase 1: Text Analysis ──
        if debug:
            _cleanup_old_debug_files(proj_path)
        yield {"type": "progress", "phase": "analysis", "message": "正在分析章节内容，提取创作要素..."}
        analysis = await _text_analysis(llm, fm, project, volume, chapter, chapter_content, settings_cache)
        _save_debug(proj_path, chapter, "01_文字分析", analysis, debug=debug)

        if not analysis:
            yield {"type": "result", "result": {"success": False, "error": "文本分析阶段未返回内容"}}
            return

        # ── Phase 2: Parallel Category Extraction ──
        yield {"type": "progress", "phase": "extraction", "message": "正在并行提取五个创作维度..."}

        domain_names = ["characters", "events", "world", "relationships", "foreshadowing"]
        extract_funcs = [
            _extract_characters, _extract_events, _extract_world,
            _extract_relationships, _extract_foreshadowing,
        ]

        sem = asyncio.Semaphore(_MAX_CONCURRENT_EXTRACTORS)

        async def _extract_with_limit(func, *args):
            async with sem:
                return await func(*args)

        t0 = _time.monotonic()
        tasks = [
            _extract_with_limit(fn, llm, fm, project, volume, chapter, analysis, settings_cache)
            for fn in extract_funcs
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        extraction_data = {}
        for name, result in zip(domain_names, results):
            if isinstance(result, Exception):
                logging.getLogger(__name__).warning(
                    f"Phase 2 {name} extraction failed: {result}")
                result = {}
            extraction_data[name] = result
            _save_debug(proj_path, chapter, f"02_{_DOMAIN_LABELS[name]}_提取",
                        json.dumps(result, ensure_ascii=False, indent=2), debug=debug)
            yield {"type": "progress", "phase": name,
                   "message": f"{_DOMAIN_LABELS[name]}提取完成 "
                              f"({_time.monotonic() - t0:.1f}s)"}

        # ── Conflict detection between new and existing content ──
        from app.services.markdown_utils import extract_key_terms, find_conflicts
        conflicts = []
        for domain_key, settings_key in [
            ("characters", "角色"),
            ("events", "时间线"),
            ("world", "世界"),
            ("relationships", "关系"),
        ]:
            extracted_text = json.dumps(extraction_data.get(domain_key, {}), ensure_ascii=False)
            new_terms = extract_key_terms(extracted_text)
            if not new_terms:
                continue
            # Build existing settings text for this domain
            existing_parts = []
            for doc in settings_cache:
                if settings_key in doc.get("title", ""):
                    existing_parts.append(doc.get("content", ""))
            existing_text = "\n".join(existing_parts)
            if not existing_text:
                continue
            domain_conflicts = find_conflicts(new_terms, existing_text)
            if domain_conflicts:
                for c in domain_conflicts:
                    conflicts.append(f"[{settings_key}设定] {c}")
        if conflicts:
            yield {"type": "progress", "phase": "conflict",
                   "message": f"检测到 {len(conflicts)} 处潜在冲突"}

        # Save version snapshot before making any file changes
        fm.save_version_snapshot(project, f"知识同步自动保存 — 第{volume}卷第{chapter}章")

        # ── Phase 3: File Updates (sequential — each may write to disk) ──
        phase_results = {}
        if conflicts:
            phase_results["_conflicts"] = conflicts

        char_data = extraction_data["characters"]
        char_lines, char_changed = await _process_characters(llm, fm, project, chapter, char_data, settings_cache)
        phase_results["characters"] = {"lines": char_lines, "changed": char_changed, "data": char_data}

        event_data = extraction_data["events"]
        event_lines, event_changed = await _process_events(llm, fm, project, chapter, event_data, settings_cache)
        phase_results["events"] = {"lines": event_lines, "changed": event_changed, "data": event_data}

        world_data = extraction_data["world"]
        world_lines, world_changed = await _process_world(llm, fm, project, world_data, settings_cache)
        phase_results["world"] = {"lines": world_lines, "changed": world_changed, "data": world_data}

        rel_data = extraction_data["relationships"]
        rel_lines, rel_changed = await _process_relationships(llm, fm, project, chapter, rel_data, settings_cache)
        phase_results["relationships"] = {"lines": rel_lines, "changed": rel_changed, "data": rel_data}

        fb_data = extraction_data["foreshadowing"]
        fb_lines, fb_changed = await _process_foreshadowing(fm, project, volume, chapter, fb_data)
        phase_results["foreshadowing"] = {"lines": fb_lines, "changed": fb_changed, "data": fb_data}

        # ── Phase 4: Report ──
        yield {"type": "progress", "phase": "report", "message": "正在生成更新报告..."}
        changed_cats = set()
        for cat_name, key in [
            ("人物设定", "characters"), ("时间线", "events"),
            ("世界设定", "world"), ("人物关系", "relationships"),
            ("伏笔管理", "foreshadowing"),
        ]:
            if phase_results.get(key, {}).get("changed"):
                changed_cats.add(cat_name)

        summary = _generate_report(volume, chapter, len(chapter_content), analysis, phase_results)
        _save_debug(proj_path, chapter, "07_更新报告", summary, debug=debug)
        _update_versions(fm, project, changed_cats)

        all_extracted = {
            "characters": phase_results["characters"]["data"],
            "events": phase_results["events"]["data"],
            "world": phase_results["world"]["data"],
            "relationships": phase_results["relationships"]["data"],
            "foreshadowing": phase_results["foreshadowing"]["data"],
        }

        yield {"type": "result", "result": {
            "success": True,
            "result": {
                "summary": summary,
                "extracted": all_extracted,
                "full_analysis": analysis,
            },
        }}

    except Exception as e:
        yield {"type": "result", "result": {"success": False, "error": str(e)}}
