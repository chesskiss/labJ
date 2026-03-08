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

# Run backend
uv run python -m agents.controller

# Run frontend (separate terminal)
cd ui && npm run dev
```

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

!TODO - 
UI:
test anything that drags
search all potential keyword
Use a pre-filled notebook (template) that's contain edge cases. Copy the template and test on the copy. Then delete it at the end of the test.

Comprehensive state machine tests validate all trigger combinations and edge cases:

```bash
# Run all tests
uv run pytest tests/test_trigger_state_machine.py -v

# Run with coverage
uv run pytest tests/ --cov=stt --cov=agents --cov-report=term-missing
```

**Test Coverage:**
- ✅ 10 test scenarios (basic → complex)
- ✅ All trigger keyword variations
- ✅ State transitions (pause/resume/stop)
- ✅ Sub-window creation and management
- ✅ Edge cases (double pause, resume without pause, etc.)

See [tests/README.md](tests/README.md) for detailed test documentation.

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
- **Backend**: FastAPI, SQLAlchemy, sounddevice, Groq API
- **Frontend**: React 18, TypeScript, Vite, Tiptap
- **Testing**: pytest, unittest.mock
- **Linting**: ruff, mypy, eslint

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/sessions` | List all journal sessions |
| GET | `/notebook` | Get full notebook content |
| POST | `/commands` | Execute text command |
| GET | `/subwindows` | List active sub-windows |
| POST | `/subwindows/{id}` | Update sub-window |
| DELETE | `/subwindows/{id}` | Close sub-window |

### Database Schema

**sessions**: `id`, `title`, `start_time`, `end_time`
**utterances**: `id`, `session_id`, `text`, `start_time`, `end_time`, `source`

## 📝 License

MIT

## 🤝 Contributing

This is an experimental research tool. Feel free to fork and adapt for your needs.
