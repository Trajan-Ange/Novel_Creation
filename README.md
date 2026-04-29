# 小说创作管理系统

AI 辅助小说创作管理工具 — 从世界观构建、人物设计到大纲规划、正文撰写的全流程支持。

![版本](https://img.shields.io/badge/版本-0.2.3-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![许可证](https://img.shields.io/badge/许可证-MIT-lightgrey)

**技术栈：** Python/FastAPI + 原生 JavaScript SPA + 文件系统存储（Markdown + JSON）

---

## 功能特性

- **项目管理** — 创建/删除/列表，支持原创与二创两种类型；右键快捷菜单删除项目
- **创作依据管理** — 世界观、人物设定、时间线、人物关系、风格指南
- **三级大纲生成** — 全书大纲 → 卷大纲 → 章节大纲
- **章节撰写** — SSE 流式生成 + 交互式反馈修改
- **手动创作模式** — Markdown 编辑器手动撰写大纲和正文，支持「AI 接管」从断点续写
- **知识同步引擎** — 每章完成后自动提取实体、事件、变更，更新所有设定文件
- **伏笔管理** — 埋设 → 追踪 → 揭示 → 回收，全生命周期管理
- **对话式设定创建** — 多轮 AI 访谈交互式生成创作依据
- **二创支持** — 基于 LLM 训练知识的原作世界观提取

---

## 快速开始

### 环境要求

- Python 3.10+
- 兼容 OpenAI 协议的 LLM API（DeepSeek、OpenAI、Ollama、vLLM 等）

### 安装

```bash
git clone <仓库地址>
cd Novel_Creation
pip install -r requirements.txt
```

### 配置

编辑 `config.json` 或通过界内设置面板配置：

```json
{
  "api_key": "your-api-key",
  "base_url": "https://api.deepseek.com",
  "model": "deepseek-v4-pro",
  "temperature": 0.7,
  "max_tokens": 393215
}
```

### 启动

```bash
python main.py
# 或双击 启动.bat（Windows）
```

浏览器访问 **http://127.0.0.1:8000**

---

## 项目结构

```
Novel_Creation/
├── main.py                    # FastAPI 入口，注册路由，挂载静态文件
├── config.json                # LLM 配置文件（gitignored）
├── requirements.txt           # Python 依赖
├── 启动.bat                   # Windows 一键启动脚本
├── app/
│   ├── api/                   # REST API + SSE 端点
│   │   ├── config.py          # LLM 配置 CRUD + 连接测试
│   │   ├── projects.py        # 项目 CRUD
│   │   ├── settings.py        # 创作依据 CRUD + 流式生成 + 对话式创建
│   │   ├── outline.py         # 大纲 CRUD + 生成
│   │   ├── chapters.py        # 章节生成流水线（SSE）+ 伏笔管理
│   │   ├── sync.py            # 知识同步 + 世界观提取
│   │   └── utils/             # SSE 辅助工具
│   ├── services/
│   │   └── llm.py             # LLMService：OpenAI 兼容客户端封装
│   ├── skills/                # AI 技能模块（SYSTEM_PROMPT + run 函数）
│   │   ├── world_design.py    # 世界设定
│   │   ├── character_design.py# 人物设定
│   │   ├── timeline.py        # 时间线
│   │   ├── relationship.py    # 人物关系
│   │   ├── outline.py         # 大纲生成（全书/卷/章节三级）
│   │   ├── chapter_write.py   # 正文撰写
│   │   ├── knowledge_sync.py  # 知识同步（6 阶段流水线）
│   │   ├── lore_extract.py    # 世界观提取（二创用）
│   │   └── writing_assist.py  # 记忆搜索、风格管理、写前检查
│   ├── storage/
│   │   └── file_manager.py    # 文件管理器：所有读写操作
│   └── static/                # 前端（原生 JS SPA）
│       ├── index.html
│       ├── css/
│       └── js/
│           ├── utils/         # SSE 客户端、API 客户端、辅助函数
│           ├── api.js, state.js, app.js
│           └── components/    # UI 组件（7 个面板）
└── projects/                  # 项目数据（每个项目一个子目录）
    └── <项目名称>/
        ├── 项目状态.json
        ├── 创作依据/           # 世界观、人物、时间线、人物关系、风格指南
        ├── 大纲/               # 全书 → 卷 → 章节大纲
        ├── 正文/               # 已撰写章节
        └── 伏笔管理/           # 伏笔追踪
```

---

## API 端点速查

### 健康检查
```
GET /api/health
```

### 配置 (`/api/config`)
```
GET  /              获取配置（Key 脱敏）
PUT  /              更新配置
POST /test          测试 LLM 连接
```

### 项目 (`/api/projects`)
```
GET    /            列出所有项目
POST   /            创建项目
DELETE /{name}      删除项目
```

### 创作依据 (`/api/settings`)
```
GET  /{project}/all                     获取所有设定（供 LLM 上下文用）
GET  /{project}/world                   获取世界设定
GET  /{project}/characters              列出角色名
POST /{project}/characters/generate     AI 生成角色
PUT  /{project}/characters/{name}       保存角色
GET  /{project}/timeline                获取时间线
GET  /{project}/relationship            获取人物关系
POST /stream-generate                   SSE：一次性流式生成
POST /chat-generate                     SSE：交互式对话创建
```

### 大纲 (`/api/outline`)
```
GET  /{project}/book                           获取全书大纲
POST /{project}/book/generate                  生成全书大纲
GET  /{project}/volume/{vol}                   获取卷大纲
POST /{project}/volume/{vol}/generate          生成卷大纲
GET  /{project}/volume/{vol}/chapter/{ch}      获取章节大纲
POST /{project}/volume/{vol}/chapter/{ch}/generate  生成章节大纲
```

### 正文 (`/api/chapters`)
```
GET  /{project}/volume/{vol}               列出已写章号
GET  /{project}/volume/{vol}/chapter/{ch}  获取章节内容
POST /generate                             SSE：完整章节撰写流水线
POST /feedback                             SSE：大纲确认/修改反馈
POST /query                                记忆搜索
GET  /{project}/foreshadowing              获取伏笔清单
```

### 同步 (`/api/sync`)
```
POST /{project}/trigger        手动触发知识同步
POST /{project}/lore-extract   从已知 IP 提取世界观
```

---

## 核心架构

### 知识同步引擎（v0.2.0 重构：12+ → 2~4 次 LLM 调用）

每章写完后自动执行，核心创新机制：

```
阶段 0：上下文预加载  →  一次性加载全部设定，全局缓存复用
阶段 1：文字分析       →  纯文字创作要素分析报告（1 次 LLM）
阶段 2：五领域并行提取 →  人物/事件/世界/关系/伏笔并发分析（1 个并发批次）
阶段 3：程序化更新     →  Markdown 直接操作，LLM 仅在复杂变更时触发（0-1 次 LLM）
阶段 4：更新报告       →  生成人类可读的更新摘要
```

### SSE 流式传输通用格式

所有 SSE 端点返回统一的消息格式：

```
data: {"type":"status","message":"..."}
data: {"type":"text_chunk","text":"..."}
data: {"type":"complete","phase":"...","history":[...]}
data: {"type":"error","message":"..."}
```

---

## 常见问题排查

| 问题 | 解决方法 |
|------|----------|
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| LLM 调用失败 | 检查 `config.json` 中的 API Key 和 Base URL；使用界面内"测试连接"按钮验证 |
| SSE 连接卡住 | 先用 `/api/config/test` 确认 LLM 正常响应；查看服务器终端日志 |
| 端口 8000 被占用 | `netstat -ano \| findstr 8000` 然后 `taskkill /PID <进程号> /F` |

---

## 相关文档

- [更新日志](CHANGELOG.md)
- [版本路线图](ROADMAP.md)
- [设计规格说明](docs/design-spec.md)

---

## 许可证

MIT
