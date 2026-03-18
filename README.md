# labJ - Voice-Powered Lab Journal

A JARVIS-like AI assistant for hands-free lab journaling with voice commands, designed for researchers who need to document experiments while working.

## 🎯 Overview

**labJ** is an intelligent lab journal that enables:
- **Voice-first interaction**: Transcribe notes, create sessions, and control the interface entirely by voice
- **Smart organization**: Automatic session management with timestamps and searchable history
- **Draggable sub-windows**: Create sticky notes and calculators on-the-fly with voice triggers
- **Real-time transcription**: Powered by Groq's Whisper Large v3 Turbo
- **Future-ready**: Architecture designed for LLM-powered intent recognition, data visualization, and intelligent querying

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- uv (Python package manager)

### Installation

```bash
# Install Python dependencies
uv sync

# Install frontend dependencies
cd ui && npm install

# Run orchestration backend
uv run uvicorn orchestration_api.app:app --reload --host 0.0.0.0 --port 8000

# Optional: enable LLM parsing (with deterministic fallback)
export LLM_API_KEY=...

# Run frontend (separate terminal)
cd ui && npm run dev
```

### Current Runnable Components

```bash
# STT docker service
cd stt/STT-module
docker compose up --build -d

# Module-level validation (from repo root)
uv run pytest context_action_plan/tests plan_validation/tests executor_runtime/tests mock_runtime_contract/tests db/tests tools/tests orchestration_api/tests -q
```

The previous unified backend entrypoint (`agents/controller.py`) has been archived.
See `archive/legacy/README.md` for legacy details and restore instructions.
Current unified backend entrypoint is `orchestration_api.app:app`.
Orchestration API docs/examples: `orchestration_api/README.md`.

### Voice Commands

| Trigger | Action |
|---------|--------|
| `"pause"` / `"mute"` | Pause transcription (triggers still work) |
| `"resume"` / `"unmute"` | Resume transcription |
| `"create note"` / `"sticky note"` | Open a draggable note window |
| `"calculator"` / `"calc"` | Open a calculator window |
| `"new session"` | Start a new journal session |
| `"stop listening"` | Shut down the assistant |

## 🏗️ Architecture

Architecture, runtime flow, and repository structure are documented in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## 🧪 Testing

```bash
# Focused module suites
uv run pytest context_action_plan/tests -q
uv run pytest plan_validation/tests -q
uv run pytest executor_runtime/tests -q
uv run pytest mock_runtime_contract/tests -q
uv run pytest db/tests tools/tests -q
uv run pytest orchestration_api/tests -q

# Or all active suites at once
uv run pytest context_action_plan/tests plan_validation/tests executor_runtime/tests mock_runtime_contract/tests db/tests tools/tests orchestration_api/tests -q
```

## 🔮 Roadmap

### Current Features
- [x] Real-time voice transcription (Groq Whisper)
- [x] Voice trigger system (keyword-based)
- [x] Session management
- [x] Draggable sub-windows (notes, calculators)
- [x] SQLite persistence
- [x] Rich text editing with Tiptap

### Planned
- [ ] Replace trigger keywords with LLM intent recognition
- [ ] Data visualization (charts, graphs, tables)
- [ ] Query historical sessions with natural language
- [ ] Dataset integration and analysis
- [ ] Export to LaTeX/PDF
- [ ] Multi-modal input (images, equations)

## 🛠️ Development

### Key Technologies
- **Core Modules**: FastAPI (STT service), SQLAlchemy, pydantic
- **Frontend**: React 18, TypeScript, Vite, Tiptap
- **Testing**: pytest, unittest.mock
- **Linting**: ruff, mypy, eslint

## 📝 License

MIT

## 🤝 Contributing

This is an experimental research tool. Feel free to fork and adapt for your needs.
