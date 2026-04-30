# 版本路线图 (Roadmap)

---

## 已完成

### v0.2.0 — 知识同步引擎深度重构 ⭐（2026-04-29）

核心同步引擎重构：LLM 调用从 12+ 降至 2-4 次，耗时从 60-120s 降至 15-30s。

**核心优化：**
- Phase 2 五领域并行化（`asyncio.gather` + Semaphore=3），5 次串行 → 1 个并发批次
- Phase 3 角色批量更新（`_batch_character_update`），N 次调用 → 1 次
- Phase 3 简单更新程序化：时间线/世界/关系优先使用 `markdown_utils.py` 直接操作 Markdown，LLM fallback
- 上下文缓存：`_preload_settings()` 一次加载，全局复用
- `_process_foreshadowing` 异步化（`async def` + `asyncio.to_thread`）
- 调试文件可选（`debug` 参数默认 `False`）+ 自动清理（保留最近 5 次）

**Bug 修复：**
- **严重**：`settings.py` chat_generate 缺少 `await` — `stream = await llm.chat_messages(...)`（v0.1.4 引入）
- **严重**：`_split_characters()` H2 回退错误拆分单角色档案 — 新增 `_CHAR_PROFILE_H2` 过滤标准分区标题，回退到 `姓名：XXX` 提取

**架构改进：**
- H1: Phase 3 角色逐条 LLM → 批量（`_batch_character_update`）
- H3: `_process_foreshadowing` 同步 → 异步

**变更统计：** `knowledge_sync.py`（690→980 行）、新增 `markdown_utils.py`（209 行）

### v0.1.4 — 代码清理与 v0.2.0 基础设施准备（2026-04-28）

- A1: 消除 36 处闭包内 import
- A3: 消除 `_project_path()` 和 `_chat_stream()` 外部调用
- A4: `get_all_settings()` 上下文缓存（5s TTL）
- A6: 上下文构建逻辑统一（`context_builder.py`）
- A7: 错误处理基础（logging 模块）
- A8: 硬编码值集中管理（`constants.py`）
- B1-B6: 前端架构清理（SSE 工厂、API 包装、CSS 化、命名空间）
- C1-C3: 跨模块一致性（FileManager 命名规范化、错误响应格式统一、死代码移除）

### v0.1.3 — 手动创作支持与用户体验修复（2026-04-28）

- 手动创建章节流程、Markdown 编辑器、AI 接管按钮
- 返回项目列表按钮、侧边栏右键菜单
- 6 CRITICAL / 5 MEDIUM 代码审查缺陷修复
- 前端 SSE 连接清理、超时机制、错误输出

### v0.1.2 — 流式生成修复与章节管理（2026-04-28）

- DeepSeek V4 推理阶段阻塞流式输出修复
- 知识同步 token 限制修复（8192）、120s 超时
- 章节管理系统、推理内容过滤

### v0.1.1 — 知识同步引擎修复（2026-04-27）

- 架构重构：单一 LLM 调用 → 6 阶段流水线
- JSON 解析器四策略回退、时间线拆分容错

### v0.1.0 — 安全与稳定性（2026-04-27）

- 路径遍历漏洞修复、HTTP 状态码规范化
- LLM 指数退避重试、SSE 客户端断连检测

### v0.0.1 — 首次发布（2026-04-27）

- 项目管理、创作依据管理、三级大纲生成、SSE 流式章节撰写

---

## v0.2.1 — 上下文优化与健壮性

### 目标

解决 LLM 上下文膨胀问题，提升生成质量和同步准确度。

### 上下文优化

- [x] **重要度筛选**：Phase 2 提取时仅关注实质性新增/变化，忽略已有信息的重复描述，减少 Phase 3 无效更新
- [x] **H5 — 对话生成上下文膨胀**：`settings.py` chat_generate 的 `get_all_settings` 对 10+ 角色项目可能超 30K tokens。按相关性筛选而非全量注入
- [x] **H6 — 章节大纲生成上下文精简**：`outline.py` create_chapter 包含 3 个大纲 + 2 个章节全文 + 全部设定，可超 40K tokens。按相关性裁剪

### 健壮性

- [x] **H7 — 时间线拆分逻辑加固**：支持 `##` 标题、无标题等更多 LLM 输出格式变体
- [x] **SSE 自动重连**：客户端断连后指数退避重连

---

## v0.2.2 — 工程质量基础 + UI 功能补全

### 目标

建立测试、日志、类型系统基础，消除架构债；补全 UI 功能缺口。

### UI 功能补全
- [x] **角色手动创建按钮**：`settings-editor.js` 新增 "手动创建角色" 按钮，与世界观/时间线/关系/风格保持一致的双按钮模式
- [x] **大纲管理冗余按钮清理**：删除 header 中的 "生成全书大纲" 和 "生成卷大纲" 旧版入口，统一到树节点详情视图
- [x] **卷大纲创建入口统一**：点击树中卷节点 → AI/手动创建，与全书大纲模式一致

### 核心工程
- [x] **A2 — 统一技能返回类型**：新增 `SkillResult(dict)` 子类，9 个 skill 模块全部迁移，保持 dict 向后兼容 + 属性访问
- [x] **A5 — I/O 异步化基础**：`file_manager.py` 新增 28 个 `asyncio.to_thread()` 包装方法
- [x] **结构化日志**：所有 9 个 skill 模块 + chapters API 引入 `logging`
- [x] **基础测试覆盖**：39 个测试（25 个 FileManager 单元 + 14 个 API 集成），零 LLM 依赖
- [x] **上下文构建逻辑统一**：删除 `settings.py` 50 行重复 `_get_relevant_context()`，6 处替换为 `context_builder`；激活未使用的 `build_chapter_context()`

**涉及文件：**
- `app/services/skill_result.py`（新建）
- `app/services/context_builder.py`（`build_chapter_context` 重写 + 截断逻辑）
- `app/skills/` 下 9 个模块（SkillResult + logging + context_builder）
- `app/storage/file_manager.py`（28 个 async 包装方法）
- `app/api/settings.py`（删除 `_get_relevant_context`）
- `app/api/chapters.py`（logging 补充）
- `app/static/js/components/settings-editor.js`（手动创建角色）
- `app/static/js/components/outline-tree.js`（冗余按钮 + 死代码清理）
- `app/static/js/components/project-list.js`（SkillResult 兼容）
- `tests/` 目录（4 个文件，39 个测试）
- `requirements.txt`（pytest / pytest-asyncio / httpx）
- `main.py`（logging 配置）

---

## v0.2.3 — 安全加固与体验提升 ⭐（2026-04-29）

### 安全加固

- [x] **API Key 环境变量支持**：`NOVEL_LLM_API_KEY` 优先级高于 `config.json`
- [x] **项目名校验增强**：长度限制（50字符）、空格名拒绝、Windows 保留名拦截（CON/PRN/AUX/NUL/COM1-9/LPT1-9）
- [x] **错误信息脱敏**：全局异常处理器 + `sanitize_error()` 路径/堆栈过滤，SSE/HTTP 全覆盖
- [x] **CORS 限制为本地地址**：替换 `allow_origins=["*"]` 为 localhost 列表，支持 `NOVEL_CORS_ORIGINS` 环境变量扩展

### 体验增强

- [x] **导航确认**：有活跃 SSE 连接时 `Dialog.confirm` 提示，`beforeunload` 浏览器确认
- [x] **浏览器历史支持**：`history.pushState` / `popstate` / hash 路由（`#/项目名/页面`），支持前进/后退/深链
- [x] **版本快照**：知识同步前自动保存当前设定到 `版本历史/`，API 支持列表/恢复，前端 "版本历史" 按钮
- [x] **冲突检测**：Phase 2 后提取关键术语与已有设定对比，Phase 4 更新报告展示冲突

---

## v0.2.4 — 代码审查、清理与 v0.3.0 预备（2026-04-29）

### 目标

按版本策略（vX.Y.4 = 清理/预备），修复缺陷、删除死代码、简化架构、为 v0.3.0 铺路。

### 缺陷修复

- [x] **`write_project_state()` 双重写入**：委托链中 `write_project_state` → `save_project_state` 已写入磁盘，自身又重复写入。修复：仅委托不二次写入
- [x] **4 处前端 XSS 高危点**：`project-list.js` 3 处 + `settings-editor.js` 1 处 innerHTML 未转义，使用 `escapeHtml()` 修复
- [x] **`load_config` 编辑匹配错误**：修复日志

### 死代码删除（5 项）

- [x] **`context_builder.py`** — 删除未使用的 `build_full_context()`（零调用者）
- [x] **`constants.py`** — 删除整个文件（11/12 常量未使用），`SYNC_DEBUG_RETENTION` 移至 `knowledge_sync.py`
- [x] **`error_response.py`** — 删除 3 个未用函数（`error_response` / `http_error_detail` / `sse_error`），仅保留 `sanitize_error()`
- [x] **`namespace.js`** — 删除（`window.NovelApp` 零引用），移除 `index.html` 引用
- [x] **`core/` 目录** — 删除（仅含 pycache 残留）

### 代码简化与去重

- [x] **import 上移**：`sync.py`、`markdown_utils.py` 等文件消除内联 import
- [x] **`file_manager.py` 异步包装器精简**：`__getattr__` 动态拦截 `a*` 前缀方法（21 个方法 / 85 行 → 12 行），向后兼容
- [x] **`outline.py` 冗余 import 删除**
- [x] **`settings.py` 保存分支合并**：提取 `_save_setting_by_type()` 消除 2 处 28 行重复 if-elif 链

### v0.3.0 预备

- [x] **CSS 自定义属性体系**：`main.css` `:root` 定义 57 个变量（`--color-bg` / `--color-text` / `--color-primary` / `--shadow-sm` 等），`editor.css` / `chat.css` 全部引用。零视觉变化。`.theme-dark` 占位选择器
- [x] **技能测试骨架**：`conftest.py` 新增 `MockLLMService`（内存模拟，零网络依赖）。新建 `test_skill_result.py`（6 测试）+ `test_world_design.py`（5 测试），总测试 39 → 50
- [x] **v0.3.0 接口桩**：`file_manager.py` 新增 `export_project_archive()` / `import_project_archive()`，`raise NotImplementedError`

### 涉及文件

- `app/storage/file_manager.py`（修复双重写入 + `__getattr__` 异步委托 + v0.3.0 桩）
- `app/services/context_builder.py`（删除 `build_full_context`）
- `app/services/constants.py`（**删除**）
- `app/api/utils/error_response.py`（删除 3 未用函数）
- `app/api/settings.py`（`_save_setting_by_type` 提取 + sanitize_error import）
- `app/api/sync.py`（import 上移）
- `app/api/outline.py`（冗余 import 删除）
- `app/api/chapters.py`（sanitize_error 替换 str(e)）
- `app/api/projects.py`（sanitize_error 替换 str(e)）
- `app/services/markdown_utils.py`（import 上移）
- `app/skills/knowledge_sync.py`（`SYNC_DEBUG_RETENTION` 内联）
- `app/services/llm.py`（`NOVEL_LLM_API_KEY` env var）
- `main.py`（CORS + 全局异常处理器）
- `app/core/`（**删除**）
- `app/static/js/namespace.js`（**删除**）
- `app/static/js/components/project-list.js`（XSS 修复）
- `app/static/js/components/settings-editor.js`（XSS 修复 + 版本历史）
- `app/static/js/state.js`（导航确认 + pushState + popstate）
- `app/static/css/main.css`（CSS 变量体系 + `.theme-dark` 占位）
- `app/static/css/editor.css`（颜色 → CSS 变量）
- `app/static/css/chat.css`（颜色 → CSS 变量）
- `app/static/index.html`（移除 namespace.js 引用 + 缓存 v=10）
- `tests/conftest.py`（MockLLMService fixture）
- `tests/test_skill_result.py`（**新建**，6 测试）
- `tests/test_world_design.py`（**新建**，5 测试）
- `tests/test_file_manager.py`（4 新增名称校验测试已在本周期完成）
- `ROADMAP.md`、`CHANGELOG.md`、`README.md`、`启动.bat`（版本同步）

---

## v0.3.0 — 桌面应用化与主题系统 ⭐

### 目标

将项目从浏览器网页模式升级为本地桌面应用，同时建立完善的 UI 主题定制系统。用户可通过双击 exe 启动，并通过配置选项自定义界面外观。

### 桌面应用化

- [x] **PyInstaller 打包**：将 Python + FastAPI + 静态资源打包为单个 `.exe` 启动文件。`main.py` 入口，`--add-data` 包含 `app/static/`。`--windowed` 模式下自动打开浏览器或内嵌 WebView
- [x] **配置路径分离**：`config.json`（API Key 等敏感配置）从应用目录移至用户数据目录（`%APPDATA%/NovelCreation/` 或 `~/.novel/`），避免升级时覆盖。通过 `sys._MEIPASS` 检测运行模式
- [x] **marked.js 本地化**：从 CDN 依赖改为本地打包（`app/static/vendor/marked.min.js`），实现完全离线可用
- [x] **生产/开发模式切换**：环境变量 `NOVEL_ENV=production` 关闭 `reload=True`、关闭调试日志、使用更保守的 uvicorn 配置
- [x] **桌面启动器替代 启动.bat**：PyInstaller 打包后 `启动.bat` 不再需要。新增 `build.bat` 构建脚本用于打包
- [x] **单实例锁**：检测已有进程占用 8000 端口，防止重复启动

### UI 主题系统

- [x] **CSS 自定义属性体系（重新实现）**：在 `main.css` `:root` 定义约 30 个设计令牌变量（`--color-bg`、`--color-surface`、`--color-primary`、`--color-text`、`--radius-md`、`--shadow-sm` 等），覆盖背景、文字、边框、阴影、圆角。本次吸取 v0.2.4 教训：逐文件渐进迁移，每步验证
- [x] **亮色/暗色/暖色/森林 四套预设主题**：通过 `[data-theme="dark"]` 等选择器覆盖变量值。主题切换器放在 header 右侧。用户选择持久化到 `localStorage`
- [x] **用户自定义配色参数**：`config.json` 新增 `theme` 段，允许用户覆盖任意设计令牌值。例如：`{ "theme": { "--color-primary": "#ff6b35" } }`。启动时加载并注入 `:root`
- [x] **布局密度选项**："紧凑 / 默认 / 舒适" 三档，通过 `--density` 变量控制 padding/gap 缩放。header/sidebar/card 间距统一响应
- [x] **字体大小调节**：`--font-scale` 变量（0.85 / 1.0 / 1.15），正文和 UI 文字统一缩放。在设置面板提供滑块
- [x] **消除 JS 内联颜色**：将 `settings-editor.js`、`chapter-writer.js` 等文件中 50+ 处 `style="color:#XXXXXX"` 替换为 CSS 类引用（`.status-success` 等已有类），为颜色变量化扫清障碍

### v0.3.0 技术风险与注意事项

- **PyInstaller 兼容性**：`asyncio` + `uvicorn` + `openai` 的组合在 PyInstaller 下需验证。`openai` SDK 依赖 `httpx`，可能需要 `--hidden-import` 补充
- **静态文件路径**：PyInstaller 打包后 `StaticFiles(directory="app/static")` 需改为 `sys._MEIPASS` 相对路径
- **CSS 变量迁移策略**：按模块分 5 个子任务（布局 → 按钮/表单 → 模态框 → 章节管理器 → 编辑器/Chat），每步手动验证后再继续。避免 v0.2.4 一次性替换导致的全局崩坏

### 涉及文件

- `main.py`（生产模式 / `--windowed` 适配）
- `app/storage/file_manager.py`（配置路径分离）
- `app/services/llm.py`（配置路径分离）
- `app/static/css/main.css`（CSS 变量定义 + 主题选择器）
- `app/static/css/editor.css`（颜色 → 变量引用）
- `app/static/css/chat.css`（颜色 → 变量引用）
- `app/static/js/components/*.js`（内联颜色 → CSS 类）
- `app/static/js/state.js`（主题切换逻辑 + localStorage 持久化）
- `app/static/js/components/config-panel.js`（主题配置 UI）
- `app/static/vendor/marked.min.js`（新增，CDN 替代）
- `app/static/index.html`（移除 CDN 引用 + 主题初始化脚本）
- `build.bat`（新增，PyInstaller 构建脚本）
- `启动.bat`（适配或废弃）

---

## v0.3.1 — Prompt 工程体系化与 AI 可观测性

### 目标

将分散在 9 个 skill 模块中的内联 prompt 提取为统一管理的 prompt 注册表，建立 LLM 调用的可观测性基础（token 用量、成本、延迟），为用户提供 AI 行为的可调参数。

### Prompt 注册表

- [ ] **Prompt 外部化**：9 个 skill 模块 + `knowledge_sync.py`（6 个 prompt）总计约 15 个 `SYSTEM_PROMPT` 常量提取到 `app/prompts/` 目录下的独立文件（每个 prompt 一个 `.md` 或 `.yaml`）。支持 `{variable}` 占位符替换
- [ ] **Prompt 版本管理**：每个 prompt 文件头部标注版本号和修改日期。`SkillResult` 返回时附带 `prompt_version` 字段，便于回溯生成质量
- [ ] **Prompt 热加载**：`--reload` 模式下监听 `app/prompts/` 目录变化，无需重启即可测试 prompt 调整
- [ ] **角色/风格 prompt 模板**：提供 3-5 套预设创作风格模板（"网文风"、"传统文学"、"轻小说"、"史诗奇幻"、"悬疑推理"），切换模板即替换所有 skill 的基础 prompt 倾向

### AI 可观测性

- [ ] **Token 用量追踪**：`LLMService` 每次调用记录 `prompt_tokens`、`completion_tokens`、`total_tokens`（OpenAI SDK 响应中 `usage` 字段）。按 skill 聚合统计
- [ ] **成本估算**：基于模型定价（DeepSeek: ¥1/M tokens, GPT-4o: $2.50/M tokens 等），实时估算每次调用成本。在 `config.json` 中配置模型单价
- [ ] **延迟监控**：记录每次 LLM 调用的首 token 延迟（TTFT）和总耗时。`/api/sync` 返回时携带 Phase 1/2/3/4 各阶段耗时分解
- [ ] **用量仪表盘**：项目概览页面新增 "AI 用量" 卡片——本次会话/累计 token 消耗、预估费用、各 skill 调用次数分布

### 用户可调 AI 参数

- [ ] **Per-skill 温度配置**：当前每个 skill 硬编码 temperature（如 `knowledge_sync`=0.3, `chapter_write`=0.8）。`config.json` 新增 `skill_temperatures` 段，允许用户按 skill 覆盖
- [ ] **全局创意度档位**：提供"严谨 / 平衡 / 创意" 三档快捷设置，一键调整所有 skill 的 temperature + top_p
- [ ] **最大 Token 数按场景配置**：大纲/正文/同步分别设置 max_tokens（大纲 4096、正文 16384、同步 8192），避免浪费

### 涉及文件

- `app/prompts/`（新增目录，15+ prompt 文件）
- `app/services/llm.py`（token 追踪 + 成本估算 + 延迟记录）
- `app/skills/*.py`（9 个 skill 迁移到 prompt 注册表）
- `app/skills/knowledge_sync.py`（6 个 prompt 迁移）
- `app/api/sync.py`（返回各阶段耗时）
- `config.json`（新增 skill_temperatures / model_pricing / creativity_presets）
- `app/static/js/components/config-panel.js`（AI 参数配置 UI）
- `app/static/js/components/project-list.js`（用量仪表盘）

---

## v0.3.2 — AI 管线深度优化

### 目标

深入优化知识同步引擎和章节生成管线的 LLM 调用效率，提升生成质量与一致性。建立 provider 抽象以支持多模型切换。

### 知识同步引擎优化

- [ ] **Phase 2 并行度可配置**：`_MAX_CONCURRENT_EXTRACTORS = 3` 改为 `config.json` 可配（默认 3，DeepSeek 付费用户可调至 5）。按 provider 的 rate limit 自动建议最优值
- [ ] **同步流式化（SSE）**：`/api/sync` 从 POST 阻塞改为 SSE 流式，实时推送 Phase 1/2/3/4 进度（类似章节生成的 `status` 事件）。UX 改进：用户可见同步进度而非等待 15-30s 无反馈
- [ ] **部分成功容错**：Phase 2 并行提取中单个类别失败不影响其余类别。Phase 3 文件更新失败时标记为"待处理"而非整体回滚。前端展示部分成功结果
- [ ] **增量同步优化**：仅同步自上次同步以来新增/修改的章节。`项目状态.json` 记录 `last_sync_chapter` 和 `last_sync_hash`，跳过未变化内容
- [ ] **冲突解决 UI**：Phase 4 检测到的冲突在前端以交互式 UI 展示（"已有设定：X；新提取：Y → [保留已有] [替换为新] [合并]"），替代当前仅文本报告

### Provider 抽象层

- [ ] **LLM Provider 接口**：定义 `BaseLLMProvider` 抽象类（`chat()` / `chat_stream()` / `chat_with_json()` 三个方法）。当前 `LLMService` 重构为实现该接口的 `OpenAICompatibleProvider`
- [ ] **多 Provider 支持**：新增 `AnthropicProvider`（Claude API 原生支持）、`OllamaProvider`（本地模型）。`config.json` 的 `provider` 字段切换
- [ ] **Provider 自检**：`/api/config/test` 增强——自动检测 endpoint 类型（OpenAI / Anthropic / Ollama），验证兼容性
- [ ] **Fallback 链**：配置主/备两个 provider，主 provider 超时或限流时自动切换到备用

### 章节生成质量优化

- [ ] **大纲→正文一致性校验**：章节生成后自动检查正文是否覆盖了大纲中所有要点。缺失项以 `status-warning` 提示用户
- [ ] **上文感知增强**：`build_chapter_context()` 引入前 N 章摘要而非全文（当前注入全文可能超 40K tokens），节省上下文窗口用于更相关的设定
- [ ] **写作风格一致性**：提取已写章节的文体特征（句式长度分布、对话比例、描写密度），`chapter_write` 生成时注入风格约束

### 涉及文件

- `app/services/llm.py`（Provider 抽象 + 多 provider 实现）
- `app/skills/knowledge_sync.py`（并行度可配 + 增量同步 + 部分成功）
- `app/api/sync.py`（SSE 流式化）
- `app/api/chapters.py`（一致性校验 + 上文感知）
- `app/services/context_builder.py`（上文摘要注入）
- `app/services/skill_result.py`（部分成功状态字段）
- `app/static/js/components/chapter-writer.js`（冲突交互 UI）
- `config.json`（provider / fallback / max_concurrent 配置）

---

## v0.3.3 — 创作内容质量闭环

### 目标

建立跨章节的创作内容一致性保障体系，引入修订模式，实现"写后即检、检后即修"的创作质量闭环。

### 内容一致性引擎

- [ ] **角色行为一致性检查**：对比角色设定中的性格/动机与正文中的实际行为。例如：设定"冷静理性"的角色在正文中频繁情绪爆发 → 标记为不一致
- [ ] **情节逻辑校验**：检测时间线矛盾（第 3 章提到"三天后"但第 4 章开头是"第二天"）、人物位置矛盾（角色同时出现在两地）
- [ ] **伏笔追踪自动化**：`knowledge_sync` Phase 2 中伏笔提取增强——自动识别正文中的伏笔线索，与"伏笔清单"对比，标记已回收/待回收/过期状态
- [ ] **设定漂移检测**：对比同一设定项在不同章节中的描述变化。例如：第 1 章"青云宗有 3000 弟子"，第 10 章变成"5000 弟子" → 标记为潜在漂移

### 修订模式

- [ ] **局部重写**：选中章节中任意段落，发送修改指令（"这段对话更紧张一些"），AI 仅重写该段落并保持上下文连贯
- [ ] **修订对比视图**：Markdown diff 显示修改前后差异。类似 GitHub diff，绿色=新增，红色=删除。用户可逐条接受/拒绝
- [ ] **批量修订**：对全文章节的特定问题进行全局修正（"把所有'说道'改成更丰富的表达"、"统一所有角色的称谓"）
- [ ] **修订历史**：每次修订保存到 `修订历史/` 目录，可回退到任意修订点

### AI 创作规范文档化

- [ ] **创作规范生成器**：基于现有设定（世界观 + 人物 + 风格指南），AI 自动生成一份《创作规范手册》，包含：命名约定、对话风格、场景转换规则、禁忌事项
- [ ] **规范检查器**：新写章节自动对照《创作规范手册》逐项评分。例如：规范要求"每章至少 2000 字"、"禁止连续 3 段以上纯对话" → 不达标项红色标注
- [ ] **规范自定义**：用户可编辑规范手册（Markdown），添加/修改/删除检查项。规范文件保存在 `创作依据/创作规范.md`

### 涉及文件

- `app/skills/consistency_check.py`（新增，一致性检查 skill）
- `app/skills/revision.py`（新增，修订模式 skill）
- `app/skills/style_check.py`（新增，规范检查 skill）
- `app/api/chapters.py`（修订/一致性接口）
- `app/services/context_builder.py`（修订上下文构建）
- `app/storage/file_manager.py`（修订历史存储 + 规范文件路径）
- `app/static/js/components/chapter-writer.js`（修订 UI + diff 视图）
- `app/static/js/components/foreshadowing.js`（伏笔追踪增强）
- `tests/`（新增 3 个 skill 测试）

---

## v0.3.4 — 前端架构现代化

### 目标

治理前端技术债：全局命名空间 → ES 模块化、inline onclick → 事件委托、innerHTML 字符串拼接 → 模板化 DOM 构建。为 v0.4.0 的高级 UI 功能铺路。

### 模块化改造

- [ ] **ES 模块系统**：所有 JS 文件从全局函数迁移到 ES module（`export function renderX()` / `import { API } from './api.js'`）。`index.html` 使用 `<script type="module">`
- [ ] **消除 90+ 全局变量**：每个组件文件作为独立模块，仅暴露渲染入口函数。模块间通过显式 import 通信，不再依赖 window 全局
- [ ] **脚本加载顺序无关**：ES module 的静态 import 自动解析依赖图，不再需要手动排列 `<script>` 标签顺序

### 事件处理现代化

- [ ] **62 处 inline onclick → 事件委托**：`onclick="renderX()"` 替换为 `addEventListener('click', handler)`。在父容器上使用事件委托模式（`e.target.closest('[data-action]')`）处理动态生成元素
- [ ] **统一事件总线**：`EventBus` 类（自定义事件 + `document.dispatchEvent`），用于跨组件通信（如"项目切换"→ 所有面板刷新）。替代当前的全局函数直接调用模式
- [ ] **键盘快捷键系统**：`KeyboardManager` 类，注册/注销快捷键映射。预设：`Ctrl+S` 保存、`Ctrl+N` 新章节、`Ctrl+G` 生成、`Esc` 关闭弹窗

### DOM 构建安全化

- [ ] **`innerHTML` 替换为安全 DOM API**：使用 `document.createElement` + `textContent`（对用户数据）+ `insertAdjacentHTML`（对可信静态 HTML）。降低 XSS 风险面，避免 innerHTML 导致的已绑定事件监听器丢失
- [ ] **模板引擎引入**：轻量 DOM 模板辅助函数（`html\`<div>...</div>\`` tagged template），编译为 DocumentFragment。避免运行时 HTML 字符串拼接
- [ ] **marked.js 隔离**：Markdown 渲染结果在插入 DOM 前经过 DOMPurify 风格的清洗（去除 `<script>`、`onerror` 等危险内容）

### 构建工具链

- [ ] **esbuild 打包**：JS 模块打包为单文件 bundle，支持 tree-shaking。CSS 合并 + 压缩。产出 `app/static/dist/` 目录
- [ ] **Source map**：开发模式生成 source map，生产模式跳过
- [ ] **文件 hash 版本化**：`main.a3f2b1c.js` 而非 `main.js?v=11`，彻底消灭浏览器缓存问题
- [ ] **开发 watch 模式**：`esbuild --watch` 监听文件变化自动重新打包，配合 uvicorn reload

### 涉及文件

- `app/static/js/*.js`（全部 14 个 JS 文件模块化改造）
- `app/static/css/*.css`（合并/压缩流程）
- `app/static/index.html`（`type="module"` + bundle 引用）
- `build.js`（新增，esbuild 构建脚本）
- `package.json`（新增，esbuild 依赖）
- `app/static/js/utils/event-bus.js`（新增，事件总线）
- `app/static/js/utils/keyboard.js`（新增，快捷键管理）
- `app/static/js/utils/template.js`（新增，模板辅助函数）

---

## v0.4.0 — 知识图谱与高级功能

### 目标

引入可视化知识图谱，集成专业编辑器，打通"灵感 → 设定 → 大纲 → 正文 → 导出"的完整创作工作流。

### 知识图谱可视化

- [ ] **人物关系图**：基于 `人物关系.md` 数据，使用 D3.js 或 Canvas 渲染力导向图。节点=角色，边=关系类型（盟友/敌对/恋人/师徒），边标签=关系描述。支持拖拽节点、缩放、导出 PNG
- [ ] **时间线可视轴**：水平时间轴展示背景时间线 + 故事时间线，标注关键事件节点。事件卡片悬浮显示详情。支持缩放时间段
- [ ] **伏笔追踪图**：伏笔埋设 → 发展 → 回收流程的可视化看板。甘特图风格展示每个伏笔的跨章节生命周期
- [ ] **章节关联网络**：章节间通过角色出场、伏笔引用、事件关联建立连接。点击任意章节显示其"影响范围"

### Monaco Editor 集成

- [ ] **正文编辑器升级**：将当前 `<textarea>` 替换为 Monaco Editor（VS Code 内核）。功能：语法高亮、Markdown 预览、代码片段、多光标、查找替换
- [ ] **AI 辅助写作面板**：Monaco 侧边栏集成 AI 建议——选中文本后显示"扩写/缩写/改写/润色"选项。AI 建议以 CodeLens 形式内联显示
- [ ] **大纲侧边栏**：Monaco 编辑器中嵌入大纲树视图，点击大纲节点跳转到对应正文段落
- [ ] **分屏模式**：左屏正文编辑器 + 右屏设定参考（世界观/角色档案），写作时无需切换页面

### 项目导入/导出

- [ ] **项目 ZIP 导出**：`export_project_archive()` 实现——将 `projects/<name>/` 目录打包为 ZIP，包含所有 .md 设定 + 正文 + 大纲 + 版本历史。附带 `manifest.json` 元数据
- [ ] **项目 ZIP 导入**：`import_project_archive()` 实现——解压 ZIP，校验 `manifest.json` 完整性，合并到 `projects/` 目录。冲突时提示用户选择覆盖/跳过/重命名
- [ ] **跨设备同步基础**：导出/导入功能为未来云同步提供基础（v0.5.x 考虑）

### 多模型管线

- [ ] **任务-模型路由**：`config.json` 配置每个 skill 使用的模型。例如：大纲生成用 DeepSeek-V3（便宜）、正文写作用 GPT-4o（质量）、知识同步用 DeepSeek-R1（推理强）
- [ ] **模型性能对比**：同一 prompt 发送到 2 个模型，并排对比输出质量。用户投票选择偏好的模型-任务配对
- [ ] **本地模型支持**：通过 Ollama provider（v0.3.2 引入），支持完全离线运行（无需网络、无 API 费用）

### RAG 知识库

- [ ] **文档上传**：支持上传 PDF/TXT/EPUB 格式的原作资料（如二创场景下的原著小说）。自动分块、向量化存储
- [ ] **语义检索**：`/api/query` 从关键词匹配升级为向量相似度搜索。结合项目设定 + 上传文档，返回最相关片段
- [ ] **引用溯源**：AI 生成的设定/大纲/正文中，标注哪些结论来源于上传文档的哪些段落。可点击跳转原文

### 批量生成

- [ ] **批量章节生成**：选择卷/章节范围（如"第 5-10 章"），基于大纲队列生成。显示批量进度（3/6 完成）。支持断点续生成
- [ ] **生成队列管理**：暂停/继续/取消批量任务。失败章节自动重试（最多 3 次），最终生成批量报告

### 涉及文件

- `app/static/js/components/graph-view.js`（新增，知识图谱渲染）
- `app/static/js/components/monaco-editor.js`（新增，Monaco 集成）
- `app/storage/file_manager.py`（export/import 实现）
- `app/api/projects.py`（导出/导入接口）
- `app/services/llm.py`（多模型路由 + 本地模型）
- `app/services/vector_store.py`（新增，向量存储与检索）
- `app/api/query.py`（语义检索接口）
- `app/api/chapters.py`（批量生成接口）
- `app/skills/chapter_write.py`（批量模式适配）
- `config.json`（model_routing 配置段）

---

## v0.4.x — 协作与生态

### 未来探索方向（不承诺具体版本）

- **Git 集成**：项目文件天然适合 Git 版本控制（纯文本 Markdown）。内置 `git` 操作——自动 commit、diff 查看、branch 管理
- **插件系统**：开放 Skill 接口规范，允许用户编写自定义 skill（Python 脚本放入 `app/skills/user/`）。插件可注册新的设定类型、新的生成管线
- **写作统计与洞察**：字数趋势图、写作时段热力图、各角色出场频率/对话占比分析。帮助作者了解自己的写作模式
- **协作写作**：多人通过 Git 分支协作同一项目。冲突解决 UI。评论/审阅模式
- **发布集成**：导出为 EPUB/PDF 格式。自动生成目录、角色索引、术语表。对接网文平台发布 API
- **移动端适配**：响应式布局，手机/平板可访问核心功能（阅读设定、查看大纲、轻量编辑）
- **语音输入**：Web Speech API 实现语音转文字输入，适合灵感快速记录

---

*最后更新：2026-04-30（v0.3.0 已发布。v0.3.1-v0.4.x 路线图已详细规划）*
