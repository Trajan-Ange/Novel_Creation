# 小说创作管理系统 — AI 助手操作指南

## 项目概述

这是一个基于 **FastAPI + 原生 JavaScript** 的小说创作管理系统。核心功能是通过 AI（LLM）辅助作者完成从世界观设定、人物设计、大纲规划到正文撰写的全流程创作。

- **后端**: Python FastAPI，通过 OpenAI 兼容接口调用 LLM
- **前端**: 原生 JavaScript SPA（无框架，无构建步骤）
- **存储**: 纯文件系统（Markdown + JSON），无数据库依赖
- **通信**: REST API + SSE（Server-Sent Events）流式传输

---

## 1. 环境要求

| 依赖 | 版本要求 |
|------|---------|
| Python | 3.10+ |
| pip | 随 Python 安装 |
| 浏览器 | Chrome / Edge / Firefox 最新版 |

Python 依赖包（`requirements.txt`）：

```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
openai>=1.30.0
python-multipart>=0.0.9
aiofiles>=23.2.0
```

---

## 2. 快速启动

### 2.1 安装依赖并启动

```bash
# 进入项目目录
cd G:\Novel_Creation

# 安装依赖
pip install -r requirements.txt

# 启动服务器
python main.py
```

服务器启动后访问：**http://127.0.0.1:8000**

也可以直接双击 `启动.bat`，它会自动安装依赖、打开浏览器并启动服务器。

### 2.2 验证服务运行

```bash
curl http://127.0.0.1:8000/api/health
# 返回: {"status":"ok"}
```

---

## 3. 配置 LLM 连接

项目使用 OpenAI 兼容的 API 协议，支持任何兼容的 LLM 提供商（DeepSeek、OpenAI、Ollama、vLLM 等）。配置文件为项目根目录的 `config.json`：

```json
{
  "api_key": "your-api-key",
  "base_url": "https://api.deepseek.com",
  "model": "deepseek-v4-pro",
  "temperature": 0.7,
  "max_tokens": 393215
}
```

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `api_key` | LLM 提供商的 API Key | 空 |
| `base_url` | OpenAI 兼容的 API 地址 | `https://api.openai.com/v1` |
| `model` | 模型名称 | `gpt-4o` |
| `temperature` | 采样温度 (0-2) | `0.7` |
| `max_tokens` | 最大输出 token 数 | `4096` |

**配置方式**：
1. 直接编辑 `config.json` 文件
2. 通过 UI：启动后点击右上角「API 配置」，填入信息并测试连接

---

## 4. 项目目录结构

```
G:\Novel_Creation\
├── main.py                          # FastAPI 入口，注册路由，挂载静态文件
├── config.json                      # LLM 配置文件
├── requirements.txt                 # Python 依赖
├── 启动.bat                         # Windows 一键启动脚本
├── app/
│   ├── api/                         # API 路由层
│   │   ├── config.py                # GET/PUT 配置、POST 测试连接
│   │   ├── projects.py              # 项目的 CRUD
│   │   ├── settings.py              # 创作依据的 CRUD + 流式生成 + 对话式创建
│   │   ├── outline.py               # 大纲的 CRUD + 生成
│   │   ├── chapters.py              # 章节生成流水线（SSE）+ 伏笔管理
│   │   └── sync.py                  # 知识同步、IP 提取
│   ├── core/
│   │   └── orchestrator.py          # 工作流编排器（创建项目、应用 lore）
│   ├── services/
│   │   └── llm.py                   # LLMService：OpenAI 兼容客户端封装
│   ├── skills/                      # AI 技能模块（每个模块含 SYSTEM_PROMPT + run 函数）
│   │   ├── world_design.py          # 世界设定
│   │   ├── character_design.py      # 人物设定
│   │   ├── timeline.py              # 时间线
│   │   ├── relationship.py          # 人物关系
│   │   ├── outline.py               # 大纲生成（全书/卷/章节三级）
│   │   ├── chapter_write.py         # 正文撰写
│   │   ├── knowledge_sync.py        # 知识同步（核心创新：写完后自动更新所有设定）
│   │   ├── lore_extract.py          # IP 提取（同人作品用）
│   │   └── writing_assist.py        # 写作辅助（记忆搜索、风格管理、写前检查）
│   ├── storage/
│   │   └── file_manager.py          # 文件管理器：所有读写操作
│   └── static/                      # 前端静态文件
│       ├── index.html               # SPA 外壳
│       ├── css/                     # 3 个样式文件
│       └── js/                      # 10 个脚本文件
│           ├── utils/sse.js         # SSE 客户端类
│           ├── api.js               # REST API 客户端
│           ├── state.js             # 全局状态管理 + 路由
│           ├── app.js               # 初始化入口
│           └── components/          # UI 组件
│               ├── config-panel.js      # API 配置面板
│               ├── project-list.js      # 项目管理 + 创建向导
│               ├── settings-editor.js   # 创作依据管理
│               ├── settings-chat.js     # 交互式对话创建
│               ├── outline-tree.js      # 大纲树管理
│               ├── chapter-writer.js    # 章节撰写界面
│               └── foreshadowing.js     # 伏笔管理
└── projects/                        # 项目数据存储（每个项目一个子目录）
    └── 修仙/                         # 示例项目
        ├── 项目状态.json
        ├── 创作依据/
        │   ├── 世界设定.md
        │   ├── 人物设定/            # 每人一个 .md 文件
        │   ├── 时间线/
        │   ├── 人物关系.md
        │   └── 风格指南.md
        ├── 大纲/
        │   ├── 全书大纲.md
        │   └── 第N卷/
        │       ├── 卷大纲.md
        │       └── 章节大纲/
        └── 正文/
            └── 第N卷/
                └── 第M章.md
```

---

## 5. 功能模块与操作流程

### 5.1 API 配置（右上角按钮）

1. 点击「API 配置」
2. 填入 API Key、Base URL、Model
3. 点击「测试连接」确保配置正确
4. 点击「保存配置」

### 5.2 项目管理（侧边栏）

- **创建项目**：点击「新建项目」→ 输入名称 → 选择类型（原创/同人）→ 可选开启创建向导
- **切换项目**：点击侧边栏项目名
- **删除项目**：点击项目旁的删除按钮

#### 创建向导（6步交互式流程）

如果选择「使用创建向导」，系统会依次引导创建：世界设定 → 人物设定 → 时间线 → 人物关系 → 大纲 → 风格指南。每一步都是流式生成，完成后点击「接受」进入下一步。

### 5.3 创作依据管理

进入项目后点击侧边栏「创作依据」。共 5 个标签页：

| 标签 | 说明 |
|------|------|
| 世界设定 | 世界观、地理、势力、力量体系 |
| 人物设定 | 角色档案（支持多角色，每人独立文件） |
| 时间线 | 背景时间线 + 故事时间线 |
| 人物关系 | 角色关系图谱 |
| 风格指南 | 写作风格规范 |

每个标签页有两个按钮：
- **「AI 对话创建」**：打开聊天界面，AI 以访谈者身份逐步询问信息，多轮对话后生成完整设定文档。**推荐使用此方式**。
- **「手动编辑」**：直接在 Markdown 编辑器中编写。

### 5.4 大纲管理

点击「大纲管理」进入。分三级结构：
- **全书大纲**：确定各卷定位和主线
- **卷大纲**：确定本卷核心矛盾、章节划分
- **章节大纲**：确定单章核心事件、人物目标、伏笔

点击具体大纲项 → 显示内容 → 点击「AI 对话创建」进行交互式生成或更新。

### 5.5 正文撰写

点击「正文撰写」进入。操作流程：
1. 选择卷号和章号
2. 点击「开始撰写」→ 系统检查大纲完整性
3. AI 先生成章节大纲供确认
4. 用户确认后 AI 流式生成正文
5. 写完后自动执行知识同步（提取新人物、事件、关系变更等，更新所有创作依据）

### 5.6 伏笔管理

追踪和管理故事中的伏笔。可在侧边栏「伏笔管理」中查看和搜索。

---

## 6. API 端点速查

### 健康检查
```
GET /api/health
```

### 配置 (prefix: /api/config)
```
GET  /api/config          # 获取配置（key 脱敏）
PUT  /api/config          # 更新配置
POST /api/config/test     # 测试 LLM 连接
```

### 项目 (prefix: /api/projects)
```
GET    /api/projects          # 列出所有项目
POST   /api/projects          # 创建项目
DELETE /api/projects/{name}   # 删除项目
```

### 创作依据 (prefix: /api/settings)
```
GET  /{project}/all                      # 获取所有设定（上下文用）
GET  /{project}/world                    # 获取世界设定
PUT  /{project}/world                    # 保存世界设定
GET  /{project}/characters               # 列出角色名
GET  /{project}/characters/{name}        # 获取角色档案
POST /{project}/characters/generate      # AI 生成角色
PUT  /{project}/characters/{name}        # 保存角色
DELETE /{project}/characters/{name}      # 删除角色
GET  /{project}/timeline                 # 获取时间线
PUT  /{project}/timeline                 # 保存时间线
GET  /{project}/relationship             # 获取人物关系
PUT  /{project}/relationship             # 保存人物关系
GET  /{project}/style-guide              # 获取风格指南
PUT  /{project}/style-guide              # 保存风格指南
POST /stream-generate                    # SSE: 一次性流式生成
POST /chat-generate                      # SSE: 交互式对话创建
```

### 大纲 (prefix: /api/outline)
```
GET  /{project}/book                              # 获取全书大纲
PUT  /{project}/book                              # 保存全书大纲
POST /{project}/book/generate                     # 生成全书大纲
GET  /{project}/volume/{vol}                      # 获取卷大纲
PUT  /{project}/volume/{vol}                      # 保存卷大纲
POST /{project}/volume/{vol}/generate             # 生成卷大纲
GET  /{project}/volume/{vol}/chapter/{ch}         # 获取章节大纲
PUT  /{project}/volume/{vol}/chapter/{ch}         # 保存章节大纲
POST /{project}/volume/{vol}/chapter/{ch}/generate # 生成章节大纲
GET  /{project}/volumes                           # 列出卷号
GET  /{project}/volume/{vol}/chapters             # 列出某卷的章号
```

### 正文 (prefix: /api/chapters)
```
GET  /{project}/volume/{vol}                  # 列出已写章号
GET  /{project}/volume/{vol}/chapter/{ch}     # 获取章节内容
POST /generate                                # SSE: 完整章节撰写流水线
POST /feedback                                # SSE: 大纲确认/修改反馈
POST /query                                   # 记忆搜索
GET  /{project}/foreshadowing                 # 获取伏笔清单
```

### 同步 (prefix: /api/sync)
```
POST /{project}/trigger        # 手动触发知识同步
POST /{project}/lore-extract   # 从已知 IP 提取世界观
```

### SSE 流式端点通用格式

所有 SSE 端点返回格式：
```
data: {"type":"status","message":"..."}
data: {"type":"text_chunk","text":"..."}
data: {"type":"complete","phase":"interview|generation","history":[...]}
data: {"type":"error","message":"..."}
```

---

## 7. 核心架构

### 7.1 LLM 服务层 (`app/services/llm.py`)

`LLMService` 封装了 OpenAI Python SDK 的 `AsyncOpenAI` 客户端。关键方法：

- `chat(system_prompt, user_message, temperature, max_tokens, stream)` — 单轮对话
- `chat_with_context(system_prompt, context_docs, user_message, ...)` — 带上下文的对话（将所有已有设定作为参考材料注入）
- `chat_with_context_and_json(...)` — 同上，但从回复中解析结构化 JSON
- `update_config(config_dict)` — 热重载配置
- `is_configured()` — 检查是否已配置 API Key

### 7.2 文件管理器 (`app/storage/file_manager.py`)

所有文件 I/O 的统一入口。关键特点：
- 纯 Markdown + JSON 存储
- 自动创建所需目录
- `get_all_settings(project)` — 收集所有创作依据作为 LLM 上下文
- `search(project, query)` — 关键词搜索所有 .md 文件

### 7.3 技能模块 (`app/skills/`)

每个技能模块导出 `SYSTEM_PROMPT`（LLM 指令）和 `async def run(llm, fm, project, params)` 函数。技能之间无直接依赖，通过文件管理器读取彼此产出的设定文件。

### 7.4 知识同步机制（核心创新）

每章写完后，`knowledge_sync.py` 自动执行：
1. 分析新章节内容，提取实体、事件、变更
2. 将变更分发到对应技能模块
3. 自动更新世界设定、人物档案、时间线、人物关系
4. 更新项目版本号

### 7.5 前端 SSE 处理 (`app/static/js/utils/sse.js`)

`SSEClient` 类读取 `fetch` 响应的 `ReadableStream`，逐行解析 `data: {json}\n\n` 帧，触发 `onEvent` 回调。

---

## 8. AI 助手的测试流程

作为运行在云电脑上的 AI 助手，请按以下流程测试所有功能：

### 步骤 1：环境检查
```bash
python --version           # 应为 3.10+
pip list | findstr openai  # 检查 openai 包已安装
pip list | findstar fastapi
```

### 步骤 2：启动服务
```bash
cd G:\Novel_Creation
pip install -r requirements.txt
start /B python main.py    # 后台启动
```

### 步骤 3：验证服务
```bash
curl http://127.0.0.1:8000/api/health
```
预期返回 `{"status":"ok"}`。

### 步骤 4：配置 LLM
确认 `config.json` 中的 API Key 和模型名称正确。可用以下命令测试：
```bash
curl -X POST http://127.0.0.1:8000/api/config/test -H "Content-Type: application/json"
```

### 步骤 5：浏览器测试

打开浏览器访问 `http://127.0.0.1:8000`，按顺序测试：

1. **API 配置** — 点击右上角「API 配置」，确认连接测试通过
2. **创建项目** — 创建一个测试项目（名称可用"测试项目"）
3. **创作依据** — 进入项目后点「创作依据」，在每个标签页测试「AI 对话创建」：
   - 世界设定：AI 应自我介绍并提问
   - 人物设定：回答几轮后点击「生成人物设定」
   - 时间线、人物关系、风格指南：同样验证多轮对话 + 生成
4. **大纲管理** — 点「大纲管理」，测试「生成全书大纲」、「生成卷大纲」
5. **正文撰写** — 点「正文撰写」，选择卷号、章号，测试完整撰写流程
6. **项目管理** — 返回项目列表，确认项目已创建

### 步骤 6：检查输出文件

对话创建和大纲生成后，检查项目目录中的文件是否有内容：
```bash
cd G:\Novel_Creation\projects\测试项目
dir /s /b   # 列出所有文件
type 创作依据\世界设定.md
```

---

## 9. 常见问题排查

### 问题：启动报错 ModuleNotFoundError
```bash
pip install -r requirements.txt
```

### 问题：LLM 调用失败
- 检查 `config.json` 中的 `api_key` 是否有效
- 检查 `base_url` 是否正确（注意不要以 `/v1` 结尾，SDK 会自动拼接）
- 通过 UI 的「测试连接」按钮验证

### 问题：SSE 连接卡住
- 确认 LLM 可以正常响应（先用 `/api/config/test` 测试）
- 查看服务器终端日志

### 问题：端口 8000 被占用
```bash
netstat -ano | findstr 8000
# 找到占用进程后：
taskkill /PID <PID> /F
```

### 问题：创建的人物设定被合并成一个文件
批量生成多个角色时，系统会自动按 `# 角色名` 标题分割成独立文件。如果角色名不在同一格式下，可能需要手动编辑。

---

## 10. 技术要点

1. **`llm.chat()` 是 `async def`（协程），需要 `await`**。调用 `llm.chat(..., stream=True)` 返回的是 async generator，需要先 `await` 再 `async for`。
2. **`llm._chat_stream()` 是 `async def` + `yield`（async generator 函数）**，调用它直接返回 async generator，**不要** `await`，直接用 `async for`。
3. **SSE 端点返回 `StreamingResponse(event_stream(), media_type="text/event-stream")`**，其中 `event_stream` 是 `async def` + `yield` 的 async generator 函数。
4. **设定之间可互相引用**：在生成过程中，系统会自动读取已有的设定文件作为上下文传给 LLM（例如生成时间线时可参考世界设定）。
5. **大纲创建使用对话模式**：全书大纲、卷大纲、章节大纲的 AI 创建入口现在都使用交互式对话模式（`openOutlineChat`），与创作依据保持一致。

---

## 11. 开发者注意事项

- 项目中 `app/api/settings_chat.py` 是旧版本残留，实际聊天端点已合并到 `app/api/settings.py` 中。**不要使用此文件**。
- 前端 JS 脚本之间有加载顺序依赖：`sse.js` → `api.js` → `state.js` → components → `app.js`
- 所有全局函数和变量使用 window 全局命名空间（无模块系统），命名时注意避免冲突
- Markdown 渲染使用 CDN 加载的 `marked.js`
