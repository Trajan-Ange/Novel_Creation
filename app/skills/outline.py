"""Outline generation skill.

Generates hierarchical outlines at three levels:
Book outline -> Volume outline -> Chapter outline.
"""

from app.services.context_builder import get_truncated_settings

SYSTEM_PROMPT_BOOK = """你是一位资深小说架构师，专精于长篇网络小说的结构设计。

你的任务是根据创作依据（世界设定、人物设定等）创建全书大纲。

输出必须包含以下结构：

```markdown
# 《小说名》全书大纲

## 故事主题
[核心主题、核心冲突、主角成长主线]

## 整体结构
### 第一卷：[卷名]
- 核心矛盾：
- 主要事件：
- 出场主要人物：
- 结局走向：
- 本卷字数预估：

### 第二卷：[卷名]
...

## 主线脉络
[从开始到结局的主线发展路线图]

## 核心伏笔规划
| 伏笔 | 埋设位置 | 预期回收 | 涉及人物 | 重要性 |
|------|---------|---------|---------|--------|
| 伏笔A | 第X章 | 第Y章 | 人物 | 高/中/低 |

## 创作建议
[对创作的总体建议和注意事项]
```

规则：
1. 所有内容使用中文
2. 每个卷之间要有清晰的情节推进和升级
3. 伏笔规划合理，不要太密集
4. 卷数建议3-8卷
5. 每卷8-15章"""

SYSTEM_PROMPT_VOLUME = """你是一位小说架构师。根据全书大纲和创作依据，为指定卷创建详细卷大纲。

输出格式：
```markdown
# 第X卷：[卷名] - 卷大纲

## 本卷定位
- 在全书中阶段：
- 核心矛盾：
- 主角阶段目标：

## 章节安排
### 第X章：[章节名]
- 核心事件：
- 出场人物：
- 剧情目的：
- 伏笔操作：（埋设/回收/无）

### 第X+1章：[章节名]
...

## 本卷伏笔
- 需埋设的伏笔：
- 需回收的伏笔：

## 承上启下
- 承接上一卷：
- 导向下一卷：
```"""

SYSTEM_PROMPT_CHAPTER = """你是一位小说章节规划师。根据卷大纲和创作依据，为指定章节创建详细的章节大纲。

输出格式：
```markdown
# 第X卷 第Y章 大纲

## 本章定位
- 在卷中的位置：
- 推进的主线：

## 本章内容
### 场景设定
- 时间：
- 地点：
- 氛围：

### 出场人物
- 主要人物：
- 次要人物：
- 新登场人物：

### 核心事件
1. [事件1]
2. [事件2]
3. [事件3]

### 人物目标
- 角色A：[目标]
- 角色B：[目标]

### 冲突与转折
[本章的主要冲突和转折点]

### 结尾钩子
[引向下一章的悬念或铺垫]

## 注意事项
- [需呼应的前文内容]
- [需埋下的伏笔]
- [风格要求]
```"""


async def run(llm, fm, project: str, params: dict) -> dict:
    """Run outline generation skill.

    params:
        action: "create_book" | "create_volume" | "create_chapter" | "adjust_chapter"
        volume: volume number
        chapter: chapter number
        instruction: user's additional instructions
        existing_chapter_outline: current chapter outline (for adjust)
    """
    action = params.get("action", "create_book")
    instruction = params.get("instruction", "")
    volume = params.get("volume", 1)
    chapter = params.get("chapter", 1)

    context_docs = get_truncated_settings(fm, project)
    user_message = instruction

    if action == "create_book":
        system_prompt = SYSTEM_PROMPT_BOOK
        existing = fm.read_book_outline(project)
        if existing:
            context_docs.insert(0, {"title": "当前全书大纲", "content": existing[:3000]})
        user_message = f"请根据已有设定为《{project}》创建全书大纲。{instruction}".strip()

    elif action == "create_volume":
        system_prompt = SYSTEM_PROMPT_VOLUME
        book_outline = fm.read_book_outline(project)
        if book_outline:
            context_docs.insert(0, {"title": "全书大纲（参考）", "content": book_outline[:3000]})
        # Include previous volume outlines
        for v in fm.list_volume_outlines(project):
            if v < volume:
                v_content = fm.read_volume_outline(project, v)
                if v_content:
                    context_docs.append({"title": f"第{v}卷大纲（已完成）", "content": v_content[:2000]})
        user_message = f"请为《{project}》第{volume}卷创建卷大纲。{instruction}".strip()

    elif action == "create_chapter":
        system_prompt = SYSTEM_PROMPT_CHAPTER
        book_outline = fm.read_book_outline(project)
        if book_outline:
            context_docs.insert(0, {"title": "全书大纲", "content": book_outline[:3000]})
        vol_outline = fm.read_volume_outline(project, volume)
        if vol_outline:
            context_docs.insert(0, {"title": f"第{volume}卷大纲", "content": vol_outline[:2000]})
        # Include recent chapter outlines
        chapters = sorted(fm.list_chapter_outlines(project, volume))
        for ch in chapters[-3:]:
            if ch < chapter:
                ch_content = fm.read_chapter_outline(project, volume, ch)
                if ch_content:
                    context_docs.append({"title": f"第{ch}章大纲（已写）", "content": ch_content[:1500]})
        # Include recent chapter content for continuity
        written_chaps = fm.list_chapters(project, volume)
        for ch in sorted(written_chaps)[-2:]:
            ch_text = fm.read_chapter(project, volume, ch)
            if ch_text:
                context_docs.append({"title": f"第{ch}章正文（已写）", "content": ch_text[:2000]})
        user_message = f"请为《{project}》第{volume}卷第{chapter}章创建章节大纲。{instruction}".strip()

    elif action == "adjust_chapter":
        system_prompt = SYSTEM_PROMPT_CHAPTER
        existing = params.get("existing_chapter_outline") or fm.read_chapter_outline(project, volume, chapter)
        if existing:
            context_docs.insert(0, {"title": "当前章节大纲（需要调整）", "content": existing})
        user_message = f"请根据以下反馈调整第{volume}卷第{chapter}章大纲：{instruction}"

    try:
        stream = params.get("stream", False)
        if stream:
            return await llm.chat_with_context(
                system_prompt=system_prompt,
                context_docs=context_docs,
                user_message=user_message,
                stream=True,
                max_tokens=8192,
            )
        result = await llm.chat_with_context(
            system_prompt=system_prompt,
            context_docs=context_docs,
            user_message=user_message,
            max_tokens=8192,
        )
        return {"success": True, "content": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
