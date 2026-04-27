"""Timeline management skill.

Creates and maintains background timeline (pre-story history) and
story timeline (events after story begins).
"""

SYSTEM_PROMPT = """你是一位时间线管理员，专精于小说叙事的时间结构管理。

你的任务是根据已有设定和章节内容，创建或更新结构化时间线。

## 背景时间线（故事开始前的世界历史）
输出格式：
```markdown
# 背景时间线

## 远古时代
| 时间 | 事件 | 涉及势力 | 影响 |
|------|------|---------|------|
| 示例 | 世界诞生 | 无 | 奠定基础 |

## 近古时代
...

## 近代
...
```

## 故事时间线（故事开始后的事件记录）
输出格式：
```markdown
# 故事时间线

## 时间轴
| 时间点 | 章节 | 事件 | 涉及人物 | 影响范围 |
|-------|------|------|---------|---------|
| 故事开始 | 第1章 | 主角觉醒 | 主角 | 个人 |
| 第3天 | 第1章 | 入门考核 | 主角、导师 | 门派 |
```

## 重要事件详情
### 事件名称
- 时间：
- 章节：
- 详细描述：
- 参与人物：
- 后续影响：
- 关联伏笔：

规则：
1. 所有内容使用中文
2. 时间点尽量具体（第X天/第X月/第X年）
3. 涉及人物之间用顿号分隔
4. 影响范围：个人/团队/势力/地区/世界
5. 如果是更新模式，在表格末尾追加新行，不修改已有行

---JSON---
在时间线内容之后，附加以下JSON格式的结构化信息：
{
  "background_events": [
    {"time": "时间", "event": "事件", "faction": "势力", "impact": "影响"}
  ],
  "story_events": [
    {"time": "时间点", "chapter": 1, "event": "事件", "characters": ["人物1"], "scope": "个人"}
  ],
  "important_events": [
    {"name": "事件名", "time": "", "chapter": 0, "description": "", "participants": [], "consequences": ""}
  ]
}"""


async def run(llm, fm, project: str, params: dict) -> dict:
    """Run timeline management skill.

    params:
        action: "create" | "add_event" | "query"
        instruction: user's natural language instruction
        existing_bg: current background timeline
        existing_story: current story timeline
        chapter_summary: chapter content (for knowledge-sync-driven update)
    """
    action = params.get("action", "create")
    instruction = params.get("instruction", "")
    existing_bg = params.get("existing_bg")
    existing_story = params.get("existing_story")
    chapter_summary = params.get("chapter_summary")

    context_docs = []
    if existing_bg:
        context_docs.append({"title": "当前背景时间线", "content": existing_bg})
    if existing_story:
        context_docs.append({"title": "当前故事时间线", "content": existing_story})

    # Add all settings for context
    context_docs.extend(fm.get_all_settings(project))

    user_message = instruction

    if chapter_summary:
        user_message = f"以下章节已生成，请从中提取时间线事件并更新：\n\n{chapter_summary}"

    if action == "create" and not existing_bg:
        user_message = f"请根据已有设定创建背景时间线和空的故事时间线框架。{instruction}"

    try:
        result = await llm.chat_with_context_and_json(
            system_prompt=SYSTEM_PROMPT,
            context_docs=context_docs,
            user_message=user_message,
        )
        bg_content = ""
        story_content = ""
        content = result.get("content", "")
        if "背景时间线" in content:
            parts = content.split("# 故事时间线", 1)
            bg_content = parts[0].strip() if parts else ""
            story_content = ("# 故事时间线" + parts[1]).strip() if len(parts) > 1 else ""

        return {
            "success": True,
            "background": bg_content or content,
            "story": story_content,
            "json": result.get("json"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
