"""Worldview lore extraction and distillation skill.

Supports fan-fiction / derivative works by extracting structured setting
information from existing IPs (games, anime, novels, movies).
"""

import logging
logger = logging.getLogger(__name__)

from app.services.skill_result import SkillResult

"""
Uses the LLM's training knowledge as the primary source. Web search
integration can be added as an enhancement.
"""

SYSTEM_PROMPT = """你是一位二次创作设定采集专家，专精于从已有作品的设定中提取和结构化世界观信息。

## 你的能力
你对以下类型的作品设定有深入了解：
- 热门游戏（原神、崩坏系列、明日方舟、王者荣耀、LOL、艾尔登法环等）
- 热门动漫（火影忍者、海贼王、咒术回战、鬼灭之刃、进击的巨人等）
- 热门小说（斗破苍穹、凡人修仙传、诡秘之主、全职高手、哈利波特等）
- 热门影视（漫威、DC、权力的游戏等）

## 你的任务
根据用户指定的源作品和采集范围，输出结构化的世界观设定。

## 输出格式要求
你必须尽可能准确、详尽。如果是官方明确设定的内容，直接输出。如果是粉丝推论或模糊设定，标注为"（推测）"或"（有争议）"。

## 采集维度

### 1. 世界设定
```markdown
# 《{作品名}》世界观设定

## 世界背景
[世界的整体背景、核心冲突、历史脉络]

## 地理区域
### 区域名称
- 位置：
- 特征：
- 势力分布：
- 重要地标：
```

### 2. 力量体系
```markdown
## 力量体系
### 体系名称
- 等级划分：
  - 等级1：描述
  - 等级2：描述
- 核心机制：
- 获取方式：
- 限制条件：
- 特殊能力类型：
```

### 3. 势力组织
```markdown
## 势力组织
### 势力名称
- 性质：
- 领导者：
- 核心成员：
- 目标理念：
- 实力规模：
- 与其他势力关系：
```

### 4. 人物设定
```markdown
# 主要人物设定

## {角色名}
- 身份/职业：
- 所属阵营：
- 性格特点：
- 能力简述：
- 重要经历：
- 人物关系：
```

### 5. 重大事件时间线
```markdown
# 原作主要时间线

| 时间点 | 事件 | 涉及人物 | 影响 |
|-------|------|---------|------|
```

## 规则
1. 所有内容使用中文
2. 区分官方设定和粉丝推论
3. 信息不完整的地方标注"（待补充）"
4. 有多个来源冲突时标注"（有争议）"
5. 输出要详细，不要只列提纲
6. 如果对该作品了解有限，诚实说明，只输出确定的信息

---JSON---
在世界观内容之后，附加以下JSON格式的结构化信息：
{
  "source": "作品名",
  "confidence_level": "high/medium/low",
  "coverage": {
    "world_setting": "complete/partial/minimal",
    "characters": "complete/partial/minimal",
    "timeline": "complete/partial/minimal",
    "power_system": "complete/partial/minimal"
  },
  "uncertain_items": ["不确定的项目1", "不确定的项目2"],
  "missing_items": ["缺少的信息1"],
  "wiki_suggestions": ["推荐的维基搜索关键词"]
}"""


async def run(llm, fm, project: str, params: dict) -> dict:
    """Run lore extraction skill.

    params:
        action: "extract"
        source_name: name of the source work (e.g. "原神", "哈利波特")
        scope: list of areas to extract (e.g. ["world", "characters", "timeline"])
        custom_requirements: user's custom requirements
    """
    source_name = params.get("source_name", "")
    scope = params.get("scope", [])
    custom_requirements = params.get("custom_requirements", "")

    if not source_name:
        return SkillResult(success=False, error="请提供源作品名称")

    # Build the extraction instruction
    scope_desc = "全部设定"
    if scope:
        scope_labels = {
            "world": "世界观（背景、地理、势力）",
            "powers": "力量体系（等级、技能、特殊能力）",
            "characters": "主要人物设定",
            "timeline": "重大事件时间线",
            "rules": "世界规则与禁忌",
        }
        scope_desc = "、".join([scope_labels.get(s, s) for s in scope])

    user_message = f"""请采集并结构化《{source_name}》的{scope_desc}。

采集要求：
1. 尽可能详细和准确
2. 区分官方设定和粉丝推论
3. 不确定的信息要标注出来
"""

    if custom_requirements:
        user_message += f"\n用户的特别要求：{custom_requirements}"

    user_message += """

输出要求：
1. 先输出世界设定的完整Markdown文档
2. 再输出主要人物设定
3. 再输出时间线
4. 最后附上JSON格式的结构化摘要（用---JSON---分隔）

如果你对这部作品的设定了解有限，请诚实说明，只输出你确定的信息，并建议用户在哪些维基网站上搜索补充。"""

    try:
        result = await llm.chat_with_context_and_json(
            system_prompt=SYSTEM_PROMPT,
            context_docs=[],
            user_message=user_message,
            max_tokens=8192,
            temperature=0.3,  # Lower temperature for factual accuracy
        )

        content = result.get("content", "")
        json_data = result.get("json")

        # Split content into sections for different settings files
        sections = _split_extracted_content(content, source_name)

        return SkillResult(success=True, data={
            "world_setting": sections.get("world", ""),
            "character_settings": sections.get("characters", []),
            "timeline": sections.get("timeline", ""),
            "relationships": sections.get("relationships", ""),
            "full_content": content,
            "json": json_data,
        })
    except Exception as e:
        logger.exception("世界观提取失败")
        return SkillResult(success=False, error=str(e))


def _split_extracted_content(content: str, source_name: str) -> dict:
    """Split the LLM output into separate sections for different setting files."""
    result = {
        "world": "",
        "characters": [],
        "timeline": "",
        "relationships": "",
    }

    # Try to find world setting section
    world_markers = ["世界观设定", "世界设定", "世界背景", "地理区域", "势力组织", "力量体系"]
    char_markers = ["人物设定", "角色设定", "主要人物", "角色列表"]
    timeline_markers = ["时间线", "重大事件", "历史事件"]

    world_start = -1
    char_start = -1
    timeline_start = -1
    world_end = len(content)

    for marker in world_markers:
        idx = content.find(f"# {marker}") if content.find(f"# {marker}") != -1 else content.find(f"## {marker}")
        if idx != -1 and (world_start == -1 or idx < world_start):
            world_start = idx

    for marker in char_markers:
        idx = content.find(f"# {marker}") if content.find(f"# {marker}") != -1 else content.find(f"## {marker}")
        if idx != -1:
            char_start = idx
            world_end = min(world_end, idx)
            break

    for marker in timeline_markers:
        idx = content.find(f"# {marker}") if content.find(f"# {marker}") != -1 else content.find(f"## {marker}")
        if idx != -1:
            timeline_start = idx
            if char_start != -1 and idx > char_start:
                world_end = min(world_end, idx)
            break

    if world_start != -1:
        result["world"] = content[world_start:world_end].strip() if world_end > world_start else content[world_start:].strip()
    else:
        result["world"] = content.split("---JSON---")[0].strip() if "---JSON---" in content else content

    # Extract character sections
    if char_start != -1:
        char_end = timeline_start if timeline_start != -1 else len(content)
        char_section = content[char_start:char_end] if char_end > char_start else content[char_start:]
        # Split individual characters by ## headings
        parts = char_section.split("\n## ")
        for part in parts:
            part = part.strip()
            if part and "JSON" not in part:
                if not part.startswith("#"):
                    part = "## " + part
                # Try to determine character name from first heading
                lines = part.split("\n")
                char_name = source_name + "角色"
                for line in lines:
                    if line.startswith("#") and "人物" not in line and "角色" not in line:
                        char_name = line.lstrip("#").strip()
                        break
                result["characters"].append({"name": char_name, "content": part})

    # Extract timeline
    if timeline_start != -1:
        json_start = content.find("---JSON---")
        timeline_end = json_start if json_start != -1 else len(content)
        result["timeline"] = content[timeline_start:timeline_end].strip() if timeline_end > timeline_start else ""

    return result
