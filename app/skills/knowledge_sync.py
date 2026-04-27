"""Knowledge sync engine — the core innovation of the system.

After each chapter is generated, this skill:
1. Parses chapter text to extract entities, events, and changes
2. Fans out to setting skills to update all relevant files
3. Generates an update summary
"""

SYSTEM_PROMPT = """你是一位数据分析师，专精于从小说文本中提取结构化信息。

你的任务是：分析章节内容，提取所有需要更新到创作依据的信息。

## 提取规则

### 1. 新出场人物
识别本章中新出现的人物（之前设定中不存在的）：
- 名称
- 基本描述（外貌、性格、能力等）
- 所属阵营

### 2. 人物状态变化
- 能力变化（新增/升级/失去）
- 性格变化（从A变为B）
- 健康/心理状态变化
- 身份变化
- 所在地变化
- 获得/失去物品

### 3. 新地点
- 名称
- 描述
- 所属区域
- 势力分布

### 4. 事件记录
- 事件名称和描述
- 发生时间
- 参与人物
- 影响范围

### 5. 关系变化
- 两个人物之间的关系类型变化
- 关系状态变化
- 导致变化的事件

### 6. 伏笔线索
- 识别潜在的伏笔（未解之谜、神秘物品、模糊预言等）
- 识别本章回收的伏笔

### 7. 新设定元素
- 新的力量/能力规则
- 新的世界规则
- 新的物品

## 重要
- 只提取本章中新出现或发生变化的信息
- 基于已有设定判断什么是"新"的
- 不确定的标记为"待确认"

## 输出格式

先输出章节分析的文字总结，然后：

---JSON---
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
}"""


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
            max_tokens=4096,
        )

        extracted = result.get("json") or {}
        summary_parts = [f"# 第{chapter}章 更新摘要\n"]
        changed_modules = set()

        # Process extracted data and fan out to skills
        from app.skills.character_design import run as char_skill
        from app.skills.world_design import run as world_skill
        from app.skills.timeline import run as timeline_skill
        from app.skills.relationship import run as rel_skill
        from app.skills.writing_assist import run as assist_skill

        # Process new characters
        new_chars = extracted.get("new_characters", [])
        for nc in new_chars:
            char_name = nc.get("name", "")
            if char_name:
                char_result = await char_skill(llm, fm, project, {
                    "action": "create",
                    "instruction": f"创建角色：{char_name}，描述：{nc.get('description', '')}，阵营：{nc.get('faction', '')}",
                    "char_name": char_name,
                })
                if char_result.get("success"):
                    fm.write_character(project, char_result["char_name"], char_result["content"])
                    changed_modules.add("人物设定")
                    summary_parts.append(f"- 新人物：{char_result['char_name']}")

        # Process character updates
        char_updates = extracted.get("character_updates", [])
        for cu in char_updates:
            char_name = cu.get("name", "")
            if char_name:
                existing = fm.read_character(project, char_name)
                if existing:
                    update_result = await char_skill(llm, fm, project, {
                        "action": "update",
                        "instruction": f"更新{cu.get('field', '')}：{cu.get('change', '')}，详情：{cu.get('detail', '')}",
                        "char_name": char_name,
                        "existing_content": existing,
                    })
                    if update_result.get("success"):
                        fm.write_character(project, char_name, update_result["content"])
                        changed_modules.add("人物设定")
                        summary_parts.append(f"- {char_name}：{cu.get('change', '')}")

        # Process new locations
        new_locs = extracted.get("new_locations", [])
        for nl in new_locs:
            summary_parts.append(f"- 新区域：{nl.get('name', '')}")

        # Process new world info
        new_world = extracted.get("new_world_info", {})
        if new_world.get("new_rules") or new_world.get("new_items") or new_world.get("new_powers") or new_locs:
            existing_world = fm.read_world_setting(project) or ""
            world_result = await world_skill(llm, fm, project, {
                "action": "update",
                "instruction": f"本章新增元素：{json.dumps(new_world, ensure_ascii=False)}",
                "existing_content": existing_world,
            })
            if world_result.get("success"):
                fm.write_world_setting(project, world_result["content"])
                changed_modules.add("世界设定")

        # Process new events → update story timeline
        new_events = extracted.get("new_events", [])
        if new_events:
            timeline_result = await timeline_skill(llm, fm, project, {
                "action": "add_event",
                "instruction": f"添加以下事件：{json.dumps(new_events, ensure_ascii=False)}",
                "existing_bg": fm.read_background_timeline(project),
                "existing_story": fm.read_story_timeline(project),
            })
            if timeline_result.get("success"):
                if timeline_result.get("story"):
                    fm.write_story_timeline(project, timeline_result["story"])
                if timeline_result.get("background"):
                    fm.write_background_timeline(project, timeline_result["background"])
                changed_modules.add("时间线")

        # Process relationship changes
        rel_changes = extracted.get("relationship_changes", [])
        if rel_changes:
            existing_rel = fm.read_relationship(project) or ""
            rel_result = await rel_skill(llm, fm, project, {
                "action": "update",
                "instruction": f"关系变化：{json.dumps(rel_changes, ensure_ascii=False)}",
                "existing_content": existing_rel,
            })
            if rel_result.get("success"):
                fm.write_relationship(project, rel_result["content"])
                changed_modules.add("人物关系")

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
                "full_analysis": result.get("content", ""),
            },
        }
    except Exception as e:
        import json
        return {"success": False, "error": str(e)}
