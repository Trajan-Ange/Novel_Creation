"""Knowledge sync engine — the core innovation of the system.

After each chapter is generated, this skill:
1. Parses chapter text to extract entities, events, and changes
2. Fans out to setting skills to update all relevant files
3. Generates an update summary
"""

import json
import os

SYSTEM_PROMPT = """你是一位数据分析师，专精于从小说文本中提取结构化信息。

你的任务是：仔细分析章节内容，提取所有值得记录的信息，用于更新创作依据。

## 提取规则

### 1. 出场人物（无论新旧）
识别本章中出现的所有人物，特别是：
- 首次登场的角色（名称、外貌、性格、能力、阵营）
- 已知角色的新信息（能力变化、性格发展、新身份等）

### 2. 人物状态变化
- 能力变化（新增/升级/失去）
- 性格变化
- 健康/心理状态变化
- 身份变化
- 所在地变化
- 获得/失去物品

### 3. 地点
- 新出现的场景/地点名称和描述
- 所属区域

### 4. 事件记录
- 本章发生的重要事件
- 涉及人物
- 影响范围

### 5. 关系变化
- 人物之间关系的确立/变化/深化

### 6. 伏笔线索
- 本章埋下的伏笔（未解之谜、神秘物品、模糊预言等）
- 本章回收的前文伏笔

### 7. 新设定元素
- 新的力量/能力规则
- 新的世界规则
- 新的重要物品

## 重要原则
- 即使已有设定中已存在的人物，只要本章中有新的表现或信息，也应该记录
- 宁可多提取，不要遗漏
- 不确定的项目也可以列出，标记为"待确认"

## 输出格式（必须严格遵守）

**第一步：** 先输出详细的章节分析，逐条列出你识别到的所有人、事、物、变化。这部分是你实际分析的成果，必须包含具体内容。

**第二步：** 然后输出一个 JSON 代码块。JSON 必须用 ```json 和 ``` 包裹，格式如下：

```json
{
  "new_characters": [
    {"name": "角色名", "description": "描述", "faction": "阵营"}
  ],
  "character_updates": [
    {"name": "角色名", "field": "能力设定", "change": "新增剑道天赋", "detail": "详细描述"}
  ],
  "new_locations": [
    {"name": "地名", "description": "描述", "region": "所属区域"}
  ],
  "new_events": [
    {"time": "时间点", "event": "事件描述", "characters": ["人物"], "scope": "个人/势力/世界"}
  ],
  "relationship_changes": [
    {"char_a": "角色A", "char_b": "角色B", "type": "师徒", "status": "友好", "trigger_event": "事件", "previous": "陌生"}
  ],
  "new_foreshadowing": [
    {"content": "伏笔描述", "related_characters": [], "suggested_recovery_chapter": null}
  ],
  "recovered_foreshadowing": [
    {"id": "FB-001-01", "how": "回收方式描述"}
  ],
  "new_world_info": {
    "new_rules": [],
    "new_items": [],
    "new_powers": []
  },
  "conflicts": [
    {"description": "与新设定矛盾的地方", "severity": "high/medium/low"}
  ]
}
```

**关键要求：**
- 没有对应内容的字段返回空数组 []，但不能所有字段都为空
- JSON 代码块必须完整且可解析
- 不要省略任何顶层字段"""


async def run(llm, fm, project: str, params: dict) -> dict:
    """Run knowledge sync engine.

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
        return {"success": False, "error": "No chapter content provided"}

    if len(chapter_content.strip()) < 50:
        return {"success": False, "error": f"Chapter content too short ({len(chapter_content)} chars). Cannot extract meaningful information."}

    # Build context from existing settings
    context_docs = fm.get_all_settings(project)
    chapter_outline = fm.read_chapter_outline(project, volume, chapter)
    if chapter_outline:
        context_docs.insert(0, {"title": "本章大纲（参考）", "content": chapter_outline})

    user_message = f"请分析以下第{volume}卷第{chapter}章的正文，提取所有需要更新到创作依据的信息：\n\n{chapter_content}"

    try:
        result = await llm.chat_with_context_and_json(
            system_prompt=SYSTEM_PROMPT,
            context_docs=context_docs,
            user_message=user_message,
            max_tokens=8192,
        )

        raw_response = result.get("content", "")
        extracted = result.get("json") or {}

        # ── Debug: save raw LLM response for diagnosis ──
        try:
            proj_path = fm._project_path(project)
            debug_dir = os.path.join(proj_path, "调试")
            os.makedirs(debug_dir, exist_ok=True)
            debug_path = os.path.join(debug_dir, f"同步原始响应_第{chapter}章.txt")
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(f"=== RAW RESPONSE (content) ===\n{raw_response}\n\n")
                f.write(f"=== PARSED JSON ===\n{json.dumps(extracted, ensure_ascii=False, indent=2)}\n")
        except Exception:
            pass  # Debug file is best-effort, don't crash sync for it

        summary_parts = [f"# 第{chapter}章 更新摘要\n"]
        changed_modules = set()

        # Stats
        summary_parts.append(f"\n**章节字数：** {len(chapter_content)} 字符")
        summary_parts.append(f"**已有设定文档数：** {len(context_docs)}")

        # Include LLM's text analysis in the summary
        if raw_response:
            # Show first portion of analysis
            analysis_text = raw_response[:3000]
            if len(raw_response) > 3000:
                analysis_text += "\n\n...（分析内容已截断，完整内容见调试文件）"
            summary_parts.append(f"\n## AI 分析\n{analysis_text}\n")

        # Show extracted JSON summary
        if extracted:
            json_summary_lines = []
            for key, val in extracted.items():
                if isinstance(val, list):
                    json_summary_lines.append(f"- {key}: {len(val)} 项")
                elif isinstance(val, dict):
                    non_empty = sum(1 for v in val.values() if v)
                    json_summary_lines.append(f"- {key}: {non_empty} 个非空字段")
                else:
                    json_summary_lines.append(f"- {key}: {val}")
            summary_parts.append(f"## 提取数据概览\n" + "\n".join(json_summary_lines) + "\n")
        else:
            summary_parts.append("\n## 提取数据概览\n> **JSON 解析完全失败** — LLM 未返回可解析的 JSON 数据。请查看调试文件。\n")

        # Warn if no structured data extracted
        if not extracted or not any(v for v in extracted.values() if v):
            summary_parts.append("\n> ⚠️ 未提取到结构化数据。可能原因：\n> 1. LLM 输出格式不符合 JSON 规范\n> 2. 章节中确实没有值得提取的新信息\n> 3. 模型能力不足，未能识别隐含信息\n> \n> 调试文件已保存至：`项目目录/调试/同步原始响应_第{ch}章.txt`\n".replace("{ch}", str(chapter)))

        # Process extracted data and fan out to skills
        from app.skills.character_design import run as char_skill
        from app.skills.world_design import run as world_skill
        from app.skills.timeline import run as timeline_skill
        from app.skills.relationship import run as rel_skill
        from app.skills.writing_assist import run as assist_skill

        # Process new characters
        new_chars = extracted.get("new_characters", [])
        for nc in new_chars:
            try:
                char_name = nc.get("name", "") if isinstance(nc, dict) else str(nc)
                if char_name:
                    desc = nc.get("description", "") if isinstance(nc, dict) else ""
                    faction = nc.get("faction", "") if isinstance(nc, dict) else ""
                    char_result = await char_skill(llm, fm, project, {
                        "action": "create",
                        "instruction": f"创建角色：{char_name}，描述：{desc}，阵营：{faction}",
                        "char_name": char_name,
                    })
                    if char_result.get("success"):
                        fm.write_character(project, char_result["char_name"], char_result["content"])
                        changed_modules.add("人物设定")
                        summary_parts.append(f"- 新人物：{char_result['char_name']}")
            except Exception as e:
                summary_parts.append(f"- 新人物处理失败（{nc}）：{e}")

        # Process character updates
        char_updates = extracted.get("character_updates", [])
        for cu in char_updates:
            try:
                char_name = cu.get("name", "") if isinstance(cu, dict) else str(cu)
                if char_name:
                    existing = fm.read_character(project, char_name)
                    if existing:
                        field = cu.get("field", "") if isinstance(cu, dict) else ""
                        change = cu.get("change", "") if isinstance(cu, dict) else ""
                        detail = cu.get("detail", "") if isinstance(cu, dict) else ""
                        update_result = await char_skill(llm, fm, project, {
                            "action": "update",
                            "instruction": f"更新{field}：{change}，详情：{detail}",
                            "char_name": char_name,
                            "existing_content": existing,
                        })
                        if update_result.get("success"):
                            fm.write_character(project, char_name, update_result["content"])
                            changed_modules.add("人物设定")
                            summary_parts.append(f"- {char_name}：{change}")
            except Exception as e:
                summary_parts.append(f"- 人物更新处理失败（{cu}）：{e}")

        # Process new locations
        new_locs = extracted.get("new_locations", [])
        for nl in new_locs:
            loc_name = nl.get("name", "") if isinstance(nl, dict) else str(nl)
            if loc_name:
                summary_parts.append(f"- 新区域：{loc_name}")

        # Process new world info
        new_world = extracted.get("new_world_info", {})
        if isinstance(new_world, dict) and (new_world.get("new_rules") or new_world.get("new_items") or new_world.get("new_powers") or new_locs):
            try:
                existing_world = fm.read_world_setting(project) or ""
                world_result = await world_skill(llm, fm, project, {
                    "action": "update",
                    "instruction": f"本章新增元素：{json.dumps(new_world, ensure_ascii=False)}",
                    "existing_content": existing_world,
                })
                if world_result.get("success"):
                    fm.write_world_setting(project, world_result["content"])
                    changed_modules.add("世界设定")
                    summary_parts.append("- 世界设定已更新")
            except Exception as e:
                summary_parts.append(f"- 世界设定更新失败：{e}")

        # Process new events → update story timeline
        new_events = extracted.get("new_events", [])
        if new_events:
            try:
                timeline_result = await timeline_skill(llm, fm, project, {
                    "action": "add_event",
                    "instruction": f"添加以下事件：{json.dumps(new_events, ensure_ascii=False)}",
                    "existing_bg": fm.read_background_timeline(project),
                    "existing_story": fm.read_story_timeline(project),
                })
                if timeline_result.get("success"):
                    if timeline_result.get("story"):
                        fm.write_story_timeline(project, timeline_result["story"])
                        summary_parts.append("- 故事时间线已更新")
                    if timeline_result.get("background"):
                        fm.write_background_timeline(project, timeline_result["background"])
                    changed_modules.add("时间线")
                else:
                    summary_parts.append(f"- 时间线更新失败：{timeline_result.get('error')}")
            except Exception as e:
                summary_parts.append(f"- 时间线更新失败：{e}")

        # Process relationship changes
        rel_changes = extracted.get("relationship_changes", [])
        if rel_changes:
            try:
                existing_rel = fm.read_relationship(project) or ""
                rel_result = await rel_skill(llm, fm, project, {
                    "action": "update",
                    "instruction": f"关系变化：{json.dumps(rel_changes, ensure_ascii=False)}",
                    "existing_content": existing_rel,
                })
                if rel_result.get("success"):
                    fm.write_relationship(project, rel_result["content"])
                    changed_modules.add("人物关系")
                    summary_parts.append("- 人物关系已更新")
            except Exception as e:
                summary_parts.append(f"- 人物关系更新失败：{e}")

        # Process foreshadowing
        new_fbs = extracted.get("new_foreshadowing", [])
        for idx, fb in enumerate(new_fbs, start=1):
            fb_content = fb.get("content", "")
            if fb_content:
                fb_id = f"FB-{chapter:03d}-{idx:02d}"
                fb_detail = f"# {fb_id}\n\n- 内容：{fb_content}\n- 埋设章节：第{chapter}章\n- 状态：待回收\n- 涉及人物：{', '.join(fb.get('related_characters', []))}\n- 建议回收章节：{fb.get('suggested_recovery_chapter', '待定')}\n"
                fm.write_foreshadowing_detail(project, fb_id, fb_detail)
                summary_parts.append(f"- 伏笔埋设：{fb_content}（{fb_id}）")

        rec_fbs = extracted.get("recovered_foreshadowing", [])
        for rfb in rec_fbs:
            fb_id = rfb.get("id", "")
            if fb_id:
                existing_detail = fm.read_foreshadowing_detail(project, fb_id)
                if existing_detail:
                    updated_detail = existing_detail.replace("待回收", "已回收")
                    updated_detail += f"\n- 回收章节：第{chapter}章\n- 回收方式：{rfb.get('how', '')}\n"
                    fm.write_foreshadowing_detail(project, fb_id, updated_detail)
                    summary_parts.append(f"- 伏笔回收：{fb_id}（{rfb.get('how', '')}）")
                    # Update project state
                    state = fm.get_project_state(project)
                    pending = state.get("待回收伏笔", [])
                    if fb_id in pending:
                        pending.remove(fb_id)
                        state["待回收伏笔"] = pending
                        fm.save_project_state(project, state)

        # Conflicts
        conflicts = extracted.get("conflicts", [])
        if conflicts:
            summary_parts.append("\n## 冲突警告")
            for c in conflicts:
                summary_parts.append(f"- ⚠️ {c.get('description', '')}（严重程度：{c.get('severity', '')}）")

        # Final stats
        if changed_modules:
            summary_parts.append(f"\n## 更新统计\n已修改模块：{', '.join(sorted(changed_modules))}")
        else:
            summary_parts.append(f"\n## 更新统计\n> 无模块被修改。")

        summary = "\n".join(summary_parts)

        # Update version numbers only for changed modules
        if changed_modules:
            state = fm.get_project_state(project)
            versions = state.get("创作依据版本", {})
            for module_key in changed_modules:
                if module_key in versions:
                    parts = versions[module_key].replace("v", "").split(".")
                    if len(parts) == 2:
                        versions[module_key] = f"v{parts[0]}.{int(parts[1]) + 1}"
            state["创作依据版本"] = versions
            fm.save_project_state(project, state)

        return {
            "success": True,
            "result": {
                "summary": summary,
                "extracted": extracted,
                "full_analysis": raw_response,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
