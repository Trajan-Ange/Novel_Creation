# 版本路线图 (Roadmap)

---

## 已完成

### v0.1.2 — 流式生成修复与章节管理（2026-04-28）

- **严重修复**：DeepSeek V4 推理阶段阻塞流式输出 — `_chat_stream()` 现在正确 yield 推理内容
- **严重修复**：知识同步在事件提取阶段卡住 — `max_tokens` 提升至 8192，时间线上下文精简，120s 超时
- 章节大纲流式生成
- 知识同步流式进度推送（SSE status 事件）
- 章节管理系统（`chapter-manager.js`）
- 双输入框 Bug 修复
- 推理内容过滤（仅向用户展示实际内容）

### v0.1.1 — 知识同步引擎修复（2026-04-27）

- **架构重构**：单一 LLM 调用 → 6 阶段流水线（文字分析 + 5 个领域独立提取）
- JSON 解析器：四策略回退（`---JSON---` / 代码块 / 平衡花括号）
- 时间线拆分容错：多种标题变体回退
- 同步失败前端可见（SSE error 事件推送）
- 每阶段独立调试文件

### v0.1.0 — 安全与稳定性（2026-04-27）

- 路径遍历漏洞修复、HTTP 状态码规范化、伏笔 ID 碰撞修复
- LLM 指数退避重试、SSE 客户端断连检测
- 死代码清理（469 行）、重复代码合并、移除未使用依赖

### v0.0.1 — 首次发布（2026-04-27）

- 项目管理、创作依据管理、三级大纲生成、SSE 流式章节撰写
- 知识同步引擎（基础版）、伏笔管理、对话式设定创建、二创世界观提取

---

## v0.1.3 — 手动创作支持与用户体验修复（已完成 ✅）

### 手动创作能力（用户需求）

- [x] **返回项目列表按钮**：在项目内部导航栏增加返回初始 UI 的入口
- [x] **侧边栏项目右键菜单**：右键项目名弹出快捷操作（删除项目等）
- [x] **手动创建章节流程**：用户可完全手动创建新卷/章
  - 选择卷号、章号 → 进入文本编辑界面
  - 先编写章节大纲（Markdown 编辑器）
  - 大纲写作中可随时点击"AI 接管"让 AI 补全剩余内容
  - 大纲完成后保存 → 可选择手动写正文或 AI 生成正文
  - 正文完成 → 自动触发知识同步更新
- [x] **章节正文手动编辑**：`chapter-writer.js` 增加 Markdown 编辑区，支持用户自行撰写/修改正文
- [x] **AI 接管按钮**：手动编辑界面中始终可见"AI 接管"按钮，AI 从已有内容继续补全
- [x] **后端章节保存 API**：新增 `PUT /api/chapters/{project}/volume/{vol}/chapter/{ch}` 端点，支持保存用户手动编写的正文

### 严重缺陷修复（代码审查发现）

- [x] **C1 — `sync.py` 独立同步端点完全不可用**：`await sync_run()` 改为 `async for` 迭代收集结果
- [x] **C3 — 角色名路径遍历漏洞**：新增 `_validate_char_name()` 拒绝路径分隔符
- [x] **C4 — 文件写入非原子操作**：改为"写临时文件 + 原子重命名"
- [x] **C5 — 章节写入失败静默丢失**：写盘包装 try/except，失败时发送 error SSE 事件
- [x] **C6 — 同步失败时仍发送 done 事件**：同步失败时发送 error 后直接 return
- [x] **H2 — 知识同步 LLM 错误被静默吞没**：`_call_llm()` 异常时记录 warning 日志
- [x] **M8 — 更新报告中缺失 f-string**：普通字符串改为 f-string

### 中等缺陷修复

- [x] **M1 — 删除项目异常未处理**：`shutil.rmtree` 包装 try/except
- [x] **M3 — `_split_characters` 遇 H2 标题全部丢失**：h1 匹配为空时回退到 h2
- [x] **M4 — 角色名称提取不可靠**：用正则从指令中提取实际角色名
- [x] **M7 — 伏笔 ID 跨卷冲突**：伏笔 ID 格式改为 `FB-{volume:02d}-{chapter:03d}-{idx:02d}`
- [x] **M10 — 流式生成角色保存为单一文件**：`_split_characters()` 拆分后逐个写入

### 前端修复

- [x] **C3（前端）— SSE 连接导航时未清理**：`navigate()` 开头断开所有活跃 SSE 连接
- [x] **H9 — SSE 客户端 JSON 解析错误被静默吞没**：catch 块添加 `console.error` 输出
- [x] **H8 — SSE 无超时机制**：`SSEClient` 支持 `timeout` 参数（默认 5 分钟）

---

## v0.1.4 — 代码清理与 v0.2.0 基础设施准备

### 目标

本次更新不聚焦于用户可见功能，而是清理代码层面的低效冗余，为 v0.2.0 知识同步引擎深度重构扫清障碍。

### A 组：后端基础设施清理（阻塞 v0.2.0）

- [x] **A1 — 消除 36 处闭包内 import**：`settings.py`（21处）、`chapters.py`（9处）、`knowledge_sync.py`（5处）、`outline.py`（3处）、`sync.py`（2处）。全部提升至模块顶层。经审查无循环依赖风险。

- [ ] **A2 — 统一技能返回类型**：为非流式技能定义统一的返回 dataclass（`SkillResult`），替代当前的 `dict` / `AsyncIterator` 混用。→ **推迟至 v0.2.0**（需同步修改 9 个技能模块，风险过高，v0.2.0 重构时一并进行）。

- [x] **A3 — 消除 `_project_path()` 和 `_chat_stream()` 外部调用**：新增 `fm.get_project_abs_path()` 公开方法 + `llm.chat_messages()` 公开 API。所有外部调用已迁移。

- [x] **A4 — `get_all_settings()` 上下文缓存**：新增 5 秒 TTL 内存缓存层 + 关键写入路径缓存失效。同一请求周期内避免重复读取。

- [ ] **A5 — I/O 异步化基础**：所有 `FileManager` 同步方法包装 `run_in_executor()`。→ **推迟至 v0.2.0**（需 `aiofiles` 依赖 + 所有调用点适配，与 Phase 2 并行化联动）。

- [x] **A6 — 上下文构建逻辑统一**：新增 `app/services/context_builder.py`（`build_full_context` / `build_targeted_context` / `build_chapter_context`），集中管理上下文组装。

- [x] **A7 — 错误处理基础**：`file_manager.py` 和 `chapters.py` 引入 `logging` 模块。`项目状态.json` JSON 解码失败时通过 `logger.exception()` 告警而非静默返回 `{}`。

- [x] **A8 — 硬编码值集中管理**：新增 `app/services/constants.py`，统一管理 `max_tokens`、`timeout`、重试次数等常数值。

### B 组：前端架构清理

- [x] **B1 — SSE 连接工厂统一**：`sse.js` 新增 `createSSEConnection(url, body, handlers)` 工厂函数。

- [x] **B2 — API 调用错误处理包装**：`api.js` 新增 `safeApiCall(fn, errorMsg, onError)` 包装函数。

- [x] **B3 — 消除 API 对象内 4 方法重复代码**：`get()`/`post()`/`put()`/`del()` 的通用逻辑提取为 `_request(method, url, body)` 私有方法。

- [x] **B4 — 状态反馈色彩 CSS 化**：`main.css` 新增 `.status-success` / `.status-error` / `.status-warning` / `.status-info` CSS 类。

- [x] **B5 — XSS 高危点修复**：project-list.js 项目名 XSS 已在 v0.1.3 修复（data-project + 事件委托）。`escapeHtml()` 已存在于 helpers.js。

- [x] **B6 — 全局变量初步收束**：新增 `app/static/js/namespace.js`，所有组件可通过 `window.NovelApp` 命名空间访问。

### C 组：跨模块一致性

- [x] **C1 — FileManager 命名规范化**：新增 `read_project_state()` / `write_project_state()` 别名方法，统一四类前缀。

- [x] **C2 — 错误响应格式统一**：新增 `app/api/utils/error_response.py`，提供 `error_response()` / `http_error_detail()` / `sse_error()` 标准化辅助函数。

- [x] **C3 — 废弃死代码移除**：已移除未使用的 `write_foreshadowing_list()` 方法。

### 不在 v0.1.4 范围内（推迟到 v0.2.0+）

- ❌ innerHTML 全面替换 DOM API（工程量过大，渐进式推进）
- ❌ 109 个全局变量全面模块化（需要前端构建工具或 ES Module 迁移）
- ❌ 62 处 inline onclick 改为事件委托（与 innerHTML 替换联动）
- ❌ 前端路由系统（hash-based）
- ❌ pytest 测试覆盖
- ❌ 暗色模式 / Monaco Editor / 移动端适配

---

## v0.2.0 — 知识同步引擎深度重构 ⭐ 里程碑

### 问题诊断

当前知识同步在一次章节写入后执行 **12 次以上串行 LLM 调用**：

| 阶段 | 调用次数 | 当前方式 |
|------|---------|---------|
| Phase 1: 文字分析 | 1 | 串行 |
| Phase 2a~2e: 五领域独立提取 | 5 | **串行**（独立无依赖，可并行） |
| Phase 3: 人物逐条更新 | N（每角色1次） | **串行**，且每次重读全部设定 |
| Phase 3: 事件/世界/关系更新 | 3 | 串行 |
| Phase 4: 报告生成 | 1 | 串行 |

**实际耗时 60-120 秒**，对交互式创作体验不可接受。

此外：
- 每个 Phase 3 角色更新调用独立触发 `char_skill()` → 内部再读一次 `fm.get_all_settings()` → 10 个角色 = 10 次全量文件读取
- Phase 2 的 5 个提取调用接收相同的 `analysis` 输入，互相无依赖，却串行执行
- Phase 3 大量"追加"操作（新增事件到时间线、追加关系条目）本可程序化完成，却各自发起一次 LLM 调用
- AI 将全章内容无差别作为更新素材，未做重要度筛选

### 重构目标

- **总 LLM 调用数**：12+ → **2~4 次**
- **同步耗时**：60-120s → **10-25s**
- **核心原则**：能用程序完成的操作不用 LLM，能并行的调用不串行

### 具体方案

- [ ] **Phase 2 五领域并行化**：`_extract_characters` / `_extract_events` / `_extract_world` / `_extract_relationships` / `_extract_foreshadowing` 使用 `asyncio.gather` 并发执行，5 次调用 → 1 个并发批次
- [ ] **Phase 3 角色批量更新**：将所有新角色和更新角色合并为单次 LLM 调用，而非逐角色调用 `char_skill()`。`character_design.py` 新增 `batch_update` action
- [ ] **Phase 3 简单更新程序化**：对于纯追加操作（时间线新增事件、关系新增条目、世界设定新增地点），从 Phase 2 提取的结构化 JSON 直接程序化拼接到 Markdown 文件，不发起额外 LLM 调用。仅在需要重写已有内容时才调用 LLM
- [ ] **重要度筛选**：Phase 2 提取时仅关注实质性新增/变化，忽略已有信息的重复描述，减少 Phase 3 的无效更新项
- [ ] **上下文缓存**：sync 开始时一次性加载 `get_all_settings()`，缓存后供所有阶段复用，避免 Phase 3 每角色一次重读
- [ ] **`_process_foreshadowing` 异步化**：改为 `async def`，文件 I/O 不阻塞事件循环
- [ ] **Phase 3 事件/世界/关系更新合并**：将三个独立 LLM 调用合并为一次调用处理所有剩余更新
- [ ] **调试文件可选**：通过参数控制是否写入调试文件，生产环境可关闭以减少 I/O
- [ ] **旧调试文件自动清理**：保留最近 N 次同步的调试文件，自动删除更早的文件

### 架构改进（同步相关）

- [ ] **H1（后端）— Phase 3 角色逐条 LLM 调用改为批量**：见上方 Phase 3 批量更新
- [ ] **H3 — `_process_foreshadowing` 同步阻塞改异步**：`def` → `async def`，文件 I/O 使用 `aiofiles` 或线程池
- [ ] **H5 — 对话生成上下文膨胀**：`settings.py` chat_generate 的 `get_all_settings` 对于 10+ 角色项目可能超 30K tokens。按相关性筛选而非全量注入
- [ ] **H6 — 章节大纲生成上下文过大**：`outline.py` create_chapter 包含 3 个大纲 + 2 个章节全文 + 全部设定，可超 40K tokens。精简上下文策略
- [ ] **H7 — 时间线拆分逻辑加固**：支持 `##` 标题、无标题等更多 LLM 输出格式变体

---

## 远期（v0.3.0+）— 体验打磨与高级功能

### 安全加固
- [ ] API Key 环境变量支持（`NOVEL_LLM_API_KEY`）
- [ ] 项目名校验增强（长度限制、空格名拒绝、Windows 保留名拦截）
- [ ] 错误信息脱敏（不泄露堆栈信息）
- [ ] CORS 限制为本地地址

### 工程质量
- [ ] 基础测试覆盖（pytest + httpx）
- [ ] 结构化日志（替换 `print`）
- [ ] 上下文构建逻辑统一（消除 settings.py / chapters.py / 各 skill 中的重复代码）
- [ ] 模块顶层导入（消除闭包内 import）

### 体验增强
- [ ] SSE 自动重连（指数退避）
- [ ] 导航确认（有活跃 SSE 连接时提示用户）
- [ ] 浏览器历史支持（`pushState`，支持前进/后退/深链）
- [ ] 版本快照（可回退到历史设定版本）
- [ ] 冲突检测（新增内容与已有设定的自动扫描）
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
- [ ] 统一 SSE 客户端模式（消除 4 处重复的 SSE 创建/回调模式）
- [ ] `innerHTML` 全面替换为安全 DOM API（降低 XSS 风险面 + 避免事件监听器丢失）
- [ ] 前端路由系统（hash-based，支持深链和浏览器导航）

---

*最后更新：2026-04-28（v0.1.4 代码清理完成 — 14/17 任务完成，3 项推迟至 v0.2.0）*
*代码审查覆盖：24 个后端文件 + 13 个前端文件，共发现 6 CRITICAL / 11 HIGH / 15 MEDIUM / 14 LOW — 严重/中等项已于 v0.1.3 全部修复*
