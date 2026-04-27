"""Interactive chat-based settings creation with SSE streaming.

Multi-turn conversational flow where the AI interviews the user about a setting,
gradually gathering information before generating the final document.
"""

import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/settings", tags=["settings-chat"])


class ChatGenerateRequest(BaseModel):
    project: str
    setting_type: str  # world, character, timeline, relationship, style
    action: str  # "start", "chat", "generate"
    message: str = ""  # user's latest message (for "chat" and "generate")
    history: list = []  # list of {role, content} dicts


INTERVIEW_BASE = """你是一位专业且友善的小说创作顾问。你的任务是通过多轮对话，逐步了解用户想要创建的设定，最终根据对话内容生成完整的设定文档。

## 对话规则
1. 每次只问一个问题，等待用户回答后再继续。
2. 简要回应用户的回答（1-2句话），表示你理解了，然后提出下一个问题。
3. 问题由浅入深，从概要到细节，逐步覆盖所有重要方面。
4. 保持语气亲切、专业，像一位有经验的编辑在与作者交流。
5. 对话用中文进行。
6. 不要一次性列出所有问题——每次只问一个。

## 重要：何时进入生成阶段
当用户说出"开始生成"、"可以了"、"好了"、"生成吧"等表示就绪的话语，或者你已经问完了下面列出的所有核心问题（至少4-5轮对话后），请在回复末尾加上标记 [READY]。
当用户明确说"开始生成"时，你必须立即在回复末尾加上 [READY]，不要再提问。
"""

# Type-specific interview guides appended to INTERVIEW_BASE
INTERVIEW_GUIDES = {
    "world": """
## 访谈提纲：世界设定

你需要逐步了解以下方面（每次只问一个问题）：
1. 世界的名称和基本类型（修仙、科幻、玄幻、都市、历史等）
2. 世界的地理环境（大陆、海洋、气候、特殊地域等）
3. 世界的势力分布（国家、宗门、组织、种族等）
4. 力量体系或科技水平（修炼体系、魔法系统、科技程度等）
5. 世界的历史背景（重要历史事件、创世传说等）
6. 世界的基本规则和法则（物理规则、社会规则等）
7. 世界上重要的物品或资源
8. 用户是否有其他特别想加入的设定

## 输出格式
生成时请按照以下markdown结构输出：
# 《世界名》世界设定
## 世界背景
## 地理环境
## 势力分布
## 力量体系
## 世界规则
## 重要物品/资源
""",

    "character": """
## 访谈提纲：人物设定

你需要逐步了解以下方面（每次只问一个问题）：
1. 角色的姓名和基本定位（主角/配角/反派）
2. 角色的外貌特征和年龄
3. 角色的性格特点
4. 角色的背景故事和成长经历
5. 角色的目标和动机（想要什么，为什么）
6. 角色的优势和弱点
7. 角色与其他主要人物的关系
8. 角色在故事中的成长弧线

## 输出格式
生成时请按照以下markdown结构输出：
# 角色名 - 人物设定
## 基本信息
## 外貌
## 性格
## 背景故事
## 目标与动机
## 能力与弱点
## 人物关系
## 成长弧线
""",

    "timeline": """
## 访谈提纲：时间线

你需要逐步了解以下方面（每次只问一个问题）：
1. 这个世界是否有历史大事件需要设定？先了解背景时间线的起点
2. 背景时间线中的重要历史节点（按时间顺序）
3. 每个重要历史事件的具体内容
4. 故事时间线的起点（故事从哪个时间点开始）
5. 故事中各卷对应的时间跨度
6. 重要的时间节点和转折点
7. 是否有特殊的时间规则（时间流速不同、时空穿越等）

## 输出格式
生成时请将时间线分为两部分：背景时间线和故事时间线。
""",

    "relationship": """
## 访谈提纲：人物关系

你需要逐步了解以下方面（每次只问一个问题）：
1. 故事中主要有哪些人物需要设定关系？
2. 各人物之间的亲疏远近（亲人、朋友、敌人、师徒等）
3. 关系的动态变化（是否有背叛、和解、发展等）
4. 关系背后的利益纠葛或情感纽带
5. 是否有隐藏的关系（未揭露的血缘、秘密联盟等）
6. 关系对主线剧情的影响

## 输出格式
生成时请以关系图谱的形式输出，包含人物节点和关系连线描述。
""",

    "style": """
## 访谈提纲：风格指南

你需要逐步了解以下方面（每次只问一个问题）：
1. 用户希望的小说整体风格（热血、轻松、沉重、悬疑等）
2. 叙事视角（第一人称/第三人称/多视角切换）
3. 文笔风格偏好（简洁/华丽/口语化/文学性强）
4. 对话与描写的比例偏好
5. 更新频率和每章字数预期
6. 是否有参考的作家或作品风格
7. 是否有特定的用词禁忌或偏好

## 输出格式
生成时请输出结构化的风格指南文档。
""",
}


def build_interview_prompt(setting_type: str) -> str:
    guide = INTERVIEW_GUIDES.get(setting_type, "")
    return INTERVIEW_BASE + guide


def build_generation_prompt(setting_type: str) -> str:
    """Map setting_type to the appropriate skill's system prompt."""
    if setting_type == "world":
        from app.skills.world_design import SYSTEM_PROMPT
    elif setting_type == "character":
        from app.skills.character_design import SYSTEM_PROMPT
    elif setting_type == "timeline":
        from app.skills.timeline import SYSTEM_PROMPT
    elif setting_type == "relationship":
        from app.skills.relationship import SYSTEM_PROMPT
    elif setting_type == "style":
        from app.skills.writing_assist import SYSTEM_PROMPT_STYLE
    else:
        raise ValueError(f"Unknown setting_type: {setting_type}")
    return SYSTEM_PROMPT


SETTING_TYPE_NAMES = {
    "world": "世界设定",
    "character": "人物设定",
    "timeline": "时间线",
    "relationship": "人物关系",
    "style": "风格指南",
}


@router.post("/chat-generate")
async def chat_generate(request: Request, body: ChatGenerateRequest):
    """Interactive chat-based setting creation with SSE streaming.

    Actions:
    - "start": Begin the interview. AI introduces itself and asks the first question.
    - "chat": Process user's answer and respond with the next question.
    - "generate": Generate the final setting document from conversation history.
    """
    llm = request.app.state.llm
    fm = request.app.state.fm

    async def event_stream():
        def send(event_type: str, data: dict = None):
            payload = {"type": event_type}
            if data:
                payload.update(data)
            return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        try:
            project = body.project
            st = body.setting_type
            type_name = SETTING_TYPE_NAMES.get(st, st)

            if body.action == "start":
                # Build messages for the first interaction
                interview_prompt = build_interview_prompt(st)
                messages = [
                    {"role": "system", "content": interview_prompt},
                    {"role": "user", "content": f"用户想要创建{type_name}。请开始访谈，先做自我介绍，然后提出第一个问题。"},
                ]

                yield send("status", {"message": f"AI 正在准备访谈..."})

                full_text = ""
                stream = llm._chat_stream(messages, None, None)
                async for chunk in stream:
                    full_text += chunk
                    yield send("text_chunk", {"text": chunk})

                ready = "[READY]" in full_text
                clean_text = full_text.replace("[READY]", "").strip()
                conv_history = [
                    {"role": "assistant", "content": clean_text},
                ]
                yield send("complete", {
                    "content": clean_text,
                    "ready": ready,
                    "phase": "interview",
                    "history": conv_history,
                })

            elif body.action == "chat":
                interview_prompt = build_interview_prompt(st)

                # Build messages from history + new user message
                messages = [{"role": "system", "content": interview_prompt}]
                for h in (body.history or []):
                    messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
                messages.append({"role": "user", "content": body.message})

                yield send("status", {"message": "AI 正在思考..."})

                full_text = ""
                stream = llm._chat_stream(messages, None, None)
                async for chunk in stream:
                    full_text += chunk
                    yield send("text_chunk", {"text": chunk})

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
                # Build generation context from conversation history
                gen_prompt = build_generation_prompt(st)

                # Convert conversation history to context
                conv_parts = ["以下是用户与AI关于创建" + type_name + "的对话记录，请根据对话中用户表达的需求和想法，生成完整的" + type_name + "：\n"]
                for h in (body.history or []):
                    role_label = "用户" if h.get("role") == "user" else "AI顾问"
                    conv_parts.append(f"【{role_label}】{h.get('content', '')}")
                conv_parts.append("")
                conv_parts.append("---")
                conv_parts.append(f"请根据以上对话内容，生成完整的{type_name}。综合用户的所有需求和想法，输出结构化的markdown文档。")

                user_msg = "\n".join(conv_parts)

                # Also include existing settings as context
                context_docs = fm.get_all_settings(project)
                context_parts = ["参考以下已有资料：\n"]
                for doc in context_docs:
                    context_parts.append(f"【{doc['title']}】")
                    context_parts.append(doc["content"])
                    context_parts.append("")

                # Add existing content for this setting type if updating
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

                full_text = ""
                stream = await llm.chat(gen_prompt, full_user_msg, stream=True)
                async for chunk in stream:
                    full_text += chunk
                    yield send("text_chunk", {"text": chunk})

                # Save to appropriate file
                if st == "world":
                    fm.write_world_setting(project, full_text)
                elif st == "character":
                    fm.write_character(project, "主角与主要配角", full_text)
                elif st == "timeline":
                    fm.write_background_timeline(project, full_text)
                elif st == "relationship":
                    fm.write_relationship(project, full_text)
                elif st == "style":
                    fm.write_style_guide(project, full_text)

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
