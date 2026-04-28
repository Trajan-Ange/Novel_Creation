"""Knowledge sync engine — the core innovation of the system.

Workflow:
  Phase 1: Text analysis (1 LLM call — free-text, no JSON)
  Phase 2: Category extraction (5 LLM calls — focused JSON per domain)
  Phase 3: File updates (fan-out to skills or direct write)
  Phase 4: Update report

Each phase has its own system prompt and JSON schema, preventing
the output truncation that occurred with the monolithic approach.
"""

import json
import os

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
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _save_debug(proj_path: str, chapter: int, phase: str, content: str):
    """Save intermediate results for diagnosis."""
    try:
        debug_dir = os.path.join(proj_path, "调试")
        os.makedirs(debug_dir, exist_ok=True)
        path = os.path.join(debug_dir, f"同步_{phase}_第{chapter}章.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
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
        import logging
        logging.getLogger(__name__).warning(f"LLM call failed in sync phase: {e}")
        return {"content": "", "json": None}


def _existing_char_names(fm, project: str) -> list[str]:
    """Get list of existing character names for the project."""
    return fm.list_characters(project)


# ══════════════════════════════════════════════════════════════════════════════
# Phase 1: Text Analysis
# ══════════════════════════════════════════════════════════════════════════════

async def _text_analysis(llm, fm, project: str, volume: int, chapter: int,
                         chapter_content: str) -> str:
    """Read chapter, produce detailed markdown analysis."""
    context_docs = fm.get_all_settings(project)
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
                              analysis: str) -> dict:
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
    result = await _call_llm(llm, CHARACTER_PROMPT, context, user_msg, max_tokens=8192)
    return result.get("json") or {}


async def _extract_events(llm, fm, project: str, volume: int, chapter: int,
                          analysis: str) -> dict:
    """Extract timeline events from analysis."""
    existing_story = fm.read_story_timeline(project) or ""
    context = [
        {"title": "章节分析报告", "content": analysis},
    ]
    if existing_story:
        context.append({"title": "当前故事时间线（参考）", "content": existing_story[-2000:]})
    user_msg = f"请根据分析报告，提取第{volume}卷第{chapter}章中发生的重要事件。"
    result = await _call_llm(llm, EVENT_PROMPT, context, user_msg, max_tokens=8192)
    return result.get("json") or {}


async def _extract_world(llm, fm, project: str, volume: int, chapter: int,
                         analysis: str) -> dict:
    """Extract new locations and world info from analysis."""
    existing_world = fm.read_world_setting(project) or ""
    context = [
        {"title": "章节分析报告", "content": analysis},
    ]
    if existing_world:
        context.append({"title": "当前世界设定（参考）", "content": existing_world[-3000:]})
    user_msg = f"请根据分析报告，提取第{volume}卷第{chapter}章中出现的新地点和世界设定元素。"
    result = await _call_llm(llm, WORLD_PROMPT, context, user_msg, max_tokens=8192)
    return result.get("json") or {}


async def _extract_relationships(llm, fm, project: str, volume: int, chapter: int,
                                 analysis: str) -> dict:
    """Extract relationship changes from analysis."""
    existing_rel = fm.read_relationship(project) or ""
    context = [
        {"title": "章节分析报告", "content": analysis},
    ]
    if existing_rel:
        context.append({"title": "当前人物关系（参考）", "content": existing_rel[-2000:]})
    user_msg = f"请根据分析报告，提取第{volume}卷第{chapter}章中的人物关系变化。"
    result = await _call_llm(llm, RELATIONSHIP_PROMPT, context, user_msg, max_tokens=8192)
    return result.get("json") or {}


async def _extract_foreshadowing(llm, fm, project: str, volume: int, chapter: int,
                                 analysis: str) -> dict:
    """Extract foreshadowing from analysis."""
    existing_fb = fm.read_foreshadowing_list(project) or ""
    context = [
        {"title": "章节分析报告", "content": analysis},
    ]
    if existing_fb:
        context.append({"title": "当前伏笔清单（参考）", "content": existing_fb[-2000:]})
    user_msg = f"请根据分析报告，提取第{volume}卷第{chapter}章中埋设的新伏笔和回收的旧伏笔。"
    result = await _call_llm(llm, FORESHADOWING_PROMPT, context, user_msg, max_tokens=8192)
    return result.get("json") or {}


# ══════════════════════════════════════════════════════════════════════════════
# Phase 3: File Updates
# ══════════════════════════════════════════════════════════════════════════════

async def _process_characters(llm, fm, project: str, chapter: int, data: dict) -> list:
    """Create new characters and update existing ones. Returns summary lines."""
    from app.skills.character_design import run as char_skill

    lines = []
    changed = False

    # New characters
    for nc in data.get("new_characters", []):
        try:
            name = nc.get("name", "") if isinstance(nc, dict) else str(nc)
            if not name:
                continue
            desc = nc.get("description", "") if isinstance(nc, dict) else ""
            faction = nc.get("faction", "") if isinstance(nc, dict) else ""
            result = await char_skill(llm, fm, project, {
                "action": "create",
                "instruction": f"创建角色：{name}，描述：{desc}，阵营：{faction}",
                "char_name": name,
            })
            if result.get("success"):
                fm.write_character(project, result["char_name"], result["content"])
                changed = True
                lines.append(f"- 新人物：{result['char_name']}")
        except Exception as e:
            lines.append(f"- 新人物处理失败（{nc}）：{e}")

    # Character updates
    for cu in data.get("character_updates", []):
        try:
            name = cu.get("name", "") if isinstance(cu, dict) else str(cu)
            if not name:
                continue
            existing = fm.read_character(project, name)
            if not existing:
                # Character doesn't exist yet — treat as new
                result = await char_skill(llm, fm, project, {
                    "action": "create",
                    "instruction": f"创建角色：{name}",
                    "char_name": name,
                })
                if result.get("success"):
                    fm.write_character(project, name, result["content"])
                    changed = True
                    lines.append(f"- 自动创建角色：{name}（原为更新目标但角色不存在）")
                continue

            field = cu.get("field", "") if isinstance(cu, dict) else ""
            change = cu.get("change", "") if isinstance(cu, dict) else ""
            detail = cu.get("detail", "") if isinstance(cu, dict) else ""
            result = await char_skill(llm, fm, project, {
                "action": "update",
                "instruction": f"更新{field}：{change}，详情：{detail}",
                "char_name": name,
                "existing_content": existing,
            })
            if result.get("success"):
                fm.write_character(project, name, result["content"])
                changed = True
                lines.append(f"- {name}：{change}")
        except Exception as e:
            lines.append(f"- 人物更新处理失败（{cu}）：{e}")

    return lines, changed


async def _process_events(llm, fm, project: str, data: dict) -> list:
    """Update story timeline with new events. Returns summary lines."""
    from app.skills.timeline import run as timeline_skill

    lines = []
    events = data.get("new_events", [])
    if not events:
        return lines, False

    try:
        result = await timeline_skill(llm, fm, project, {
            "action": "add_event",
            "instruction": f"添加以下事件：{json.dumps(events, ensure_ascii=False)}",
            "existing_bg": fm.read_background_timeline(project),
            "existing_story": fm.read_story_timeline(project),
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


async def _process_world(llm, fm, project: str, data: dict) -> list:
    """Update world setting. Returns summary lines."""
    from app.skills.world_design import run as world_skill

    lines = []
    new_world = data.get("new_world_info", {})
    new_locs = data.get("new_locations", [])

    # Log locations even though we don't have a separate locations file
    for nl in new_locs:
        name = nl.get("name", "") if isinstance(nl, dict) else str(nl)
        if name:
            lines.append(f"- 新区域：{name}")

    if isinstance(new_world, dict) and (
        new_world.get("new_rules") or new_world.get("new_items") or
        new_world.get("new_powers")
    ):
        try:
            existing = fm.read_world_setting(project) or ""
            result = await world_skill(llm, fm, project, {
                "action": "update",
                "instruction": f"本章新增元素：{json.dumps(new_world, ensure_ascii=False)}",
                "existing_content": existing,
            })
            if result.get("success"):
                fm.write_world_setting(project, result["content"])
                lines.append("- 世界设定已更新")
                return lines, True
        except Exception as e:
            lines.append(f"- 世界设定更新失败：{e}")

    return lines, bool(new_locs)


async def _process_relationships(llm, fm, project: str, data: dict) -> list:
    """Update relationship map. Returns summary lines."""
    from app.skills.relationship import run as rel_skill

    lines = []
    changes = data.get("relationship_changes", [])
    if not changes:
        return lines, False

    try:
        existing = fm.read_relationship(project) or ""
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


def _process_foreshadowing(fm, project: str, volume: int, chapter: int, data: dict) -> list:
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
            fm.write_foreshadowing_detail(project, fb_id, detail)
            lines.append(f"- 伏笔埋设：{fb_content[:50]}...（{fb_id}）")

    # Recovered foreshadowing
    for rfb in data.get("recovered_foreshadowing", []):
        fb_id = rfb.get("id", "") if isinstance(rfb, dict) else str(rfb)
        if fb_id:
            existing = fm.read_foreshadowing_detail(project, fb_id)
            if existing:
                how = rfb.get("how", "") if isinstance(rfb, dict) else ""
                updated = existing.replace("待回收", "已回收")
                updated += f"\n- 回收章节：第{chapter}章\n- 回收方式：{how}\n"
                fm.write_foreshadowing_detail(project, fb_id, updated)
                lines.append(f"- 伏笔回收：{fb_id}（{how}）")
                state = fm.get_project_state(project)
                pending = state.get("待回收伏笔", [])
                if fb_id in pending:
                    pending.remove(fb_id)
                    state["待回收伏笔"] = pending
                    fm.save_project_state(project, state)

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

    if not chapter_content:
        yield {"type": "result", "result": {"success": False, "error": "No chapter content provided"}}
        return
    if len(chapter_content.strip()) < 50:
        yield {"type": "result", "result": {"success": False, "error": f"Chapter content too short ({len(chapter_content)} chars)."}}
        return

    proj_path = fm._project_path(project)

    try:
        # ── Phase 1: Text Analysis ──
        yield {"type": "progress", "phase": "analysis", "message": "正在分析章节内容，提取创作要素..."}
        analysis = await _text_analysis(llm, fm, project, volume, chapter, chapter_content)
        _save_debug(proj_path, chapter, "01_文字分析", analysis)

        if not analysis:
            yield {"type": "result", "result": {"success": False, "error": "文本分析阶段未返回内容"}}
            return

        # ── Phase 2+3: Category Extraction + File Updates ──
        phase_results = {}

        # 2a+3a: Characters
        yield {"type": "progress", "phase": "characters", "message": "正在提取人物信息并更新角色设定..."}
        char_data = await _extract_characters(llm, fm, project, volume, chapter, analysis)
        _save_debug(proj_path, chapter, "02_人物提取", json.dumps(char_data, ensure_ascii=False, indent=2))
        char_lines, char_changed = await _process_characters(llm, fm, project, chapter, char_data)
        phase_results["characters"] = {"lines": char_lines, "changed": char_changed, "data": char_data}

        # 2b+3b: Events
        yield {"type": "progress", "phase": "events", "message": "正在提取事件并更新时间线..."}
        event_data = await _extract_events(llm, fm, project, volume, chapter, analysis)
        _save_debug(proj_path, chapter, "03_事件提取", json.dumps(event_data, ensure_ascii=False, indent=2))
        event_lines, event_changed = await _process_events(llm, fm, project, event_data)
        phase_results["events"] = {"lines": event_lines, "changed": event_changed, "data": event_data}

        # 2c+3c: World
        yield {"type": "progress", "phase": "world", "message": "正在提取世界设定并更新..."}
        world_data = await _extract_world(llm, fm, project, volume, chapter, analysis)
        _save_debug(proj_path, chapter, "04_世界提取", json.dumps(world_data, ensure_ascii=False, indent=2))
        world_lines, world_changed = await _process_world(llm, fm, project, world_data)
        phase_results["world"] = {"lines": world_lines, "changed": world_changed, "data": world_data}

        # 2d+3d: Relationships
        yield {"type": "progress", "phase": "relationships", "message": "正在提取关系变化并更新人物关系..."}
        rel_data = await _extract_relationships(llm, fm, project, volume, chapter, analysis)
        _save_debug(proj_path, chapter, "05_关系提取", json.dumps(rel_data, ensure_ascii=False, indent=2))
        rel_lines, rel_changed = await _process_relationships(llm, fm, project, rel_data)
        phase_results["relationships"] = {"lines": rel_lines, "changed": rel_changed, "data": rel_data}

        # 2e+3e: Foreshadowing
        yield {"type": "progress", "phase": "foreshadowing", "message": "正在提取伏笔信息..."}
        fb_data = await _extract_foreshadowing(llm, fm, project, volume, chapter, analysis)
        _save_debug(proj_path, chapter, "06_伏笔提取", json.dumps(fb_data, ensure_ascii=False, indent=2))
        fb_lines, fb_changed = _process_foreshadowing(fm, project, volume, chapter, fb_data)
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
        _save_debug(proj_path, chapter, "07_更新报告", summary)
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
