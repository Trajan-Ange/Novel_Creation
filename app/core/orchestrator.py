"""Main orchestrator — coordinates skills to execute complete workflows.

This module sequences skill calls for the major workflows:
- WF-1: Create project (world + characters + timeline + relationships + outline)
- WF-2: Write chapter (outline -> user confirm -> write -> sync)
- WF-3: Modify & sync (update settings -> check conflicts)
"""


async def create_project_workflow(llm, fm, project: str, description: str) -> dict:
    """WF-1: Initialize a new project with world, characters, timeline, relationships.

    Returns step-by-step progress events.
    """
    from app.skills.world_design import run as world_skill
    from app.skills.character_design import run as char_skill
    from app.skills.timeline import run as timeline_skill
    from app.skills.relationship import run as rel_skill
    from app.skills.outline import run as outline_skill
    from app.skills.writing_assist import run as assist_skill

    steps = []

    try:
        # Step 1: World setting
        steps.append({"step": "world", "status": "running", "message": "正在创建世界设定..."})
        world_result = await world_skill(llm, fm, project, {
            "action": "create",
            "instruction": description,
        })
        if world_result.get("success"):
            fm.write_world_setting(project, world_result["content"])
            steps.append({"step": "world", "status": "done", "message": "世界设定已完成"})
        else:
            steps.append({"step": "world", "status": "error", "message": world_result.get("error")})

        # Step 2: Main characters
        steps.append({"step": "characters", "status": "running", "message": "正在创建主要人物..."})
        char_result = await char_skill(llm, fm, project, {
            "action": "create",
            "instruction": f"请创建主角和主要配角的设定。项目描述：{description}",
            "char_name": "主角",
        })
        if char_result.get("success"):
            fm.write_character(project, char_result["char_name"], char_result["content"])
            steps.append({"step": "characters", "status": "done", "message": f"人物设定已完成：{char_result['char_name']}"})
        else:
            steps.append({"step": "characters", "status": "error", "message": char_result.get("error")})

        # Step 3: Timeline
        steps.append({"step": "timeline", "status": "running", "message": "正在创建时间线..."})
        timeline_result = await timeline_skill(llm, fm, project, {
            "action": "create",
            "instruction": description,
        })
        if timeline_result.get("success"):
            if timeline_result.get("background"):
                fm.write_background_timeline(project, timeline_result["background"])
            if timeline_result.get("story"):
                fm.write_story_timeline(project, timeline_result["story"])
            steps.append({"step": "timeline", "status": "done", "message": "时间线已完成"})
        else:
            steps.append({"step": "timeline", "status": "error", "message": timeline_result.get("error")})

        # Step 4: Relationships
        steps.append({"step": "relationships", "status": "running", "message": "正在创建人物关系..."})
        rel_result = await rel_skill(llm, fm, project, {
            "action": "create",
            "instruction": "请根据已有的人物设定创建人物关系图谱。",
        })
        if rel_result.get("success"):
            fm.write_relationship(project, rel_result["content"])
            steps.append({"step": "relationships", "status": "done", "message": "人物关系已完成"})
        else:
            steps.append({"step": "relationships", "status": "error", "message": rel_result.get("error")})

        # Step 5: Book outline
        steps.append({"step": "outline", "status": "running", "message": "正在创建全书大纲..."})
        outline_result = await outline_skill(llm, fm, project, {
            "action": "create_book",
            "instruction": description,
        })
        if outline_result.get("success"):
            fm.write_book_outline(project, outline_result["content"])
            steps.append({"step": "outline", "status": "done", "message": "全书大纲已完成"})
        else:
            steps.append({"step": "outline", "status": "error", "message": outline_result.get("error")})

        # Step 6: Style guide
        steps.append({"step": "style", "status": "running", "message": "正在收集风格偏好..."})
        style_result = await assist_skill(llm, fm, project, {
            "action": "style_collect",
            "instruction": description,
        })
        if style_result.get("success"):
            fm.write_style_guide(project, style_result["content"])
            steps.append({"step": "style", "status": "done", "message": "风格指南已生成"})

        # Update project state
        state = fm.get_project_state(project)
        state["阶段"] = "大纲创作"
        fm.save_project_state(project, state)

        return {"success": True, "steps": steps}

    except Exception as e:
        return {"success": False, "error": str(e), "steps": steps}


async def apply_extracted_lore(llm, fm, project: str, lore_result: dict) -> dict:
    """Apply extracted lore from lore_extract to project settings files."""
    data = lore_result.get("result", {})
    steps = []

    try:
        # Write world setting
        if data.get("world_setting"):
            fm.write_world_setting(project, data["world_setting"])
            steps.append({"step": "world", "status": "done", "message": "世界设定已导入"})

        # Write character settings
        for char in data.get("character_settings", []):
            fm.write_character(project, char["name"], char["content"])
            steps.append({"step": "character", "status": "done", "message": f"人物已导入：{char['name']}"})

        # Write timeline
        if data.get("timeline"):
            fm.write_background_timeline(project, data["timeline"])
            steps.append({"step": "timeline", "status": "done", "message": "时间线已导入"})

        # Update project state
        state = fm.get_project_state(project)
        state["创作类型"] = "二创"
        state["源作品信息"] = lore_result.get("result", {}).get("json", {}).get("source", "")
        state["阶段"] = "大纲创作"
        fm.save_project_state(project, state)

        return {"success": True, "steps": steps}
    except Exception as e:
        return {"success": False, "error": str(e), "steps": steps}
