"""World setting design skill.

Creates and updates structured world setting documents with geography,
"""

import logging
logger = logging.getLogger(__name__)

from app.services.skill_result import SkillResult

"""
factions, power systems, rules, and important items.
"""

SYSTEM_PROMPT = """你是一位资深的世界设定设计师，专精于网络小说的世界观构建。

你的任务是创建或更新结构化的世界设定文档。

输出必须是有效的Markdown格式，包含以下章节：
## 世界背景
[描述世界整体的背景、历史、核心冲突等]

## 地理区域
### 区域名称
- 位置：
- 特征：
- 势力分布：
- 资源特产：
- 特殊规则：

## 势力组织
### 势力名称
- 性质：（宗门/国家/组织/家族等）
- 领导者：
- 核心成员：
- 目标理念：
- 实力规模：
- 与其他势力关系：

## 力量体系
### 等级划分
（详细的等级体系，每个等级的特点和能力范围）

### 特殊能力/技能
- 能力名称：描述、所属体系、限制条件

## 世界规则
- 规则描述（物理法则、魔法规则、禁忌等）

## 重要物品
- 物品名称：描述、来源、能力、当前归属

规则：
1. 所有内容使用中文
2. 使用具体细节，避免模糊描述
3. 保持内部一致性
4. 如果是更新模式，只修改与新信息相关的章节，不重写整个文档
5. 如果有新元素与已有设定矛盾，用 <!-- 冲突提示：描述 --> 标记

输出时，对于可能需要程序化访问的结构化信息（如势力列表、等级名称），确保使用一致的格式。"""


async def run(llm, fm, project: str, params: dict) -> dict:
    """Run world design skill.

    params:
        action: "create" | "update" | "query"
        instruction: user's natural language instruction
        existing_content: current world setting (for update)
        chapter_summary: chapter content (for knowledge-sync-driven update)
    """
    action = params.get("action", "create")
    instruction = params.get("instruction", "")
    existing_content = params.get("existing_content")
    chapter_summary = params.get("chapter_summary")

    context_docs = []
    user_message = instruction

    if action == "update" and existing_content:
        context_docs.append({"title": "当前世界设定（需要更新）", "content": existing_content})

    if chapter_summary:
        user_message = f"以下章节已生成，请从中提取新的世界设定信息并更新世界设定文档：\n\n{chapter_summary}"

    if action == "query":
        user_message = f"请根据世界设定回答以下问题：{instruction}"

    try:
        result = await llm.chat_with_context_and_json(
            system_prompt=SYSTEM_PROMPT,
            context_docs=context_docs,
            user_message=user_message,
        )
        return SkillResult(success=True, content=result["content"], data={"json": result.get("json")})
    except Exception as e:
        logger.exception("世界设定生成失败")
        return SkillResult(success=False, error=str(e))
