"""Chapter writing skill.

Generates chapter prose based on chapter outline and all project settings.
Maintains style consistency and handles foreshadowing integration.
"""

import logging
logger = logging.getLogger(__name__)

from app.services.context_builder import build_chapter_context
from app.services.skill_result import SkillResult

SYSTEM_PROMPT = """你是一位专业网络小说作家，擅长创作引人入胜的长篇小说章节。

## 你的写作准则

### 优先级原则
1. 用户直接指令 > 创作依据各文件 > AI自主发挥
2. 严格遵守已有的世界设定和人物设定
3. 保持与已有章节的风格一致

### 写作要求
1. **设定遵循**：不违背已有的世界设定、人物设定、时间线
2. **人物一致**：每个人物的对话风格、行为模式保持前后一致
3. **细节丰富**：使用具体的场景描写、动作描写、心理描写
4. **节奏控制**：根据章节大纲要求的节奏来写
5. **伏笔处理**：按大纲要求埋设或回收伏笔
6. **对话自然**：对话符合人物性格，推动剧情发展
7. **结尾钩子**：章节结尾要有悬念或吸引力

### 输出格式
直接输出章节正文内容，使用Markdown格式：
- 使用 ## 表示场景分隔
- 对话使用中文引号
- 段落之间保持适当空行
- 字数建议：2000-5000字

### 风格约束
- 使用中文写作
- 叙事流畅，画面感强
- 避免过于口语化
- 避免信息密集的说明性文字，通过场景和对话展现信息

## 注意事项
- 如果前文有伏笔需要回收，在本章适当位置呼应
- 如果本章需要埋设伏笔，用自然的方式铺垫
- 注意与前文的连贯性，必要时通过人物回忆或对话回顾前情
"""


async def run(llm, fm, project: str, params: dict) -> dict:
    """Run chapter writing skill.

    params:
        action: "write"
        volume: volume number
        chapter: chapter number
        instruction: user's additional instructions
        stream: whether to stream output
    """
    action = params.get("action", "write")
    volume = params.get("volume", 1)
    chapter = params.get("chapter", 1)
    instruction = params.get("instruction", "")
    stream = params.get("stream", False)

    # Build truncated context via centralized assembler
    context_docs = build_chapter_context(fm, project, volume, chapter)

    user_message = f"请根据本章大纲和所有创作依据，撰写第{volume}卷第{chapter}章的正文。"

    if instruction:
        user_message += f"\n\n用户特别要求：{instruction}"

    user_message += "\n\n注意：严格遵循本章大纲的结构和事件安排。保持与前文的连贯性。适当处理伏笔。"

    try:
        if stream:
            return await llm.chat_with_context(
                system_prompt=SYSTEM_PROMPT,
                context_docs=context_docs,
                user_message=user_message,
                stream=True,
                max_tokens=16384,
            )
        else:
            result = await llm.chat_with_context(
                system_prompt=SYSTEM_PROMPT,
                context_docs=context_docs,
                user_message=user_message,
                max_tokens=16384,
            )
            return SkillResult(success=True, content=result)
    except Exception as e:
        logger.exception("章节正文生成失败")
        return SkillResult(success=False, error=str(e))
