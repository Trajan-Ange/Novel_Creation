# 更新日志 (Changelog)

本文件记录项目的所有重要变更。

本项目遵循[语义化版本控制](https://semver.org/lang/zh-CN/)：`v主版本.次版本.修订号`

---

## v0.1.1 (2026-04-27)

### Bug 修复 — 知识同步引擎无法正常工作

**问题：** 章节生成后知识同步无输出，创作依据不更新，更新摘要为空。

**最终根因（通过调试文件确认）：** LLM 输出被截断。模型在单一调用中需要同时输出详尽文字分析（~3000 tokens）和完整 JSON（16 条人物更新 + 3 个地点 + 9 个事件 + 关系 + 伏笔），远超 `max_tokens=8192`。JSON 块在中途截断 → `_parse_json_response` 只能找到残留的嵌套对象 → 解析结果只有一个 `relationship_changes` 元素 → 全流程无效。

**架构重构：** 从单次 LLM 调用改为 6 阶段流水线：

| 阶段 | 调用 | max_tokens | 输出 |
|------|------|------------|------|
| Phase 1: 文字分析 | 1 次 | 4096 | 纯文字创作要素分析报告 |
| Phase 2a: 人物提取 | 1 次 | 8192 | `{new_characters, character_updates}` |
| Phase 2b: 事件提取 | 1 次 | 4096 | `{new_events}` |
| Phase 2c: 世界提取 | 1 次 | 4096 | `{new_locations, new_world_info}` |
| Phase 2d: 关系提取 | 1 次 | 4096 | `{relationship_changes}` |
| Phase 2e: 伏笔提取 | 1 次 | 4096 | `{new_foreshadowing, recovered}` |

每个分类提取仅接收文字分析作为上下文（非完整章节），配合领域专属的简化 JSON schema，确保单次输出不超 token 限制。

**其他修复：**
- **JSON 解析器四策略回退：** 支持 `---JSON---` 标记 / \`\`\`json 代码块 / 任意 \`\`\` 代码块 / 裸 `{...}` JSON 对象（遍历所有平衡括号对，选键最多者）
- **时间线拆分容错增强：** `app/skills/timeline.py` 增加多种标题变体回退
- **同步失败前端可见：** `app/api/chapters.py` 失败时通过 SSE 推送 error 事件

**调试支持：** 每阶段独立保存调试文件（`同步_01_文字分析_第X章.txt` ~ `同步_07_更新报告_第X章.txt`），可精确定位问题阶段。

**涉及文件：**
- `app/skills/knowledge_sync.py`（重写）
- `app/services/llm.py`
- `app/api/chapters.py`
- `app/skills/timeline.py`

---

## v0.1.2 (2026-04-28)

### Critical Bug Fix — 章节大纲流式生成卡住

**根因：** DeepSeek V4 (deepseek-v4-pro) 模型在生成内容前有一个推理阶段 (reasoning phase)，此阶段的 SSE chunk 中 `delta.content` 为 `None`，推理内容在 `delta.reasoning_content` 字段中。`_chat_stream()` 仅检查 `delta.content`，导致推理阶段无任何数据 yield，前端表现为"卡住无输出"。

**修复：** `app/services/llm.py:_chat_stream()` 改为同时检查 `delta.content or delta.reasoning_content`，推理阶段也能流式输出，用户可实时看到模型思考过程。

### Critical Bug Fix — 知识同步在事件提取阶段卡住

**根因 A — max_tokens 不足：** 事件/世界/关系/伏笔提取使用 `max_tokens=4096`，DeepSeek V4 的推理 tokens 计入输出预算，导致 JSON 输出空间不足、LLM 调用超时或响应截断。

**根因 B — 时间线更新上下文膨胀：** `timeline.run()` 无条件调用 `fm.get_all_settings(project)` 加载所有创作依据（含 21KB 人物关系等），每次 `add_event` 操作都发送 50KB+ 上下文给 LLM，导致响应极慢（测试中 >4 分钟）。

**修复：**
- `knowledge_sync.py`: Phase 2b~2e 的 `max_tokens` 从 4096 提升至 8192
- `timeline.py`: 仅在 `action="create"` 时加载全部设定，`add_event` 仅使用已有时间线
- `llm.py`: `AsyncOpenAI` 客户端增加 `timeout=120s` 防止无限挂起

### 新增功能

- **章节大纲流式生成：** `outline.py` 的 `create_chapter` action 支持 `stream=True` 参数，`chapters.py` 的 `generate_chapter` 端点将大纲逐 chunk 推送至前端
- **知识同步流式进度：** `chapters.py` 的两处 sync 调用改为 `async for` 迭代 `sync_run()` 生成器，将阶段进度消息作为 SSE `status` 事件实时推送
- **章节管理系统：** 新增 `chapter-manager.js` 组件，支持按卷浏览章节列表（含已写作/有大纲/无内容 状态标识）、正文/大纲双标签查看、字数统计、一键跳转章节写作

### Bug 修复

- **双输入框 Bug：** `addChatInput()` 添加顶部去重守卫，移除 `awaiting_confirmation` 事件中重复的 `addChatInput` 调用
- 章节写作页面的卷/章输入框默认值使用 `writeState`，支持从章节管理跳转时自动预填
- **推理内容过滤：** `_chat_stream()` 改为 yield `(type, text)` 元组，所有 7 个流式调用点（`chapters.py` 3 处 + `settings.py` 4 处）过滤 `reasoning` 类型 chunk，仅向用户展示实际内容，思维过程以单次"模型思考中..."状态事件替代
- **正文生成截断修复：** `chapter_write.py` 的 `max_tokens` 从 8192 提升至 16384，`outline.py` 章节大纲从 4096 提升至 8192，知识同步各提取阶段从 4096 提升至 8192，确保 DeepSeek V4 推理 tokens 不挤占输出空间

### 涉及文件

- `app/services/llm.py`（推理内容流式修复 + timeout=120s）
- `app/skills/outline.py`（stream 参数支持 + max_tokens 提升）
- `app/skills/chapter_write.py`（max_tokens 提升至 16384）
- `app/skills/knowledge_sync.py`（各阶段 max_tokens 提升至 8192）
- `app/skills/timeline.py`（仅 create 时加载全部设定）
- `app/api/chapters.py`（大纲流式 + sync 流式进度 + 推理过滤）
- `app/api/settings.py`（4 处流式调用点推理过滤）
- `app/static/js/components/chapter-writer.js`（大纲流式展示 + 双输入框修复）
- `app/static/js/components/chapter-manager.js`（新建，章节管理）
- `app/static/js/state.js`、`app/static/index.html`、`app/static/css/main.css`

---

## v0.1.0 (2026-04-27)

### 安全修复

- **路径遍历漏洞：** `file_manager.py` 的 `delete_project()` 添加 `_validate_name()` 校验；新增 `_validate_path()` 方法使用 `os.path.realpath` + `os.path.commonpath` 防止路径遍历攻击，并通过 `_project_path()` 保护所有路径操作
- **HTTP 状态码规范化：** 6 个 API 文件使用正确的 HTTP 状态码（404/409/422/500）；前端 `api.js` 添加 `res.ok` 检查，向后兼容

### 缺陷修复

- **伏笔 ID 碰撞：** `knowledge_sync.py` 使用 `enumerate(fbs, start=1)` 生成唯一 ID（如 `FB-001-01`），替代之前所有 ID 相同的 Bug
- **LLM 重试机制：** `llm.py` 添加 `_retry_with_backoff()` 方法，指数退避（1s→2s→4s）重试瞬时错误（RateLimit/Timeout/Connection/500），不重试 BadRequest/Authentication
- **SSE 客户端断连检测：** `chapters.py` 和 `settings.py` 的 4 个 `event_stream()` 生成器添加 `request.is_disconnected()` 检查，防止用户离开页面后继续消耗 API Token
- **版本号粒度修复：** `knowledge_sync.py` 用 `changed_modules` 集合追踪实际变更，仅递增变更模块的版本号

### 代码质量

- **死代码删除：** 移除 `app/api/settings_chat.py` (328行)、`app/core/orchestrator.py` (141行)、`outline-tree.js` 的 `generateOutlineLegacy()` 函数
- **重复代码合并：**
  - 新建 `app/api/utils/sse_helpers.py`，提取 `create_sse_sender()` 消除 4 处重复的 SSE send 闭包
  - 新建 `app/static/js/utils/helpers.js`，提取 `escapeHtml()` 消除 2 处重复定义
- **移除未使用依赖：** `requirements.txt` 删除 `aiofiles`

**涉及文件：** 19 个文件变更（2 新建、2 删除、15 修改）/+218 -586 行

---

## v0.0.1 (2026-04-27)

### 首次可用版本

- 基于 FastAPI + vanilla JS 的 AI 辅助小说创作管理系统
- **项目管理：** 创建/删除/列表，支持原创和二创两种类型
- **创作依据管理：** 世界观、人物、时间线、人物关系、风格指南
- **三级大纲生成：** 全书/卷/章节大纲
- **章节写作：** SSE 流式生成 + 交互式反馈
- **知识同步引擎：** 章节后自动提取实体/事件/变更，更新所有设定文件
- **伏笔管理：** 埋设/回收/状态追踪
- **聊天式设定创建：** 多轮交互访谈式生成创作依据
- **二创支持：** 基于 LLM 训练知识的原作世界观提取

**技术栈：** Python/FastAPI + OpenAI SDK + Vanilla JS + 文件系统存储
