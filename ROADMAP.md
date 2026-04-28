# Roadmap

## Completed

### v0.1.2 — Streaming Fix & Chapter Management (2026-04-28)

- **Critical Fix**: DeepSeek V4 reasoning phase blocked streaming output — `_chat_stream()` now yields reasoning chunks
- **Critical Fix**: Knowledge sync stuck at event extraction — `max_tokens` raised to 8192, timeline context trimmed, 120s timeout
- Chapter outline streaming generation
- Knowledge sync streaming progress (SSE status events)
- Chapter management system (`chapter-manager.js`)
- Double input box bug fix
- Reasoning content filtered from user-facing output

### v0.1.1 — Knowledge Sync Engine Fix (2026-04-27)

- **Architecture**: Single LLM call → 6-phase pipeline (text analysis + 5 domain extractions)
- JSON parser: 4-strategy fallback (`---JSON---` / code blocks / balanced braces)
- Timeline split tolerance: multiple heading variant fallbacks
- Sync failure visible in frontend via SSE error events
- Per-phase debug files for troubleshooting

### v0.1.0 — Security & Stability (2026-04-27)

- Path traversal vulnerability fix in `file_manager.py`
- HTTP status codes normalized across 6 API files
- Foreshadowing ID collision fix
- LLM retry with exponential backoff (RateLimit/Timeout/Connection/500)
- SSE client disconnect detection
- Dead code removal (328+141 lines)
- Duplicate code consolidation (SSE helpers, `escapeHtml`)
- Removed unused `aiofiles` dependency

### v0.0.1 — Initial Release (2026-04-27)

- Project management (create/delete/list)
- Creation basis management (world, characters, timeline, relationships, style)
- Three-level outline generation
- SSE streaming chapter writing with interactive feedback
- Knowledge sync engine (basic)
- Foreshadowing management
- Chat-based setting creation
- Fan-fiction lore extraction

---

## Next (v0.2.0) — Quality & Completeness

### Security
- [ ] API Key environment variable support (`NOVEL_LLM_API_KEY`)
- [ ] Atomic file writes (temp file + rename)
- [ ] Error message sanitization (don't leak stack traces)

### Bug Fixes
- [ ] N+1 query optimization in outline tree loading
- [ ] Character name extraction robustness
- [ ] Character heading recognition (h1/h2)
- [ ] Context-aware truncation (paragraph boundaries)

### Architecture
- [ ] Project-level concurrency safety (`asyncio.Lock`)
- [ ] Token counting & context window budget management

### Quality
- [ ] Basic test coverage (pytest + httpx)
- [ ] Structured logging (replace `print`)
- [ ] SSE auto-reconnect with exponential backoff

### Features
- [ ] Project export/import (zip archive)
- [ ] Project rename

---

## Future (v0.3.0+)

### Enhanced Experience
- [ ] Version snapshots (restore previous setting versions)
- [ ] Conflict detection (new content vs. existing settings)
- [ ] Knowledge graph visualization (relationship graph, timeline view)
- [ ] Dark mode
- [ ] Monaco Editor integration for Markdown editing
- [ ] Keyboard shortcuts

### Advanced Features
- [ ] Multi-model configuration (cheap model for outlines, strong model for chapters)
- [ ] RAG knowledge base for fan-fiction (upload source material documents)
- [ ] Batch chapter generation
- [ ] Revision mode (partial chapter edits)
- [ ] Mobile responsive layout

---

*Last updated: 2026-04-28*
