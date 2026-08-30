# Architecture Overview

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

## System Components
1. **Agent Engine (`apps/agent`)**: State machine, intent/urgency/risk classification, language policies, and tools.
2. **API Backend (`apps/api`)**: FastAPI service for call lifecycle events, database persistence, and dashboard communication.
3. **Packages (`packages/`)**: Reusable schemas and shared config/logging modules.
4. **Dashboard (`apps/dashboard`)**: Next.js realtime call dashboard with human intervention.
