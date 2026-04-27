# 版本日志 (CHANGELOG)

本项目遵循语义化版本控制 (SemVer)：`v主版本.次版本.修订号`

---

## v0.1.1 (2026-04-27)

### Bug 修复

**知识同步引擎多项 Bug（测试中发现）**

- **修复缺少 `import json` 导致的崩溃：** `app/skills/knowledge_sync.py` 在模块顶层添加 `import json`，解决 fan-out 阶段 `NameError: name 'json' is not defined` 崩溃问题
- **同步失败前端可见：** `app/api/chapters.py` 两处同步调用添加 else 分支，失败时通过 SSE 推送 error 事件给前端
- **JSON 解析器增强：** `app/services/llm.py` 的 `_parse_json_response()` 重写为三策略回退解析器，支持 `---JSON---` 标记、\`\`\`json 代码块、以及任意 \`\`\` 代码块
- **增大同步 max_tokens：** knowledge_sync 调用从 4096 提升至 8192，避免长章节输出截断
- **SYSTEM_PROMPT 强化：** 明确要求使用 \`\`\`json 代码块格式，而非自定义标记
- **时间线拆分容错增强：** `app/skills/timeline.py` 拆分逻辑增加多种标题变体回退，最终兜底返回全部内容为故事时间线

**涉及文件：**
- `app/skills/knowledge_sync.py`
- `app/services/llm.py`
- `app/api/chapters.py`
- `app/skills/timeline.py`

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
