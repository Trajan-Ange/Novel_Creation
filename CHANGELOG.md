# 更新日志 (Changelog)

本文件记录项目的所有重要变更。

本项目遵循[语义化版本控制](https://semver.org/lang/zh-CN/)：`v主版本.次版本.修订号`

---

---

## v0.2.3 (2026-04-29)

### 安全加固与体验提升

**安全加固：**

- **API Key 环境变量支持**：`load_config()` 检查 `NOVEL_LLM_API_KEY` 环境变量，优先级高于 `config.json` 文件。GET `/api/config` 返回 `api_key_source` 字段标识 Key 来源（`env` / `file` / `none`）
- **项目名校验增强**：`_validate_name()` 增加长度限制（≤50 字符）、纯空白拒绝、前后空格拒绝、Windows 保留名拦截（CON / PRN / AUX / NUL / COM1-9 / LPT1-9）
- **错误信息脱敏**：新增 `sanitize_error()` 函数（移除绝对路径、堆栈跟踪）；`main.py` 新增全局 `@app.exception_handler(Exception)` 统一拦截未处理异常；`chapters.py`、`settings.py`、`projects.py`、`sync.py` 的 `str(e)` 全部替换为 `sanitize_error(e)`
- **CORS 限制为本地地址**：`allow_origins=["*"]` 替换为 `["http://127.0.0.1:8000", "http://localhost:8000", "http://127.0.0.1:3000", "http://localhost:3000"]`，支持 `NOVEL_CORS_ORIGINS` 环境变量扩展

**体验增强：**

- **版本快照**：`file_manager.py` 新增 `save_version_snapshot()` / `list_version_snapshots()` / `restore_version_snapshot()` 方法及异步包装器。知识同步 Phase 3 前自动保存快照。新增 `GET /api/settings/{project}/snapshots` 和 `POST /api/settings/{project}/snapshots/restore` API。前端新增 "版本历史" 按钮，Dialog 展示快照列表并支持恢复
- **冲突检测**：`markdown_utils.py` 新增 `extract_key_terms()` / `find_conflicts()` 函数。知识同步 Phase 2 后自动提取关键术语与已有设定对比，Phase 4 更新报告展示「⚠️ 潜在冲突」小节
- **导航确认**：`state.js` 新增 `hasActiveSSE()` 检查四个 SSE 客户端活跃状态。`navigate()` 中若存在活跃连接则 `Dialog.confirm` 提示用户确认。切换项目时同样检查。`beforeunload` 监听器防止意外关闭页面
- **浏览器历史支持**：`navigate()` / `setProject()` 调用 `history.pushState` 写入 `#/项目名/页面` 格式 hash URL。`popstate` 监听器支持前进/后退。`restoreFromHash()` 在页面初始化时从 URL hash 恢复导航状态。缓存版本 v=8 → v=9

**涉及文件：**

- `app/services/llm.py`（env var 支持）
- `app/storage/file_manager.py`（名称校验增强 + 版本快照方法 + async 包装器）
- `app/api/utils/error_response.py`（`sanitize_error` 新增）
- `main.py`（CORS 限制 + 全局异常处理器）
- `app/api/config.py`（`api_key_source` 字段）
- `app/api/settings.py`（SSE 错误脱敏 + 快照 API + HTTPException import）
- `app/api/chapters.py`（SSE 错误脱敏）
- `app/api/projects.py`（错误脱敏）
- `app/api/sync.py`（错误脱敏）
- `app/skills/knowledge_sync.py`（快照调用 + 冲突检测 + 报告增强）
- `app/services/markdown_utils.py`（`extract_key_terms` + `find_conflicts`）
- `app/static/js/state.js`（导航确认 + pushState + popstate + beforeunload + restoreFromHash）
- `app/static/js/app.js`（init 从 hash 恢复）
- `app/static/js/components/settings-editor.js`（版本历史 Dialog UI）
- `app/static/index.html`（缓存版本 v=8 → v=9）
- `tests/test_file_manager.py`（新增 4 条名称校验测试）
- `README.md`、`启动.bat`、`ROADMAP.md`（版本号同步）

---

## v0.2.2 (2026-04-29)

### 工程质量基础 + UI 功能补全

**UI 功能补全：**

- **角色手动创建按钮**：`settings-editor.js` 新增 "手动创建角色" 按钮（`createCharacterManual()`），含名称验证、路径遍历防护、重复名检测。角色设定现在与世界/时间线/关系/风格保持一致的双按钮模式（AI 对话创建 + 手动创建）
- **大纲管理冗余按钮清理**：`outline-tree.js` header 删除 "生成全书大纲" 和 "生成卷大纲" 两个旧版入口按钮（与树节点详情视图中的 AI/手动按钮功能重复）。同步删除死代码 `generateOutline()` 函数
- **卷大纲创建入口统一**：删除 header 按钮后，创建卷大纲唯一路径为：点击树中卷节点 → AI 对话创建 / 手动编辑，与全书大纲创建模式一致

**工程质量：**

- **A2 — 统一技能返回类型**：新增 `app/services/skill_result.py`，`SkillResult(dict)` 子类提供 `success`/`content`/`data`/`error` 属性访问，同时保持 `isinstance(result, dict)` 和 `result["success"]` 向后兼容。9 个 skill 模块全部迁移
- **A5 — I/O 异步化基础**：`file_manager.py` 新增 28 个 `asyncio.to_thread()` 包装方法（`aread_*` / `awrite_*`），同步调用方不受影响
- **上下文构建逻辑统一**：删除 `settings.py` 中 50 行重复的 `_get_relevant_context()` 函数，两处调用点替换为 `context_builder.build_targeted_context()`。5 个 skill 模块中 `fm.get_all_settings(project)` 全部替换为 `get_truncated_settings(fm, project)`。重写 `build_chapter_context()` 返回 `list[dict]`，整合最近章节、卷大纲、伏笔清单，`chapter_write.py` 已激活使用
- **结构化日志**：所有 9 个 skill 模块（`world_design`/`character_design`/`timeline`/`outline`/`chapter_write`/`writing_assist`/`relationship`/`lore_extract`）及 `chapters.py` API 引入 `logging`，`main.py` 添加 `logging.basicConfig()` 基础配置
- **基础测试覆盖**：新建 `tests/` 目录，39 个测试（25 个 FileManager 单元 + 14 个 API 集成），零 LLM 依赖。`requirements.txt` 新增 `pytest`/`pytest-asyncio`/`httpx`

**涉及文件：**

- `app/services/skill_result.py`（新建）
- `app/services/context_builder.py`（`build_chapter_context` 重写）
- `app/skills/` 下 9 个模块（SkillResult + logging + context_builder）
- `app/storage/file_manager.py`（28 个 async 包装方法 + `import asyncio`）
- `app/api/settings.py`（删除 `_get_relevant_context` + context_builder 调用）
- `app/api/chapters.py`（logging 补充）
- `main.py`（logging 配置）
- `app/static/js/components/settings-editor.js`（手动创建角色按钮）
- `app/static/js/components/outline-tree.js`（冗余按钮 + 死代码清理）
- `app/static/js/components/project-list.js`（SkillResult 兼容：`data`/`result` 双键）
- `tests/` 目录（4 个文件，39 个测试）
- `requirements.txt`（pytest / pytest-asyncio / httpx）
- `index.html`（缓存版本 v=6 → v=7）
- `README.md`、`启动.bat`、`ROADMAP.md`（版本号同步）

### v0.2.2 补丁 (2026-04-29)

**Bug 修复：**

- **角色手动创建不可见**：`editCharacterManual()` 未设置 `char-detail` 的 `display:block`，导致编辑器内容不可见。修复：编辑时显示编辑器区域并隐藏角色列表
- **分卷大纲创建入口缺失**：删除旧版 header 按钮后，大纲树仅展示已有卷，无法创建新卷。修复：大纲树底部新增「＋ 新建卷大纲」入口，通过页面内 Dialog 询问卷号后进入 AI/手动创建

**UX 增强 — 消除浏览器弹窗：**

- 新增 `dialog.js` 页面内 Dialog 系统（`Dialog.alert` / `Dialog.confirm` / `Dialog.prompt`），替代所有 22 处浏览器原生 `prompt()` / `confirm()` / `alert()` 调用
- 涉及 5 个文件：`app.js`、`chapter-writer.js`、`outline-tree.js`、`project-list.js`、`settings-editor.js`
- 添加 Dialog CSS（`.novel-dialog-overlay` / `.novel-dialog` 等），带动画效果
- 缓存版本 v=7 → v=8

---

## v0.2.1 (2026-04-29)

### 上下文优化与健壮性

**上下文膨胀修复：**

- **H5 — 对话生成上下文截断**：`context_builder.py` 从死代码激活为核心服务。新增 `get_truncated_settings()` 和 `build_truncated_context_parts()`，按类型截断（世界 3000 字 / 角色 500 字×8 / 时间线 2000 字 / 关系 2000 字 / 风格 1500 字）。`settings.py` 两处 inline `get_all_settings()` 替换为截断版本，chat-generate 上下文从 150K+ tokens 降至 10-15K tokens
- **H6 — 章节大纲生成上下文精简**：`outline.py` 用 `get_truncated_settings()` 替代全量加载，prepend/append 文档增加截断（全书大纲 3000 / 卷大纲 2000 / 章节大纲 1500 / 正文保持 2000），`create_chapter` 上下文从 ~210K tokens 降至 ~30K tokens
- **重要度筛选**：`knowledge_sync.py` 新增 `_FILTERING_PREAMBLE`，注入 5 个 Phase 2 提取 prompt。忽略功能性路人、过渡性事件、无命名背景景物，减少 Phase 3 无效更新
- **`list_characters()` 过滤备份文件**：`file_manager.py` 过滤 `---.md` 后缀的备份文件，防止出现重复角色名

**健壮性增强：**

- **H7 — 时间线拆分逻辑加固**：`timeline.py` 新增 `split_timeline_content()` 函数，多策略 regex 匹配（H1/H2/bare/中英文变体），三级回退链。替换原有 14 行脆弱的 `str.split()` 逻辑
- **时间线保存 Bug 修复**：`settings.py` 两处 timeline 保存（stream-generate + chat-generate）从"全部写入背景时间线"改为调用 `split_timeline_content()` 拆分后分别写入背景和故事时间线
- **SSE 自动重连**：`sse.js` SSEClient 新增指数退避重连（baseDelay=1s, maxDelay=30s, maxReconnect=5），`_intentionalDisconnect` 标记防止误重连。`project-list.js` wizard SSE client 提升为模块级变量，`state.js` navigate 增加清理

**涉及文件：**

- `app/services/context_builder.py`（新增 `get_truncated_settings` + `build_truncated_context_parts`）
- `app/api/settings.py`（上下文截断 + 阈值统一 + timeline 拆分修复）
- `app/skills/outline.py`（上下文截断 + import 新增）
- `app/skills/timeline.py`（`split_timeline_content` 新增 + 拆分逻辑替换）
- `app/skills/knowledge_sync.py`（`_FILTERING_PREAMBLE` 注入 5 个 prompt）
- `app/storage/file_manager.py`（`list_characters` 过滤备份文件）
- `app/static/js/utils/sse.js`（重连逻辑重写）
- `app/static/js/components/project-list.js`（wizardSSEClient 模块级）
- `app/static/js/state.js`（wizardSSEClient 清理）
- `ROADMAP.md`（v0.2.1 标记完成）

---

## v0.2.0 (2026-04-29)

### 知识同步引擎深度重构 — LLM 调用 12+ → 2~4 次，耗时 60-120s → 15-30s

**核心优化：**

- **Phase 2 五领域并行化**：`_extract_characters` / `_extract_events` / `_extract_world` / `_extract_relationships` / `_extract_foreshadowing` 使用 `asyncio.gather` + `Semaphore(3)` 并发执行，5 次串行调用 → 1 个并发批次
- **Phase 3 角色批量更新**：新增 `_batch_character_update()`，所有角色变更合并为单次 LLM 调用。简单新角色使用 `markdown_utils.build_character_template()` 程序化模板创建，无需 LLM
- **Phase 3 程序化更新**：新增 `app/services/markdown_utils.py`（209 行），提供 `append_table_rows` / `append_section` / `append_list_item` 等程序化 Markdown 操作函数。时间线事件追加、世界设定追加、人物关系追加均优先使用程序化路径，解析失败时自动 fallback 到 LLM
- **上下文缓存**：新增 `_preload_settings()` 在 sync 开始时一次性加载全部设定为 dict，传递给所有 Phase 2/3 函数，消除 Phase 3 多次独立读盘
- **`_process_foreshadowing` 异步化**：`def` → `async def`，文件 I/O 使用 `asyncio.to_thread` 包装
- **调试文件可选**：`run()` 新增 `debug` 参数（默认 `False`）。生产环境不写调试文件
- **旧调试文件自动清理**：`_cleanup_old_debug_files()` 保留最近 `SYNC_DEBUG_RETENTION=5` 次同步的调试文件

**Bug 修复：**

- **严重 — `settings.py` chat_generate 缺少 `await`**：`stream = llm.chat_messages(...)` → `stream = await llm.chat_messages(...)`。v0.1.4 将 `llm._chat_stream()` 替换为 `llm.chat_messages()` 时遗漏两处 `await`，导致所有 AI 交互功能报错 `'async for' requires an object with __aiter__ method, got coroutine`
- **严重 — `_split_characters()` H2 回退错误拆分单角色档案**：角色设定标准格式使用 `## 基本信息` / `## 外貌特征` 等 H2 分区标题，`_split_characters` 的 H2 回退将每个分区当作独立角色保存。修复：新增 `_CHAR_PROFILE_H2` 集合过滤标准分区标题，回退到从 `姓名：XXX` 字段提取角色名

**涉及文件：**

- `app/skills/knowledge_sync.py`（690→980 行，核心重构）
- `app/services/markdown_utils.py`（新建，209 行）
- `app/api/settings.py`（`await` 修复 + `_split_characters` 修复）
- `ROADMAP.md`（v0.2.0 完成 + 0.2.x 规划）

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

## v0.1.3 (2026-04-28)

### 新功能 — 手动创作与用户体验增强

**返回项目列表：** 项目内导航栏新增"← 返回项目列表"入口，点击清除当前项目并回到初始 UI。

**右键快捷菜单：** 侧边栏项目列表支持右键弹出上下文菜单，可快速删除项目（含确认对话框）。

**手动章节创作（含 AI 接管）：**
- 章节写作页面新增"手动创作"按钮，进入两阶段编辑器
- **阶段 1 — 大纲编辑**：Markdown 文本编辑器，支持手动编写或点击"AI 接管大纲"让 AI 流式补全
- **阶段 2 — 正文编辑**：Markdown 文本编辑器，支持手动编写或点击"AI 接管正文"让 AI 从已有内容续写
- 大纲保存后自动切换到正文阶段，正文保存后自动触发知识同步
- 后端新增 `PUT /api/chapters/{project}/volume/{vol}/chapter/{ch}` 端点
- AI 接管通过扩展的 generate 端点实现（`mode: continue_outline` / `continue_text`，`partial_content` 字段）

### 严重缺陷修复（代码审查）

- **C1 — sync.py 独立同步端点不可用**：`await sync_run()` 改为 `async for event in sync_run()` 迭代收集结果
- **C3 — 角色名路径遍历防护**：`file_manager.py` 新增 `_validate_char_name()` 方法，拒绝 `../`、`\\`、`/` 等字符
- **C4 — 原子文件写入**：`_write_file` / `_write_json` 改为先写 `.tmp` 临时文件再 `os.replace` 原子重命名
- **C5 — 章节写入失败不再静默**：`write_chapter_outline` 和 `write_chapter` 包装 try/except，失败时发送 error SSE 事件并 return
- **C6 — 同步失败时不再发送 done 事件**：同步失败时发送 error 后直接 return，跳过项目状态更新

### 中等缺陷修复

- **M1 — 删除项目异常处理**：`shutil.rmtree` 包装 try/except，抛出 `RuntimeError`
- **M3 — 角色拆分支持 H2 标题**：`_split_characters()` 在 h1 匹配为空时回退到 h2 标题
- **M4 — 角色名提取增强**：用正则从指令中提取实际角色名（匹配"创建角色：张三"等模式）
- **M7 — 伏笔 ID 包含卷号**：`FB-{chapter}-{idx}` → `FB-{volume:02d}-{chapter:03d}-{idx:02d}`
- **M8 — 更新报告 f-string 修复**：普通字符串改为 f-string 正确显示章节号
- **M10 — 流式生成角色拆分保存**：`_split_characters()` 拆分后逐个写入独立角色文件

### 前端修复

- **SSE 导航清理**：`navigate()` 开头断开 `chapterSSE` / `outlineStreamingClient` / `settingsChatClient`
- **H2 — LLM 错误日志记录**：`knowledge_sync.py` `_call_llm` 异常时记录 warning 日志
- **H8 — SSE 超时机制**：`SSEClient` 构造函数支持 `timeout` 参数（默认 5 分钟）
- **H9 — SSE JSON 解析错误日志**：catch 块添加 `console.error` 输出

### 涉及文件

- `app/api/sync.py`（C1 修复）
- `app/api/chapters.py`（C5/C6 修复 + PUT 端点 + AI 接管模式）
- `app/api/settings.py`（M3/M4/M10 修复）
- `app/skills/knowledge_sync.py`（H2/M7/M8 修复）
- `app/storage/file_manager.py`（C3/C4/M1 修复）
- `app/static/index.html`（返回按钮 + 右键菜单 DOM）
- `app/static/js/state.js`（SSE 清理 + 返回导航）
- `app/static/js/app.js`（右键菜单事件 + 返回导航事件）
- `app/static/js/components/chapter-writer.js`（手动编辑器 + AI 接管）
- `app/static/js/api.js`（新增 chapters.save API）
- `app/static/js/utils/sse.js`（超时 + 错误日志）
- `app/static/css/main.css`（context-menu / manual-editor / chat 样式）

### v0.1.3 补丁 (2026-04-28)

**v0.1.3 功能可用性修复：**

- **手动创作按钮更易发现**：仪表盘新增"手动创作"快捷操作按钮（`navigateManualWriter`），直接跳转至手动编辑器
- **手动编辑器健壮性增强**：`renderManualWriter` 增加 API 调用失败容错（`.catch` 回退），异常时仍能正常渲染编辑界面；添加即时加载状态避免页面闪烁
- **项目选中高亮**：侧边栏选中项目现在有蓝色高亮标识，`navigate()` 在项目内导航时保持选中态
- **返回项目列表增强**：点击头部"当前项目"标签即可返回项目列表；标签增加悬停样式和 tooltip 提示
- **右键删除覆盖增强**：内容区项目卡片也支持右键菜单快捷删除，与侧边栏行为一致
- **缓存版本号提升**：全部 JS/CSS 引用版本号从 `?v=2` 提升至 `?v=3`，确保浏览器获取最新文件

涉及文件：`app.js`, `state.js`, `chapter-writer.js`, `project-list.js`, `foreshadowing.js`, `main.css`, `index.html`

---

## v0.1.4 (2026-04-28)

### 代码清理 — v0.2.0 知识同步引擎深度重构的前置准备

本次更新不涉及用户可见功能变更，聚焦于消除代码层面的低效冗余和架构债，为 v0.2.0 的重大重构扫清障碍。14/17 项计划任务完成，3 项推迟至 v0.2.0。

### A 组：后端基础设施清理（6/8 完成）

- **A1 — 消除 36 处闭包内 import**：`settings.py`（21处）、`chapters.py`（9处）、`knowledge_sync.py`（5处）、`outline.py`（3处）、`sync.py`（2处）全部提升至模块顶层，经审查无循环依赖风险
- **A3 — 消除私有方法外部调用**：`fm.get_project_abs_path()` 公开方法替代 `fm._project_path()`；`llm.chat_messages()` 公开 API 替代 `llm._chat_stream()`
- **A4 — `get_all_settings()` 上下文缓存**：5 秒 TTL 内存缓存层 + 关键写入路径缓存失效，同一请求周期避免重复读取 5-17 个文件
- **A6 — 上下文构建逻辑统一**：新增 `app/services/context_builder.py`（`build_full_context` / `build_targeted_context` / `build_chapter_context`）
- **A7 — 错误处理基础**：`file_manager.py` 和 `chapters.py` 引入 `logging` 模块；`项目状态.json` JSON 解码失败时通过 `logger.exception()` 告警而非静默返回 `{}`
- **A8 — 硬编码值集中管理**：新增 `app/services/constants.py`

### B 组：前端架构清理（6/6 完成）

- **B1 — SSE 连接工厂**：`sse.js` 新增 `createSSEConnection(url, body, handlers)` 工厂函数
- **B2 — API 错误处理包装**：`api.js` 新增 `safeApiCall(fn, errorMsg, onError)` 包装函数
- **B3 — API 方法去重**：`get()`/`post()`/`put()`/`del()` 通用逻辑提取为 `_request(method, url, body)`
- **B4 — 状态色彩 CSS 化**：新增 `.status-success` / `.status-error` / `.status-warning` / `.status-info` CSS 类
- **B5 — XSS 修复**：project-list.js 项目名 XSS 已在 v0.1.3 修复（data-project + 事件委托）
- **B6 — 全局变量命名空间**：新增 `namespace.js`，`window.NovelApp` 统一入口

### C 组：跨模块一致性（3/3 完成）

- **C1 — FileManager 命名统一**：新增 `read_project_state()` / `write_project_state()` 别名
- **C2 — 错误响应格式统一**：新增 `app/api/utils/error_response.py`
- **C3 — 死代码移除**：移除未使用的 `write_foreshadowing_list()`

### 推迟至 v0.2.0

- **A2**（统一技能返回类型）：需同步修改 9 个技能模块，风险过高
- **A5**（I/O 异步化基础）：需 `aiofiles` 依赖 + 全部调用点适配，与 Phase 2 并行化联动

### 涉及文件

**新建：**
- `app/services/constants.py`（集中常量管理）
- `app/services/context_builder.py`（上下文组装统一）
- `app/api/utils/error_response.py`（错误 DTO 标准化）
- `app/static/js/namespace.js`（前端命名空间）

**修改：**
- `app/api/settings.py`（消除 21 处闭包 import + _chat_stream 迁移）
- `app/api/chapters.py`（消除 9 处闭包 import + logging 引入）
- `app/api/outline.py`（消除 3 处闭包 import）
- `app/api/sync.py`（消除 2 处闭包 import）
- `app/skills/knowledge_sync.py`（消除 5 处闭包 import + _project_path 迁移）
- `app/services/llm.py`（新增 chat_messages 公开 API）
- `app/storage/file_manager.py`（缓存 + logging + 命名别名 + 死代码移除）
- `app/static/js/api.js`（_request 去重 + safeApiCall）
- `app/static/js/utils/sse.js`（createSSEConnection 工厂）
- `app/static/css/main.css`（status-* CSS 类）
- `app/static/index.html`（namespace.js 引用 + 缓存版本 v=4）
- `README.md`、`启动.bat`、`ROADMAP.md`（版本号同步）

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
