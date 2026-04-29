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

## v0.3.0+ — 体验打磨与高级功能

### 体验增强
- [ ] 知识图谱可视化（人物关系图、时间线图）
- [ ] 暗色模式
- [ ] Monaco Editor 集成
- [ ] 键盘快捷键

### 高级功能
- [ ] 多模型配置（便宜模型做大纲，强力模型写正文）
- [ ] RAG 知识库（用户上传原作资料文档）
- [ ] 批量章节生成
- [ ] 修订模式（对已写章节局部修改）
- [ ] 移动端适配
- [ ] 项目导出/导入（zip 打包）

### 前端架构债
- [ ] 全局命名空间治理（90+ 全局变量，高碰撞风险）
- [ ] `innerHTML` 全面替换为安全 DOM API（降低 XSS 风险面 + 避免事件监听器丢失）
- [ ] 前端路由系统（hash-based，支持深链和浏览器导航）
- [ ] 62 处 inline onclick 改为事件委托

---

*最后更新：2026-04-29（v0.2.4 已发布 — 代码清理与 v0.3.0 预备）*
