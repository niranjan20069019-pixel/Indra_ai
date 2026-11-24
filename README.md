# INDRA AI

Local-first personal AI assistant. Runs on your laptop with optional cloud LLM support.

## Architecture

```
User (Voice/Text)
    → Input Processor
    → AI Agent Orchestrator
        → Intent Detection
        → Context Management
        → Memory Retrieval
        → Planning
        → Tool Selection & Execution
    → Response Generator (Text/Voice)
```

## Features

- **16 tools** across filesystem, terminal, projects, tasks, memory, web search
- **LLM abstraction** — Ollama, OpenAI, Anthropic via provider pattern
- **Agent orchestrator** — tool calling, multi-step reasoning, context management
- **Project & task management** — CRUD with deadlines, priorities, tags
- **Memory system** — save, search, delete long-term memories
- **Web search** — DuckDuckGo integration
- **Security** — permission levels, command denylists, workspace restrictions
- **30-minute check-ins** — configurable proactive scheduler
- **REST API** — FastAPI with async SQLite

## Requirements

- Python 3.12+
- Ollama (for local LLM) or OpenAI/Anthropic API key
- Node.js (for frontend, optional)

## Setup

```bash
# Clone and enter
cd indra-ai

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your settings

# Run backend
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8420 --reload
```

## Ollama Setup

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model (recommended for your hardware)
ollama pull qwen2.5:1.5b

# Start Ollama
ollama serve
```

## Configuration

Key `.env` settings:

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5:1.5b
VOICE_ENABLED=false
CHECKIN_ENABLED=true
CHECKIN_INTERVAL_MINUTES=30
APPROVED_WORKSPACES=/home/youruser/projects
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send message to AI agent |
| GET | `/api/status` | System status |
| GET | `/api/tools` | List available tools |
| GET | `/api/projects/` | List projects |
| POST | `/api/projects/` | Create project |
| PUT | `/api/projects/{id}` | Update project |
| DELETE | `/api/projects/{id}` | Delete project |
| GET | `/api/tasks/` | List tasks |
| POST | `/api/tasks/` | Create task |
| POST | `/api/tasks/{id}/complete` | Complete task |
| DELETE | `/api/tasks/{id}` | Delete task |
| GET | `/api/voice/status` | Voice system status |

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `list_files` | read_only | List directory contents |
| `read_file` | read_only | Read file contents |
| `write_file` | moderate | Write/create files |
| `create_directory` | low | Create directories |
| `run_command` | high | Execute shell commands |
| `web_search` | read_only | Search the internet |
| `list_projects` | read_only | List all projects |
| `create_project` | low | Create a project |
| `update_project` | low | Update project fields |
| `list_tasks` | read_only | List tasks |
| `create_task` | low | Create a task |
| `complete_task` | low | Mark task done |
| `delete_task` | high | Delete a task |
| `save_memory` | low | Save to memory |
| `search_memory` | read_only | Search memory |
| `delete_memory` | moderate | Delete a memory |

## Testing

```bash
cd backend
python -m pytest tests/ -v
```

## Security

- Shell command denylist blocks dangerous commands
- High-risk commands require confirmation
- File operations restricted to approved workspaces
- No API keys in code — all via environment variables
- Permission levels: read_only → low → moderate → high → critical

## Roadmap

- [x] LLM provider abstraction (Ollama, OpenAI, Anthropic)
- [x] Agent orchestrator with tool calling
- [x] 16 tools (filesystem, terminal, projects, tasks, memory, web search)
- [x] Permission system with risk levels
- [x] 30-minute check-in scheduler
- [ ] Voice input (faster-whisper)
- [ ] Voice output (Piper TTS)
- [ ] Wake word detection
- [ ] Web UI dashboard
- [ ] Document processing (PDF, DOCX)
- [ ] Browser automation (Playwright)
- [ ] Email assistant
- [ ] Coding agent
- [ ] Vector memory (ChromaDB)
- [ ] Focus mode
- [ ] Daily productivity summaries
