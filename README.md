# 🎙️ Personal AI Voice & Call Agent

A self-hosted, privacy-first personal AI phone agent that answers incoming phone calls, speaks naturally in English, Hindi, and Hinglish with sub-second latency, intelligently detects urgency, caller relationships, and scam threats, executes actions with explicit permission tiers, and provides seamless RAG memory and telephony streaming.

---

## 🏛️ System Architecture

```text
Incoming Call ────────► Twilio Media Streams / Microphone
                               │
                               ▼
                    Pipecat Real-Time Pipeline
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
   Silero VAD            Faster-Whisper        Language Tracker
 (Voice Activity)       (STT Inference)      (Hindi/Eng/Hinglish)
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               ▼
                        Decision Engine
                (Caller ID, Intent, Urgency, Risk)
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
       AgentEngine (LLM)             Tool Registry & RAG
       (Gemini / Qwen)               (pgvector Knowledge)
                │                             │
                └──────────────┬──────────────┘
                               ▼
                       Kokoro-82M TTS
                  (24kHz Phonetic Voice)
                               │
                               ▼
                    Outbound Telephony Audio
                (Instant Barge-In Clear on Talk)
```

---

## 🚀 Key Capabilities

1. **Natural Real-Time Voice Loop**:
   - Sub-second round-trip voice latency using **Pipecat**, **Silero VAD**, **Faster-Whisper**, and **Kokoro-82M**.
   - Zero acoustic echo feedback suppression and instant barge-in playback clearing.
2. **Indian Hinglish Language Engine**:
   - Smooth Romanized Hinglish vocabulary detection and phonetic pronunciation smoothing.
   - Dynamic language policy mirroring (`MIRROR`, `FORCE_ENGLISH`, `FORCE_HINDI`, `FORCE_HINGLISH`).
3. **Multi-Agent Decision & Security Engine**:
   - Real-time classification across 8 intent categories and 4 urgency levels.
   - Active protection against extortion, phishing, and fake arrest warrant scams.
4. **PostgreSQL + pgvector Long-Term Memory**:
   - Dense vector embeddings for personal knowledge bases and calendar availability.
   - Caller relationship histories, voicemails, and full call transcript retention.
5. **FastAPI REST API**:
   - Endpoints for call histories, voicemails, contacts, knowledge base ingestion, reminders, and system health.
6. **Telephony Integration**:
   - Bidirectional Twilio Media Streams WebSocket protocol with G.711 μ-law <-> Linear PCM transcoding and TwiML webhooks.
7. **Comprehensive Benchmark Suite**:
   - 50-call evaluation benchmark covering recruiters, deliveries, emergencies, scams, and friends with 100% accuracy.

---

## 📁 Repository Structure

```text
├── apps/
│   ├── agent/                 # Core AI agent engine, STT, TTS, language, decision, tools, telephony
│   │   ├── decision/          # Intent, urgency, risk classifiers, and caller resolver
│   │   ├── language/          # Hindi/Hinglish detection, lexicon, and tracker
│   │   ├── llm/               # Gemini and local LLM providers
│   │   ├── stt/               # Faster-Whisper local transcription
│   │   ├── tts/               # Kokoro-82M TTS engine and phonetic smoothing
│   │   ├── telephony/         # Twilio Media Streams bridge and codecs
│   │   ├── tools/             # Builtin tool registry and permission policies
│   │   └── voice/             # Real-time Pipecat pipeline runner
│   └── api/                   # FastAPI REST API server and routes
│       └── routes/            # /api/calls, /api/messages, /api/contacts, /api/knowledge, /api/reminders, /api/status, /api/telephony
├── packages/
│   ├── db/                    # SQLAlchemy async models, repositories, and pgvector session
│   ├── schemas/               # Pydantic request/response validation schemas
│   └── shared/                # Environment configuration and structured logging
├── infrastructure/
│   ├── docker/                # Multi-stage Dockerfiles for API and Agent
│   └── postgres/              # PostgreSQL 16 pgvector initialization
├── tests/
│   ├── evals/                 # E2E 50-call evaluation, Hinglish, and voice pipeline benchmarks
│   ├── fixtures/              # Dataset fixtures for decision and E2E calls
│   ├── integration/           # API server, memory RAG, and telephony streaming tests
│   └── unit/                  # Comprehensive unit tests for all subsystems
├── docker-compose.yml         # Full-stack container orchestration
├── eval_report.json           # 50-call benchmark results report
├── pyproject.toml             # Project dependencies and packaging configuration
├── voice_agent.py             # Live interactive CLI voice pipeline entrypoint
└── README.md                  # Operational documentation
```

---

## 🛠️ Quick Start (Local Development)

### 1. Prerequisites
- Python 3.12+
- `uv` package manager:
  ```powershell
  powershell -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
  ```

### 2. Environment Setup
```powershell
# Clone and enter directory
cd "Voice Agent"

# Install virtual environment with all dependencies
uv sync --all-extras

# Copy environment variables
copy .env.example .env
```

Configure your `.env` file with your Gemini API key:
```ini
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-flash-lite-latest
```

---

## 🎙️ Running the Live Voice Agent

To start the interactive real-time voice pipeline with your microphone and speakers:
```powershell
python voice_agent.py
```
Speak into your microphone in English, Hindi, or Hinglish. Press `Ctrl+C` to exit.

---

## 🌐 Running the FastAPI REST API Server

Start the REST API server locally:
```powershell
uv run uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Interactive API Docs (Swagger)**: `http://localhost:8000/docs`
- **System Health Probe**: `http://localhost:8000/health`
- **Telemetry & Status**: `http://localhost:8000/api/status`

### Key REST Endpoints:
- `GET /api/calls`: List call records with pagination and filters (`phone_number`, `status`, `intent`, `urgency`).
- `GET /api/messages`: List caller voicemails and messages.
- `GET /api/contacts`: Search and manage caller contact profiles.
- `POST /api/knowledge/search`: Hybrid semantic and keyword search across stored knowledge chunks.
- `POST /api/telephony/twilio/incoming`: Twilio inbound voice webhook returning TwiML stream instructions.
- `WebSocket /api/telephony/twilio/stream`: Bidirectional audio streaming WebSocket.

---

## 📊 Running the 50-Call E2E Evaluation Benchmark

Run the full end-to-end evaluation benchmark across 50 simulated calls:
```powershell
python -m tests.evals.test_e2e_evaluation
```
This generates [`eval_report.json`](file:///c:/Users/Manan/Desktop/Voice%20Agent/eval_report.json) with accuracy metrics, per-category statistics, and P95 latency measurements.

---

## 🧪 Automated Testing & Linters

Run the comprehensive test suite (228 tests):
```powershell
# Run all tests
python -m pytest tests/ -v

# Run linters and formatting checks
python -m ruff check .
python -m ruff format --check .
```

---

## 🐳 Production Deployment with Docker Compose

Deploy the full stack with PostgreSQL 16 + `pgvector` and FastAPI:
```bash
docker compose up -d --build
```
Check running containers:
```bash
docker compose ps
```
View application logs:
```bash
docker compose logs -f api
```

---

## 🔒 Security & Privacy Policy
- **Local-First Processing**: STT (faster-whisper) and TTS (Kokoro-82M) run locally on CPU/GPU without sending audio to third-party services.
- **Sensitive Credential Shield**: The risk classifier actively detects and blocks OTP requests and credential phishing attempts.
- **Explicit Permission Tiers**: Tool invocations are gated by strict permission rules with structured audit logs.
