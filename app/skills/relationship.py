"""Character relationship management skill.

Creates and updates the relationship graph between characters,
tracking relationship types, states, and change history.
"""

SYSTEM_PROMPT = """你是一位关系网络分析师，专精于小说中的人物关系设计和管理。

你的任务是根据已有设定和章节内容，创建或更新人物关系图谱。

输出必须是有效的Markdown格式：

```markdown
# 人物关系图谱

## 关系概览
当前共有N个角色，形成了以下关系网络。

## 关系详情

### 角色A - 角色B
- 关系类型：（师徒/朋友/仇敌/恋人/家人/同门/上下级/陌生人等）
- 关系状态：（亲密/友好/普通/紧张/敌对/仇恨）
- 建立时间：（第X章/背景设定）
- 关系演变：
  - 初始：描述 → 现在：描述
- 关键事件：
  - 第X章：事件描述
- 备注：

## 关系变化记录
| 变化时间 | 涉及人物 | 变化内容 | 来源章节 |
|---------|---------|---------|---------|
| 示例 | A, B | 陌生 → 师徒 | 第1章 |
```

规则：
1. 所有内容使用中文
2. 只记录已经发生的真实关系变化，不推测未来
3. 关系类型准确，状态描述具体
4. 关键事件按时间顺序排列
5. 如果是更新模式，追加新的关系变化，修改受影响的关系详情

---JSON---
在关系图谱内容之后，附加以下JSON格式：
{
  "relationships": [
    {"chars": ["角色A", "角色B"], "type": "师徒", "status": "友好", "established": "第1章"},
    {"chars": ["角色A", "角色C"], "type": "仇敌", "status": "敌对", "established": "第3章"}
  ],
  "new_changes": [
    {"chars": ["A", "B"], "change": "普通 → 亲密", "trigger": "事件", "chapter": 1}
  ]
}"""


async def run(llm, fm, project: str, params: dict) -> dict:
    """Run relationship management skill.

    params:
        action: "create" | "update" | "query"
        instruction: user's natural language instruction
        existing_content: current relationship document
        chapter_summary: chapter content (for knowledge-sync-driven update)
    """
    action = params.get("action", "create")
    instruction = params.get("instruction", "")
    existing_content = params.get("existing_content")
    chapter_summary = params.get("chapter_summary")

    context_docs = []
    if existing_content:
        context_docs.append({"title": "当前人物关系", "content": existing_content})

    # Add character profiles for reference
    for char_name in fm.list_characters(project):
        content = fm.read_character(project, char_name)
        if content:
            context_docs.append({"title": f"人物设定：{char_name}", "content": content})

    user_message = instruction

    if chapter_summary:
        user_message = f"以下章节已生成，请从中提取人物关系变化并更新关系图谱：\n\n{chapter_summary}"

    if action == "create" and not existing_content:
        user_message = f"请根据已有的人物设定创建人物关系图谱。{instruction}"

    try:
        result = await llm.chat_with_context_and_json(
            system_prompt=SYSTEM_PROMPT,
            context_docs=context_docs,
            user_message=user_message,
        )
        return {"success": True, "content": result["content"], "json": result.get("json")}
    except Exception as e:
        return {"success": False, "error": str(e)}
