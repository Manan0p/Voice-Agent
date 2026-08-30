# Personal AI Call Agent

A self-hosted, privacy-first personal AI phone agent that answers incoming calls, speaks naturally in English, Hindi, and Hinglish, detects urgency/spam, executes actions with explicit permission policies, and seamlessly hands off to the human user when requested.

## Architecture

```text
Incoming Call ──> Asterisk (PJSIP) ──> WebSocket Media ──> Pipecat Pipeline
                                                               │
     ┌─────────────────┬─────────────────┬─────────────────────┤
     ▼                 ▼                 ▼                     ▼
Silero VAD       faster-whisper    Language Tracker      Decision Engine
(Voice Detect)   (STT Inference)   (Hindi/Eng/Hinglish)  (State & Routing)
                                                               │
                                                               ▼
                                                       Qwen LLM / Tools
                                                               │
                                                               ▼
                                                       Kokoro TTS Engine
                                                               │
                                                               ▼
Caller Audio <──────────────── WebSocket Media <───────────────┘
```

## Directory Structure

- `apps/`: Application entrypoints
  - `agent/`: Voice & text AI runtime and state machines
  - `api/`: FastAPI server for call events, state, and dashboard communication
  - `dashboard/`: Next.js frontend UI
- `packages/`: Reusable packages
  - `shared/`: Config, logging, common utilities
  - `schemas/`: Pydantic data schemas
- `infrastructure/`: Infrastructure configurations (Docker, PostgreSQL, Asterisk)
- `knowledge/`: RAG markdown documents
- `tests/`: Automated unit, integration, and voice/Hinglish evaluation suites
- `docs/`: Technical and operational documentation

## Quick Start (Local Development)

### 1. Prerequisites
- Python 3.12+
- `uv` package manager: `powershell -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"`

### 2. Environment Setup & Dependency Installation
```powershell
# Create venv and install dependencies
uv venv --python 3.12
uv pip install -e ".[dev]"
```

### 3. Run Linting & Tests
```powershell
# Lint check & format
uv run ruff check .
uv run ruff format --check .

# Run unit tests
uv run pytest tests/unit -v
```

### 4. Start the API Server
```powershell
uv run uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload
```
Check health: `http://127.0.0.1:8000/health`
