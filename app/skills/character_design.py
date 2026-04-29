"""Character design skill.

Creates and updates character profiles with abilities, items,
experiences, status tracking, and growth trajectory.
"""

import logging
logger = logging.getLogger(__name__)

from app.services.context_builder import get_truncated_settings
from app.services.skill_result import SkillResult

SYSTEM_PROMPT = """你是一位资深角色设计师，专精于网络小说的人物塑造。

你的任务是创建或更新结构化的角色设定档案。

输出必须是有效的Markdown格式，包含以下章节：

## 基本信息
- 姓名：
- 年龄：
- 性别：
- 身份/职业：
- 阵营/所属势力：

## 外貌特征
[详细的外貌描述，包括身高、体型、面容、常用服饰等]

## 性格特点
[详细的性格描述，包括优点、缺点、习惯、偏好等]

## 能力设定
### 已拥有能力
- 能力名称：[等级/熟练度/描述]
- ...

### 特殊天赋
- 天赋名称：描述、觉醒条件、发展潜力

### 战斗风格
[偏好的战斗方式、常用招数、战斗习惯]

## 物品装备
- 物品名称：描述、来源、品质/等级

## 重要经历
| 时间/章节 | 事件 | 状态变化 |
|----------|------|---------|
| 示例 | 觉醒能力 | 新增：某能力 |

## 当前状态
- 所在地：
- 健康状况：
- 心理状态：
- 当前目标：
- 当前困境：

## 人物关系
[与其他人物的关系简述]

## 成长轨迹
[角色的成长方向和发展预期]

## 备注
[其他重要信息，如秘密、弱���、特殊设定等]

规则：
1. 所有内容使用中文
2. 使用具体细节，避免模糊描述
3. 基本信息、能力设定使用列表格式，方便检索
4. 如果是更新模式，保留已有信息，仅修改变化的部分
5. 重要经历表按时间顺序排列

---JSON---
在角色档案的markdown内容之后，附加以下JSON格式的结构化信息（用于程序化更新）：
{
  "name": "角色名",
  "basic_info": {"age": null, "gender": "男/女", "faction": ""},
  "abilities": ["能力1", "能力2"],
  "items": ["物品1", "物品2"],
  "current_status": {"location": "", "health": "", "mental_state": "", "goal": ""},
  "new_experiences": [{"chapter": 1, "event": "事件描述", "change": "变化描述"}]
}"""


async def run(llm, fm, project: str, params: dict) -> dict:
    """Run character design skill.

    params:
        action: "create" | "update" | "query"
        instruction: user's natural language instruction
        char_name: character name
        existing_content: current character profile (for update)
        chapter_summary: chapter content (for knowledge-sync-driven update)
    """
    action = params.get("action", "create")
    instruction = params.get("instruction", "")
    char_name = params.get("char_name", "新角色")
    existing_content = params.get("existing_content")
    chapter_summary = params.get("chapter_summary")

    context_docs = []
    user_message = instruction

    if action == "update" and existing_content:
        context_docs.append({"title": f"当前人物设定：{char_name}（需要更新）", "content": existing_content})

    if chapter_summary:
        user_message = f"以下章节已生成，请从中提取关于{char_name}的新信息并更新人物设定：\n\n{chapter_summary}"

    if action == "create":
        context_docs = get_truncated_settings(fm, project)
        user_message = f"请为以下角色创建完整的设定档案：{instruction}"

    try:
        result = await llm.chat_with_context_and_json(
            system_prompt=SYSTEM_PROMPT,
            context_docs=context_docs,
            user_message=user_message,
        )
        json_data = result.get("json")
        resolved_name = char_name
        if json_data and json_data.get("name"):
            resolved_name = json_data["name"]
        return SkillResult(success=True, content=result["content"], char_name=resolved_name, json=json_data)
    except Exception as e:
        logger.exception("角色设定生成失败")
        return SkillResult(success=False, error=str(e))
