"""Writing assistant skill.

Integrates four capabilities:
1. Memory retrieval — search project files for relevant information
2. Style management — collect and detect style consistency
3. Foreshadowing management — track bury/recover lifecycle
4. Pre-write check — generate hints before writing a chapter
"""

import logging
logger = logging.getLogger(__name__)

from app.services.context_builder import get_truncated_settings
from app.services.skill_result import SkillResult

SYSTEM_PROMPT_MEMORY = """你是一位小说创作助手，擅长从创作资料中检索和综合信息。

根据用户的问题和提供的参考资料，给出准确、全面的回答。

要求：
1. 引用具体的来源文件
2. 如果资料中有矛盾，指出矛盾
3. 如果资料不足以回答，诚实说明
4. 用结构化的方式呈现信息"""

SYSTEM_PROMPT_STYLE = """你是一位文学风格分析师。根据已有章节内容，分析作者的写作风格。

输出格式：
```markdown
# 风格指南

## 叙事视角
[第一人称/第三人称限制/第三人称全知]

## 语言风格
- 整体基调：[古风/现代/文艺/口语化]
- 词汇选择：[典雅/通俗/混合]
- 句式特点：[长句为主/短句为主/长短结合]
- 平均段落长度：[短/中/长]

## 对话特色
- 风格：[简洁/絮叨/文雅/粗犷]
- 对话占比：[高/中/低]
- 各角色对话特点：

## 描写偏好
- 侧重：[心理描写/场景描写/动作描写/对话驱动]
- 细节程度：[丰富/适中/简洁]
- 常用修辞：

## 节奏控制
- 整体节奏：[紧凑/舒缓/张弛有度]
- 信息密度：[高/中/低]
- 高潮安排特点：
```"""

SYSTEM_PROMPT_PRE_WRITE = """你是一位小说创作顾问。在作者开始写作前，检视已有资料并提供写作提示。

请检查以下内容并提供建议：
1. 待回收的伏笔 — 是否适合在本章回收？
2. 相关的前文内容 — 是否有需要呼应的情节？
3. 人物状态 — 各人物当前的处境和目标
4. 需要注意的细节 — 容易遗忘的设定

输出简洁的提示列表即可。"""


async def run(llm, fm, project: str, params: dict) -> dict:
    """Run writing assistant skill.

    params:
        action: "memory_search" | "style_collect" | "style_check" | "pre_write_check" | "record_foreshadowing"
        query: search query (for memory_search)
        instruction: user instruction (for style_collect)
        volume: volume number (for pre_write_check)
        chapter: chapter number (for pre_write_check)
    """
    action = params.get("action", "memory_search")

    try:
        if action == "memory_search":
            query = params.get("query", "")
            # Use keyword search to find relevant files
            search_results = fm.search(project, query)
            context_docs = []
            for sr in search_results:
                context_docs.append({
                    "title": sr["file"],
                    "content": sr["snippet"],
                })
            if not context_docs:
                # Fallback to all settings
                context_docs = get_truncated_settings(fm, project)

            result = await llm.chat_with_context(
                system_prompt=SYSTEM_PROMPT_MEMORY,
                context_docs=context_docs,
                user_message=f"请根据提供的资料回答：{query}",
            )
            return SkillResult(success=True, content=result, sources=[r["file"] for r in search_results])

        elif action == "style_collect":
            instruction = params.get("instruction", "")
            # Collect recent chapters to analyze style
            context_docs = []
            all_volumes = fm.list_volume_outlines(project)
            for vol in all_volumes:
                chaps = fm.list_chapters(project, vol)
                for ch in sorted(chaps, reverse=True)[:3]:
                    text = fm.read_chapter(project, vol, ch)
                    if text:
                        context_docs.append({
                            "title": f"第{vol}卷第{ch}章",
                            "content": text[:2000],
                        })
            if not context_docs and instruction:
                context_docs = [{"title": "用户要求", "content": instruction}]

            user_message = "请根据已有章节分析作者的写作风格，生成风格指南。"
            if instruction:
                user_message += f"\n用户偏好：{instruction}"

            result = await llm.chat_with_context(
                system_prompt=SYSTEM_PROMPT_STYLE,
                context_docs=context_docs,
                user_message=user_message,
            )
            return SkillResult(success=True, content=result)

        elif action == "style_check":
            # Compare recent chapter with style guide
            style_guide = fm.read_style_guide(project)
            context_docs = []
            if style_guide:
                context_docs.append({"title": "风格指南", "content": style_guide})
            # Get latest chapter
            all_volumes = fm.list_volume_outlines(project)
            for vol in reversed(all_volumes):
                chaps = fm.list_chapters(project, vol)
                if chaps:
                    latest = max(chaps)
                    text = fm.read_chapter(project, vol, latest)
                    if text:
                        context_docs.append({"title": f"第{vol}卷第{latest}章（待检查）", "content": text[-3000:]})
                    break

            result = await llm.chat_with_context(
                system_prompt="请对比最新章节与风格指南，检测风格是否偏离。给出评分（0-100）和具体偏离点。",
                context_docs=context_docs,
                user_message="请检测最新章节的风格一致性。",
            )
            return SkillResult(success=True, content=result)

        elif action == "pre_write_check":
            volume = params.get("volume", 1)
            chapter = params.get("chapter", 1)

            context_docs = get_truncated_settings(fm, project)
            fb_content = fm.read_foreshadowing_list(project)
            if fb_content:
                context_docs.append({"title": "待回收伏笔", "content": fb_content})

            # Add previous chapter for continuity
            prev_chapter = fm.read_chapter(project, volume, chapter - 1)
            if prev_chapter:
                context_docs.append({
                    "title": f"上一章（第{chapter - 1}章）",
                    "content": prev_chapter[-2000:],
                })

            # Add chapter outline
            outline = fm.read_chapter_outline(project, volume, chapter)
            if outline:
                context_docs.insert(0, {"title": "本章大纲", "content": outline})

            result = await llm.chat_with_context(
                system_prompt=SYSTEM_PROMPT_PRE_WRITE,
                context_docs=context_docs,
                user_message=f"即将写作第{volume}卷第{chapter}章，请给出写作前提示。",
            )
            return SkillResult(success=True, data={"hints": result})

        return {"success": False, "error": f"Unknown action: {action}"}

    except Exception as e:
        logger.exception("写作辅助执行失败")
        return {"success": False, "error": str(e)}
