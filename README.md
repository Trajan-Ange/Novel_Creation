# Novel Creation System

AI-assisted novel creation management system — from worldbuilding and character design to outline planning and chapter writing.

![Version](https://img.shields.io/badge/version-0.1.2-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

**Tech Stack:** Python/FastAPI + Vanilla JavaScript SPA + File-based Storage (Markdown + JSON)

---

## Features

- **Project Management** — Create/delete projects, support original and fan-fiction types
- **Creation Basis** — World settings, character profiles, timeline, character relationships, style guide
- **Three-level Outlines** — Book → Volume → Chapter outline generation
- **Chapter Writing** — SSE streaming generation with interactive feedback loop
- **Knowledge Sync Engine** — Auto-extract entities, events, and changes after each chapter; update all setting files
- **Foreshadowing Management** — Plant → Track → Reveal → Recover full lifecycle
- **Chat-based Setting Creation** — Multi-turn interview-style generation of creation basis
- **Fan-fiction Support** — Extract original work worldbuilding via LLM knowledge

---

## Quick Start

### Prerequisites

- Python 3.10+
- A compatible LLM API (DeepSeek, OpenAI, Ollama, vLLM, etc.)

### Installation

```bash
git clone <repo-url>
cd Novel_Creation
pip install -r requirements.txt
```

### Configuration

Edit `config.json` or use the in-app settings panel:

```json
{
  "api_key": "your-api-key",
  "base_url": "https://api.deepseek.com",
  "model": "deepseek-v4-pro",
  "temperature": 0.7,
  "max_tokens": 393215
}
```

### Launch

```bash
python main.py
# Or double-click 启动.bat (Windows)
```

Open **http://127.0.0.1:8000** in your browser.

---

## Project Structure

```
Novel_Creation/
├── main.py                    # FastAPI entry point
├── config.json                # LLM configuration (gitignored)
├── requirements.txt           # Python dependencies
├── app/
│   ├── api/                   # REST API + SSE endpoints
│   │   ├── config.py          # LLM config CRUD + connection test
│   │   ├── projects.py        # Project CRUD
│   │   ├── settings.py        # Creation basis CRUD + streaming generate + chat
│   │   ├── outline.py         # Outline CRUD + generation
│   │   ├── chapters.py        # Chapter generation pipeline (SSE) + foreshadowing
│   │   ├── sync.py            # Knowledge sync + lore extraction
│   │   └── utils/             # SSE helper utilities
│   ├── services/
│   │   └── llm.py             # LLMService: OpenAI-compatible client wrapper
│   ├── skills/                # AI skill modules (SYSTEM_PROMPT + run function)
│   │   ├── world_design.py    # World setting
│   │   ├── character_design.py# Character design
│   │   ├── timeline.py        # Timeline
│   │   ├── relationship.py    # Character relationships
│   │   ├── outline.py         # Outline generation (3 levels)
│   │   ├── chapter_write.py   # Chapter writing
│   │   ├── knowledge_sync.py  # Knowledge sync (6-phase pipeline)
│   │   ├── lore_extract.py    # IP extraction (fan-fiction)
│   │   └── writing_assist.py  # Memory search, style management, pre-write checks
│   ├── storage/
│   │   └── file_manager.py    # File manager: all read/write operations
│   └── static/                # Frontend (vanilla JS SPA)
│       ├── index.html
│       ├── css/
│       └── js/
│           ├── utils/         # SSE client, API client, helpers
│           ├── api.js, state.js, app.js
│           └── components/    # UI components (7 panels)
└── projects/                  # Project data (one subdirectory per project)
    └── <project-name>/
        ├── 项目状态.json
        ├── 创作依据/           # World, characters, timeline, relationships, style guide
        ├── 大纲/               # Book → Volume → Chapter outlines
        ├── 正文/               # Written chapters
        └── 伏笔管理/           # Foreshadowing tracking
```

---

## API Endpoints

### Health
```
GET /api/health
```

### Config (`/api/config`)
```
GET  /              Get config (key masked)
PUT  /              Update config
POST /test          Test LLM connection
```

### Projects (`/api/projects`)
```
GET    /            List projects
POST   /            Create project
DELETE /{name}      Delete project
```

### Settings (`/api/settings`)
```
GET  /{project}/all                     Get all settings (for LLM context)
GET  /{project}/world                   Get world setting
GET  /{project}/characters              List characters
POST /{project}/characters/generate     AI generate character
PUT  /{project}/characters/{name}       Save character
GET  /{project}/timeline                Get timeline
GET  /{project}/relationship            Get relationships
POST /stream-generate                   SSE: one-shot streaming generate
POST /chat-generate                     SSE: interactive chat creation
```

### Outline (`/api/outline`)
```
GET  /{project}/book                           Get book outline
POST /{project}/book/generate                  Generate book outline
GET  /{project}/volume/{vol}                   Get volume outline
POST /{project}/volume/{vol}/generate          Generate volume outline
GET  /{project}/volume/{vol}/chapter/{ch}      Get chapter outline
POST /{project}/volume/{vol}/chapter/{ch}/generate  Generate chapter outline
```

### Chapters (`/api/chapters`)
```
GET  /{project}/volume/{vol}               List chapters
GET  /{project}/volume/{vol}/chapter/{ch}  Get chapter content
POST /generate                             SSE: full chapter writing pipeline
POST /feedback                             SSE: outline confirmation / revision
POST /query                                Memory search
GET  /{project}/foreshadowing              Get foreshadowing list
```

### Sync (`/api/sync`)
```
POST /{project}/trigger        Manual knowledge sync
POST /{project}/lore-extract   Extract worldbuilding from known IP
```

---

## Core Architecture

### Knowledge Sync (6-Phase Pipeline)

The core innovation. After each chapter is written, the knowledge sync engine automatically:

```
Phase 1: Text Analysis  →  Pure-text creative element analysis
Phase 2a: Character Extraction  →  New characters + character updates
Phase 2b: Event Extraction  →  New timeline events
Phase 2c: World Extraction  →  New locations + world info
Phase 2d: Relationship Extraction  →  Relationship changes
Phase 2e: Foreshadowing Extraction  →  New + recovered foreshadowing
Phase 3: Step-by-step updates  →  Apply changes to each setting file
Phase 4: Update Report  →  Generate human-readable summary
```

### SSE Streaming Format

All SSE endpoints use a consistent message format:

```
data: {"type":"status","message":"..."}
data: {"type":"text_chunk","text":"..."}
data: {"type":"complete","phase":"...","history":[...]}
data: {"type":"error","message":"..."}
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| LLM call fails | Check `config.json` API key and base URL; use the "Test Connection" button in UI |
| SSE connection hangs | Verify LLM responds normally via `/api/config/test`; check server logs |
| Port 8000 occupied | `netstat -ano \| findstr 8000` then `taskkill /PID <PID> /F` |

---

## Links

- [Changelog](CHANGELOG.md)
- [Roadmap](ROADMAP.md)
- [Design Specification](docs/design-spec.md)

---

## License

MIT
