"""Settings management API endpoints."""

import re

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.utils.sse_helpers import check_disconnected, create_sse_sender
from app.skills.world_design import run as world_skill_run, SYSTEM_PROMPT as WORLD_SYSTEM_PROMPT
from app.skills.character_design import run as character_skill_run, SYSTEM_PROMPT as CHARACTER_SYSTEM_PROMPT
from app.skills.timeline import run as timeline_skill_run, SYSTEM_PROMPT as TIMELINE_SYSTEM_PROMPT
from app.skills.relationship import run as relationship_skill_run, SYSTEM_PROMPT as RELATIONSHIP_SYSTEM_PROMPT
from app.skills.writing_assist import run as writing_assist_run, SYSTEM_PROMPT_STYLE
from app.skills.outline import SYSTEM_PROMPT_BOOK, SYSTEM_PROMPT_VOLUME, SYSTEM_PROMPT_CHAPTER

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingRequest(BaseModel):
    project: str
    instruction: str = ""


class CharacterDeleteRequest(BaseModel):
    project: str
    char_name: str


class SettingSaveRequest(BaseModel):
    project: str
    content: str


class TimelineSaveRequest(BaseModel):
    project: str
    background: str = ""
    story: str = ""


class StreamGenerateRequest(BaseModel):
    project: str
    setting_type: str  # world, character, timeline, relationship, style, book_outline, volume_outline, chapter_outline
    instruction: str = ""
    volume: int = 1
    chapter: int = 1


@router.get("/{project}/all")
async def get_all_settings(request: Request, project: str):
    """Get all settings as context documents."""
    fm = request.app.state.fm
    docs = fm.get_all_settings(project)
    state = fm.get_project_state(project)
    return {"settings": docs, "state": state}


@router.get("/{project}/world")
async def get_world(request: Request, project: str):
    content = request.app.state.fm.read_world_setting(project)
    return {"content": content or ""}


@router.put("/{project}/world")
async def save_world(request: Request, project: str, body: SettingSaveRequest):
    request.app.state.fm.write_world_setting(project, body.content)
    return {"success": True}


@router.post("/{project}/world/generate")
async def generate_world(request: Request, project: str, body: SettingRequest):
    llm = request.app.state.llm
    fm = request.app.state.fm
    result = await world_skill_run(llm, fm, project, {
        "action": "create" if not fm.read_world_setting(project) else "update",
        "instruction": body.instruction,
        "existing_content": fm.read_world_setting(project),
    })
    if result.get("success"):
        fm.write_world_setting(project, result["content"])
    return result


@router.get("/{project}/characters")
async def list_characters(request: Request, project: str):
    fm = request.app.state.fm
    chars = fm.list_characters(project)
    return {"characters": chars}


@router.get("/{project}/characters/{char_name}")
async def get_character(request: Request, project: str, char_name: str):
    content = request.app.state.fm.read_character(project, char_name)
    return {"content": content or "", "name": char_name}


@router.post("/{project}/characters/generate")
async def generate_character(request: Request, project: str, body: SettingRequest):
    llm = request.app.state.llm
    fm = request.app.state.fm
    result = await character_skill_run(llm, fm, project, {
        "action": "create",
        "instruction": body.instruction,
        "char_name": _extract_char_name(body.instruction) if body.instruction else "新角色",
    })
    if result.get("success") and result.get("char_name"):
        fm.write_character(project, result["char_name"], result["content"])
    return result


@router.delete("/{project}/characters/{char_name}")
async def delete_character(request: Request, project: str, char_name: str):
    request.app.state.fm.delete_character(project, char_name)
    return {"success": True}


@router.put("/{project}/characters/{char_name}")
async def save_character(request: Request, project: str, char_name: str, body: SettingSaveRequest):
    request.app.state.fm.write_character(project, char_name, body.content)
    return {"success": True}


@router.get("/{project}/timeline")
async def get_timeline(request: Request, project: str):
    fm = request.app.state.fm
    return {
        "background": fm.read_background_timeline(project) or "",
        "story": fm.read_story_timeline(project) or "",
    }


@router.put("/{project}/timeline")
async def save_timeline(request: Request, project: str, body: TimelineSaveRequest):
    fm = request.app.state.fm
    if body.background:
        fm.write_background_timeline(project, body.background)
    if body.story:
        fm.write_story_timeline(project, body.story)
    return {"success": True}


@router.post("/{project}/timeline/generate")
async def generate_timeline(request: Request, project: str, body: SettingRequest):
    llm = request.app.state.llm
    fm = request.app.state.fm
    result = await timeline_skill_run(llm, fm, project, {
        "action": "create",
        "instruction": body.instruction,
        "existing_bg": fm.read_background_timeline(project),
        "existing_story": fm.read_story_timeline(project),
    })
    if result.get("success"):
        if result.get("background"):
            fm.write_background_timeline(project, result["background"])
        if result.get("story"):
            fm.write_story_timeline(project, result["story"])
    return result


@router.get("/{project}/relationship")
async def get_relationship(request: Request, project: str):
    content = request.app.state.fm.read_relationship(project)
    return {"content": content or ""}


@router.put("/{project}/relationship")
async def save_relationship(request: Request, project: str, body: SettingSaveRequest):
    request.app.state.fm.write_relationship(project, body.content)
    return {"success": True}


@router.post("/{project}/relationship/generate")
async def generate_relationship(request: Request, project: str, body: SettingRequest):
    llm = request.app.state.llm
    fm = request.app.state.fm
    result = await relationship_skill_run(llm, fm, project, {
        "action": "create",
        "instruction": body.instruction,
        "existing_content": fm.read_relationship(project),
    })
    if result.get("success"):
        fm.write_relationship(project, result["content"])
    return result


@router.get("/{project}/style-guide")
async def get_style_guide(request: Request, project: str):
    content = request.app.state.fm.read_style_guide(project)
    return {"content": content or ""}


@router.put("/{project}/style-guide")
async def save_style_guide(request: Request, project: str, body: SettingSaveRequest):
    request.app.state.fm.write_style_guide(project, body.content)
    return {"success": True}


@router.post("/{project}/style-guide/generate")
async def generate_style_guide(request: Request, project: str, body: SettingRequest):
    llm = request.app.state.llm
    fm = request.app.state.fm
    result = await writing_assist_run(llm, fm, project, {
        "action": "style_collect",
        "instruction": body.instruction,
    })
    if result.get("success"):
        fm.write_style_guide(project, result["content"])
    return result


@router.post("/stream-generate")
async def stream_generate_setting(request: Request, body: StreamGenerateRequest):
    """SSE streaming generation for any setting type. Shows real-time AI output."""
    llm = request.app.state.llm
    fm = request.app.state.fm

    async def event_stream():
        send = create_sse_sender()

        try:
            st = body.setting_type
            instruction = body.instruction
            project = body.project

            # Gather all settings as context
            context_docs = fm.get_all_settings(project)
            context_parts = ["参考以下已有资料：\n"]
            for doc in context_docs:
                context_parts.append(f"【{doc['title']}】")
                context_parts.append(doc["content"])
                context_parts.append("")

            if st == "world":
                existing = fm.read_world_setting(project)
                if existing:
                    context_parts.insert(0, f"【当前世界设定】\n{existing}\n")
                context_parts.append(f"---\n用户指令：请{'更新' if existing else '创建'}世界设定。{instruction}")
                full_sys = WORLD_SYSTEM_PROMPT
                user_msg = "\n".join(context_parts)
                yield send("status", {"message": f"正在{'更新' if existing else '生成'}世界设定..."})

            elif st == "character":
                context_parts.append(f"---\n用户指令：创建主角和主要配角。{instruction}")
                full_sys = CHARACTER_SYSTEM_PROMPT
                user_msg = "\n".join(context_parts)
                yield send("status", {"message": "正在生成人物设定..."})

            elif st == "timeline":
                existing_bg = fm.read_background_timeline(project)
                existing_story = fm.read_story_timeline(project)
                if existing_bg:
                    context_parts.insert(0, f"【当前背景时间线】\n{existing_bg}\n")
                if existing_story:
                    context_parts.insert(0, f"【当前故事时间线】\n{existing_story}\n")
                context_parts.append(f"---\n用户指令：创建完整的背景时间线和故事时间线。{instruction}")
                full_sys = TIMELINE_SYSTEM_PROMPT
                user_msg = "\n".join(context_parts)
                yield send("status", {"message": "正在生成时间线..."})

            elif st == "relationship":
                existing = fm.read_relationship(project)
                if existing:
                    context_parts.insert(0, f"【当前人物关系】\n{existing}\n")
                context_parts.append(f"---\n用户指令：创建人物关系图谱。{instruction}")
                full_sys = RELATIONSHIP_SYSTEM_PROMPT
                user_msg = "\n".join(context_parts)
                yield send("status", {"message": "正在生成人物关系..."})

            elif st == "style":
                context_parts.append(f"---\n用户指令：分析并创建风格指南。{instruction}")
                full_sys = SYSTEM_PROMPT_STYLE
                user_msg = "\n".join(context_parts)
                yield send("status", {"message": "正在生成风格指南..."})

            elif st == "book_outline":
                existing = fm.read_book_outline(project)
                if existing:
                    context_parts.insert(0, f"【当前全书大纲】\n{existing}\n")
                context_parts.append(f"---\n用户指令：请根据已有设定为《{project}》创建全书大纲。{instruction}")
                full_sys = SYSTEM_PROMPT_BOOK
                user_msg = "\n".join(context_parts)
                yield send("status", {"message": "正在生成全书大纲..."})

            elif st == "volume_outline":
                book_outline = fm.read_book_outline(project)
                if book_outline:
                    context_parts.insert(0, f"【全书大纲（参考）】\n{book_outline}\n")
                vol = body.volume
                context_parts.append(f"---\n用户指令：请为《{project}》第{vol}卷创建卷大纲。{instruction}")
                full_sys = SYSTEM_PROMPT_VOLUME
                user_msg = "\n".join(context_parts)
                yield send("status", {"message": f"正在生成第{vol}卷大纲..."})

            elif st == "chapter_outline":
                book_outline = fm.read_book_outline(project)
                if book_outline:
                    context_parts.insert(0, f"【全书大纲】\n{book_outline}\n")
                vol = body.volume
                vol_outline = fm.read_volume_outline(project, vol)
                if vol_outline:
                    context_parts.insert(0, f"【第{vol}卷大纲】\n{vol_outline}\n")
                context_parts.append(f"---\n用户指令：请为《{project}》第{vol}卷第{body.instruction or '新'}章创建章节大纲。{instruction}")
                full_sys = SYSTEM_PROMPT_CHAPTER
                user_msg = "\n".join(context_parts)
                yield send("status", {"message": f"正在生成第{vol}卷章节大纲..."})

            else:
                yield send("error", {"message": f"未知的设置类型：{st}"})
                return

            # Stream the generation (filter reasoning, only show content)
            if await check_disconnected(request):
                return
            full_text = ""
            stream = await llm.chat(full_sys, user_msg, stream=True)
            chunk_count = 0
            async for chunk_type, chunk_text in stream:
                if chunk_type == "reasoning":
                    continue
                full_text += chunk_text
                yield send("text_chunk", {"text": chunk_text})
                chunk_count += 1
                if chunk_count % 10 == 0 and await check_disconnected(request):
                    return

            # Save to appropriate file
            if st == "world":
                fm.write_world_setting(project, full_text)
            elif st == "character":
                char_entries = _split_characters(full_text)
                if char_entries:
                    for char_name, char_content in char_entries:
                        if char_name and char_content.strip():
                            fm.write_character(project, char_name, char_content.strip())
                else:
                    fm.write_character(project, "主角与主要配角", full_text)
            elif st == "timeline":
                fm.write_background_timeline(project, full_text)
            elif st == "relationship":
                fm.write_relationship(project, full_text)
            elif st == "style":
                fm.write_style_guide(project, full_text)
            elif st == "book_outline":
                fm.write_book_outline(project, full_text)
            elif st == "volume_outline":
                fm.write_volume_outline(project, body.volume, full_text)
            elif st == "chapter_outline":
                fm.ensure_volume_dir(project, body.volume)
                fm.write_chapter_outline(project, body.volume, body.chapter, full_text)

            yield send("complete", {"content": full_text, "setting_type": st})

        except Exception as e:
            yield send("error", {"message": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── Interview prompts for chat-based settings creation ────────────────

class ChatGenerateRequest(BaseModel):
    project: str
    setting_type: str
    action: str  # "start", "chat", "generate"
    message: str = ""
    history: list = []
    volume: int = 1
    chapter: int = 1


INTERVIEW_BASE = """你是一位专业且友善的小说创作顾问。你的任务是通过多轮对话，逐步了解用户想要创建的设定，最终根据对话内容生成完整的设定文档。

## 对话规则
1. 每次只问一个问题，等待用户回答后再继续。
2. 简要回应用户的回答（1-2句话），表示你理解了，然后提出下一个问题。
3. 问题由浅入深，从概要到细节，逐步覆盖所有重要方面。
4. 保持语气亲切、专业，像一位有经验的编辑在与作者交流。
5. 对话用中文进行。
6. 不要一次性列出所有问题——每次只问一个。
7. 如果已有项目设定（会附在下方），必须在对话中主动引用。例如"根据已有的世界设定「修仙界」，我来帮你设计适合这个世界观的人物..."。提出的问题应与已有设定保持逻辑一致，不要问用户已经回答过的问题。

## 重要：何时进入生成阶段
当用户说出"开始生成"、"可以了"、"好了"、"生成吧"等表示就绪的话语，或者你已经问完了下面列出的所有核心问题（至少4-5轮对话后），请在回复末尾加上标记 [READY]。
当用户明确说"开始生成"时，你必须立即在回复末尾加上 [READY]，不要再提问。
"""

INTERVIEW_GUIDES = {
    "world": """
## 访谈提纲：世界设定

逐步了解以下方面（每次只问一个问题）：
1. 世界的名称和基本类型（修仙、科幻、玄幻、都市、历史等）
2. 世界的地理环境（大陆、海洋、气候、特殊地域等）
3. 世界的势力分布（国家、宗门、组织、种族等）
4. 力量体系或科技水平（修炼体系、魔法系统、科技程度等）
5. 世界的历史背景
6. 世界的基本规则和法则
7. 世界上重要的物品或资源
8. 用户是否有其他特别想加入的设定
""",
    "character": """
## 访谈提纲：人物设定

逐步了解以下方面（每次只问一个问题）：
如果已有世界设定，应根据世界设定来设计适配的角色。如果已有人物，应避免重复创建。
1. 角色的姓名和基本定位（主角/配角/反派）
2. 角色的外貌特征和年龄
3. 角色的性格特点
4. 角色的背景故事和成长经历
5. 角色的目标和动机
6. 角色的优势和弱点
7. 角色与其他主要人物的关系
8. 角色在故事中的成长弧线
""",
    "timeline": """
## 访谈提纲：时间线

逐步了解以下方面（每次只问一个问题）：
如果已有世界设定和人物设定，应根据世界的历史背景和人物经历来构建时间线。提出的问题要与已有设定吻合。
1. 已有世界设定中提到了哪些历史事件？先了解背景时间线的起点
2. 背景时间线中的重要历史节点（按时间顺序）
3. 每个重要历史事件的具体内容
4. 故事时间线的起点
5. 故事中各卷对应的时间跨度
6. 重要的时间节点和转折点
7. 是否有特殊的时间规则
""",
    "relationship": """
## 访谈提纲：人物关系

逐步了解以下方面（每次只问一个问题）：
如果已有世界设定和人物设定，应基于已有的人物列表和世界观来设计关系网络。首先告知用户已有哪些人物。
1. 根据已有的人物列表，确认哪些人物之间需要设定关系
2. 各人物之间的亲疏远近（亲人、朋友、敌人、师徒等）
3. 关系的动态变化（是否有背叛、和解、发展等）
4. 关系背后的利益纠葛或情感纽带
5. 是否有隐藏的关系
6. 关系对主线剧情的影响
""",
    "style": """
## 访谈提纲：风格指南

逐步了解以下方面（每次只问一个问题）：
如果已有世界设定和人物设定，应根据世界观的风格和人物特点来建议写作风格。
1. 用户希望的小说整体风格（热血、轻松、沉重、悬疑等）
2. 叙事视角（第一人称/第三人称/多视角切换）
3. 文笔风格偏好（简洁/华丽/口语化/文学性强）
4. 对话与描写的比例偏好
5. 每章字数预期
6. 是否有参考的作家或作品风格
""",
    "book_outline": """
## 访谈提纲：全书大纲

如果已有世界设定和人物设定，应根据已有设定来规划全书结构。逐步了解以下方面（每次只问一个问题）：
1. 小说的核心主题和想传达的理念
2. 主角的成长主线（起点 → 终点）
3. 全书大概分为几卷（建议3-8卷）
4. 每一卷的核心矛盾和主要事件
5. 重要的伏笔规划
6. 结局的大致走向
7. 是否有特别想写的高潮场景
""",
    "volume_outline": """
## 访谈提纲：卷大纲

如果已有全书大纲，应根据全书大纲中本卷的定位来细化。逐步了解以下方面（每次只问一个问题）：
1. 本卷在全书中承担什么阶段（开端/发展/转折/高潮/收尾）
2. 本卷的核心矛盾是什么
3. 本卷大概多少章（建议8-15章）
4. 每章的核心事件安排
5. 本卷需要埋设或回收哪些伏笔
6. 本卷的主角阶段性目标
7. 与其他卷的衔接关系
""",
    "chapter_outline": """
## 访谈提纲：章节大纲

如果已有卷大纲，应根据卷大纲中本章的定位来细化。逐步了解以下方面（每次只问一个问题）：
1. 本章的核心事件
2. 本章的场景设定（时间、地点、氛围）
3. 本章出场的主要人物和次要人物
4. 本章的人物目标
5. 本章的主要冲突或转折
6. 本章的结尾钩子（如何引向下一章）
7. 本章需要呼应或埋设的伏笔
""",
}

SETTING_TYPE_NAMES = {
    "world": "世界设定", "character": "人物设定",
    "timeline": "时间线", "relationship": "人物关系", "style": "风格指南",
    "book_outline": "全书大纲", "volume_outline": "卷大纲", "chapter_outline": "章节大纲",
}


def _build_interview_prompt(setting_type: str, context_text: str = "") -> str:
    guide = INTERVIEW_GUIDES.get(setting_type, "")
    prompt = INTERVIEW_BASE + guide
    if context_text:
        prompt += f"\n\n## 已有的项目设定（请务必参考）\n以下是你所属项目中已经创建好的其他设定。请在对话中主动引用这些内容，提出的问题应当与已有设定保持一致，避免让用户重复已经提供过的信息。\n\n{context_text}\n"
    return prompt


def _get_relevant_context(fm, project: str, setting_type: str, volume: int = 1) -> str:
    """Build a context string from existing project settings relevant to the given type."""
    parts = []

    if setting_type != "world":
        world = fm.read_world_setting(project)
        if world:
            parts.append(f"【世界设定（已完成）】\n{world}\n")

    if setting_type != "character":
        chars = fm.list_characters(project)
        if chars:
            char_texts = []
            char_limit = 2000 if setting_type == "relationship" else 800
            for c in chars[:8]:  # limit to avoid overflow
                content = fm.read_character(project, c)
                if content:
                    char_texts.append(f"### {c}\n{content[:char_limit]}")
            if char_texts:
                parts.append("【人物设定（已完成）】\n" + "\n\n".join(char_texts) + "\n")

    if setting_type not in ("timeline", "world"):
        bg = fm.read_background_timeline(project)
        if bg:
            parts.append(f"【背景时间线（已完成）】\n{bg[:1500]}\n")
        story = fm.read_story_timeline(project)
        if story:
            parts.append(f"【故事时间线（已完成）】\n{story[:1500]}\n")

    if setting_type != "relationship":
        rel = fm.read_relationship(project)
        if rel:
            parts.append(f"【人物关系（已完成）】\n{rel[:1500]}\n")

    if setting_type != "style":
        style = fm.read_style_guide(project)
        if style:
            parts.append(f"【风格指南（已完成）】\n{style[:1000]}\n")

    # Outline context for volume/chapter outline creation
    if setting_type in ("volume_outline", "chapter_outline"):
        book = fm.read_book_outline(project)
        if book:
            parts.append(f"【全书大纲（已完成）】\n{book[:2000]}\n")
    if setting_type == "chapter_outline":
        vol = fm.read_volume_outline(project, volume)
        if vol:
            parts.append(f"【第{volume}卷大纲（已完成）】\n{vol[:2000]}\n")

    return "\n".join(parts)


def _extract_char_name(instruction: str) -> str:
    """Extract character name from instruction text like '创建角色：张三' or '新增角色 张三'."""
    m = re.search(r'(?:创建|新增|添加|生成)(?:角色[：:]\s*)?(.+?)(?:[，,。]|$)', instruction)
    return m.group(1).strip() if m else "新角色"


def _split_characters(markdown_text: str) -> list:
    """Split a multi-character markdown into individual (name, content) pairs.

    Detects sections by matching h1 headers like:
      # 角色名 - 人物设定
      # 角色名
    Returns a list of (char_name, char_content) tuples.
    """
    # Find all h1 headers first, fall back to h2
    h1_pattern = re.compile(r'^# (.+)$', re.MULTILINE)
    matches = list(h1_pattern.finditer(markdown_text))

    if not matches:
        h2_pattern = re.compile(r'^## (.+)$', re.MULTILINE)
        matches = list(h2_pattern.finditer(markdown_text))

    if not matches:
        return []

    entries = []
    for i, match in enumerate(matches):
        name_raw = match.group(1).strip()
        # Clean up common suffixes
        name = re.sub(r'\s*[-—–]\s*人物设定.*$', '', name_raw).strip()
        if not name:
            name = name_raw

        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown_text)
        content = markdown_text[start:end].strip()

        entries.append((name, content))

    return entries


def _build_generation_prompt(setting_type: str) -> str:
    if setting_type == "world":
        return WORLD_SYSTEM_PROMPT
    elif setting_type == "character":
        return CHARACTER_SYSTEM_PROMPT
    elif setting_type == "timeline":
        return TIMELINE_SYSTEM_PROMPT
    elif setting_type == "relationship":
        return RELATIONSHIP_SYSTEM_PROMPT
    elif setting_type == "style":
        return SYSTEM_PROMPT_STYLE
    elif setting_type == "book_outline":
        return SYSTEM_PROMPT_BOOK
    elif setting_type == "volume_outline":
        return SYSTEM_PROMPT_VOLUME
    elif setting_type == "chapter_outline":
        return SYSTEM_PROMPT_CHAPTER
    else:
        raise ValueError(f"Unknown setting_type: {setting_type}")


@router.post("/chat-generate")
async def chat_generate(request: Request, body: ChatGenerateRequest):
    """Interactive chat-based setting creation with SSE streaming."""
    llm = request.app.state.llm
    fm = request.app.state.fm

    async def event_stream():
        send = create_sse_sender()

        try:
            project = body.project
            st = body.setting_type
            type_name = SETTING_TYPE_NAMES.get(st, st)

            if body.action == "start":
                context_text = _get_relevant_context(fm, project, st, body.volume)
                interview_prompt = _build_interview_prompt(st, context_text)
                messages = [
                    {"role": "system", "content": interview_prompt},
                    {"role": "user", "content": f"用户想要创建{type_name}。请开始访谈，先做自我介绍，然后提出第一个问题。"},
                ]

                yield send("status", {"message": "AI 正在准备访谈..."})

                if await check_disconnected(request):
                    return
                full_text = ""
                stream = llm.chat_messages(messages, stream=True)
                chunk_count = 0
                async for chunk_type, chunk_text in stream:
                    if chunk_type == "reasoning":
                        continue
                    full_text += chunk_text
                    yield send("text_chunk", {"text": chunk_text})
                    chunk_count += 1
                    if chunk_count % 10 == 0 and await check_disconnected(request):
                        return

                ready = "[READY]" in full_text
                clean_text = full_text.replace("[READY]", "").strip()
                yield send("complete", {
                    "content": clean_text,
                    "ready": ready,
                    "phase": "interview",
                    "history": [{"role": "assistant", "content": clean_text}],
                })

            elif body.action == "chat":
                context_text = _get_relevant_context(fm, project, st, body.volume)
                interview_prompt = _build_interview_prompt(st, context_text)
                messages = [{"role": "system", "content": interview_prompt}]
                for h in (body.history or []):
                    messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
                messages.append({"role": "user", "content": body.message})

                yield send("status", {"message": "AI 正在思考..."})

                if await check_disconnected(request):
                    return
                full_text = ""
                stream = llm.chat_messages(messages, stream=True)
                chunk_count = 0
                async for chunk_type, chunk_text in stream:
                    if chunk_type == "reasoning":
                        continue
                    full_text += chunk_text
                    yield send("text_chunk", {"text": chunk_text})
                    chunk_count += 1
                    if chunk_count % 10 == 0 and await check_disconnected(request):
                        return

                ready = "[READY]" in full_text
                clean_text = full_text.replace("[READY]", "").strip()
                new_history = list(body.history or []) + [
                    {"role": "user", "content": body.message},
                    {"role": "assistant", "content": clean_text},
                ]
                yield send("complete", {
                    "content": clean_text,
                    "ready": ready,
                    "phase": "interview",
                    "history": new_history,
                })

            elif body.action == "generate":
                gen_prompt = _build_generation_prompt(st)

                conv_parts = [f"以下是用户与AI关于创建{type_name}的对话记录，请根据对话中用户表达的需求和想法，生成完整的{type_name}：\n"]
                for h in (body.history or []):
                    role_label = "用户" if h.get("role") == "user" else "AI顾问"
                    conv_parts.append(f"【{role_label}】{h.get('content', '')}")
                conv_parts.append("")
                conv_parts.append("---")
                conv_parts.append(f"请根据以上对话内容，生成完整的{type_name}。综合用户的所有需求和想法，输出结构化的markdown文档。")
                user_msg = "\n".join(conv_parts)

                context_docs = fm.get_all_settings(project)
                context_parts = ["参考以下已有资料：\n"]
                for doc in context_docs:
                    context_parts.append(f"【{doc['title']}】")
                    context_parts.append(doc["content"])
                    context_parts.append("")

                if st == "world":
                    existing = fm.read_world_setting(project)
                elif st == "timeline":
                    existing = fm.read_background_timeline(project) or fm.read_story_timeline(project)
                elif st == "relationship":
                    existing = fm.read_relationship(project)
                elif st == "style":
                    existing = fm.read_style_guide(project)
                else:
                    existing = None

                if existing:
                    context_parts.insert(0, f"【当前{type_name}（在此基础上更新）】\n{existing}\n")

                context_parts.append(f"---\n用户指令：{user_msg}")
                full_user_msg = "\n".join(context_parts)

                yield send("status", {"message": f"正在生成{type_name}..."})

                if await check_disconnected(request):
                    return
                full_text = ""
                gen_stream = await llm.chat(gen_prompt, full_user_msg, stream=True)
                chunk_count = 0
                async for chunk_type, chunk_text in gen_stream:
                    if chunk_type == "reasoning":
                        continue
                    full_text += chunk_text
                    yield send("text_chunk", {"text": chunk_text})
                    chunk_count += 1
                    if chunk_count % 10 == 0 and await check_disconnected(request):
                        return

                if st == "world":
                    fm.write_world_setting(project, full_text)
                elif st == "character":
                    # Split multi-character output into individual files
                    char_entries = _split_characters(full_text)
                    for char_name, char_content in char_entries:
                        if char_name and char_content.strip():
                            fm.write_character(project, char_name, char_content.strip())
                elif st == "timeline":
                    fm.write_background_timeline(project, full_text)
                elif st == "relationship":
                    fm.write_relationship(project, full_text)
                elif st == "style":
                    fm.write_style_guide(project, full_text)
                elif st == "book_outline":
                    fm.write_book_outline(project, full_text)
                elif st == "volume_outline":
                    fm.write_volume_outline(project, body.volume, full_text)
                elif st == "chapter_outline":
                    fm.ensure_volume_dir(project, body.volume)
                    fm.write_chapter_outline(project, body.volume, body.chapter, full_text)

                yield send("complete", {
                    "content": full_text,
                    "phase": "generation",
                    "setting_type": st,
                })

            else:
                yield send("error", {"message": f"未知的 action：{body.action}"})

        except Exception as e:
            yield send("error", {"message": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
