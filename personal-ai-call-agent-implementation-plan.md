# Personal AI Call Agent — Full Implementation Plan

## Project Objective

Build a self-hosted/open-source personal AI phone agent that acts as the first-line handler for essentially every incoming call.

The agent should:

- Answer incoming calls automatically.
- Speak naturally with callers.
- Handle known contacts and unknown numbers.
- Identify callers when possible.
- Determine caller intent.
- Detect urgency.
- Detect likely spam/scams.
- Decide whether to:
  - handle the call itself,
  - collect a message,
  - notify the user,
  - interrupt/forward the call to the user,
  - or terminate the call.
- Understand Hindi, English, and Hinglish.
- Dynamically adapt its response language to the caller's dominant language.
- Remember callers and previous interactions.
- Maintain call transcripts and summaries.
- Allow the user to review calls and correct classifications.
- Eventually perform actions such as scheduling/reminders.
- Provide a web dashboard.
- Eventually be reliable enough for real personal use.

The project should prioritize open-source/local components and avoid paid AI APIs.

---

# NON-NEGOTIABLE DEVELOPMENT RULE: STOP AFTER EVERY PHASE

After completing **each phase**:

1. Stop implementation.
2. Run relevant automated tests.
3. Start the application if applicable.
4. Explain exactly what was implemented.
5. Explain exactly how to manually test it.
6. Give a QA checklist.
7. Report known limitations/issues.
8. **DO NOT start the next phase.**
9. Wait for explicit user approval such as `continue`, `phase passed`, or `move to next phase`.

Do not assume approval from silence.

Even if the next phase seems obvious, stop.

The project must be developed incrementally so the user can manually QA every layer before additional complexity is introduced.

---

# Core Architecture

```text
                         PHONE
                           │
                    PSTN / SIP / Forwarding
                           │
                           ▼
                       ASTERISK
                           │
                    WebSocket media
                           │
                           ▼
                       PIPECAT
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         Silero VAD   faster-whisper   Audio
                           │
                           ▼
                  Language Detection
                           │
                           ▼
                     Agent Engine
                           │
                  ┌────────┼────────┐
                  ▼        ▼        ▼
                 Qwen     Memory    RAG
                  │        │        │
                  └────────┼────────┘
                           │
                        Tools
                           │
                 ┌─────────┼─────────┐
                 ▼         ▼         ▼
             Contacts   Calendar   Actions
                           │
                           ▼
                    Decision Engine
                           │
                ┌──────────┼──────────┐
                ▼          ▼          ▼
              Handle     Notify     Forward
                │          │          │
                └──────────┼──────────┘
                           ▼
                         Kokoro
                           │
                           ▼
                       Pipecat
                           │
                           ▼
                        Asterisk
                           │
                           ▼
                         PHONE
```

Dashboard/data path:

```text
                         CALL EVENTS
                              │
                              ▼
                         FastAPI
                              │
                              ▼
                         PostgreSQL
                              │
                              ▼
                          Next.js
                              │
                              ▼
                       USER DASHBOARD
```

---

# Technology Stack

## Backend

- Python 3.12+
- FastAPI
- Pydantic
- SQLAlchemy 2.x
- PostgreSQL
- Alembic
- `uv`

## Voice Pipeline

- Pipecat
- Silero VAD
- faster-whisper
- Qwen3
- llama.cpp and/or Ollama
- Kokoro
- Piper as fallback

## Telephony

- Asterisk
- PJSIP
- ARI
- Asterisk WebSocket media / `chan_websocket` where appropriate

## Retrieval / Memory

- PostgreSQL
- pgvector
- Local embedding model

## Frontend

- Next.js
- TypeScript
- App Router
- Tailwind CSS
- shadcn/ui

## Development

- Docker
- pytest
- Ruff
- pre-commit
- structured logging

## Notifications

- Telegram initially, behind an abstraction

---

# Official / Existing Resources

Antigravity MUST inspect official documentation, repositories, and examples before implementing a subsystem.

## Pipecat

- https://github.com/pipecat-ai/pipecat
- https://github.com/pipecat-ai/pipecat-examples

Use Pipecat's existing realtime voice abstractions wherever possible. Do not recreate its streaming pipeline.

## Asterisk

- https://docs.asterisk.org/
- https://docs.asterisk.org/Configuration/Interfaces/Asterisk-REST-Interface-ARI/
- https://docs.asterisk.org/Configuration/Channel-Drivers/WebSocket/

Use ARI and WebSocket media functionality rather than implementing unnecessary low-level telephony infrastructure.

## faster-whisper

- https://github.com/SYSTRAN/faster-whisper

Use the existing inference implementation.

Benchmark appropriate model sizes rather than blindly choosing the largest model.

## Qwen3

- https://github.com/QwenLM/Qwen3

Use a local Qwen3 model. Benchmark suitable quantized model sizes.

Qwen documentation/repository includes local execution options such as llama.cpp and Ollama.

## Silero VAD

- https://github.com/snakers4/silero-vad

Use it for speech detection, turn boundaries, silence handling, and interruption detection.

## Piper

- https://github.com/OHF-Voice/piper1-gpl

Use as a TTS fallback if useful. Prefer the maintained successor rather than blindly using an archived/old repository.

## pgvector

- https://github.com/pgvector/pgvector

Use pgvector for vector search inside PostgreSQL instead of adding a separate vector database unless benchmarking proves it necessary.

## Next.js

- https://nextjs.org/docs
- https://nextjs.org/docs/app

Use the App Router.

---

# Reuse Philosophy

Before implementing any subsystem:

1. Search the official documentation.
2. Search the official GitHub repository.
3. Search its examples.
4. Search for maintained integrations.
5. Prefer using existing libraries/frameworks.
6. Reuse existing components/adapters/utilities where appropriate.
7. Do not copy large code sections blindly.
8. Understand the interface and adapt it to this project.
9. Only implement functionality ourselves when:
   - no suitable library exists,
   - the library does not support the requirement,
   - or custom business logic is required.

Do NOT reinvent:

- audio streaming
- WebSocket handling
- VAD
- Whisper inference
- TTS inference
- vector search
- PostgreSQL drivers
- UI primitives
- telephony media handling
- realtime transport

Custom engineering effort should primarily go into:

- caller identification
- Hinglish language policy
- intent classification
- urgency detection
- risk detection
- decision engine
- caller memory
- tool permissions
- human handoff
- personal call policies
- evaluation
- reliability

---

# Agent Architecture

Do NOT start with LangGraph.

Do NOT start with n8n.

Do NOT start with MCP.

Do NOT start with multiple agents.

Start with a clean Python architecture:

```text
Agent
│
├── ConversationManager
├── ContextManager
├── CallerResolver
├── LanguageManager
├── IntentClassifier
├── UrgencyClassifier
├── RiskClassifier
├── DecisionEngine
├── ToolRegistry
├── MemoryManager
├── KnowledgeManager
└── EscalationManager
```

Every component should have a clear interface.

---

# Call State Machine

Do not allow the LLM to independently control the complete call lifecycle.

Use deterministic call states:

```text
INCOMING
   ↓
ANSWERING
   ↓
IDENTIFYING
   ↓
CONVERSING
   ↓
CLASSIFYING
   ↓
DECIDING
   ├── HANDLE
   ├── COLLECT_MESSAGE
   ├── NOTIFY
   ├── INTERRUPT_USER
   ├── TRANSFER
   └── END
```

The LLM provides information and proposed decisions; deterministic application logic enforces the final action.

---

# Caller Identification

Implement:

```text
CallerResolver
```

Resolution order:

1. Exact phone-number match.
2. Previous-call match.
3. Contact database match.
4. Caller-provided identity.
5. Conversation-based identity inference.
6. Unknown caller.

Store confidence and source.

Example:

```json
{
  "identity": "Rahul",
  "source": "previous_interaction",
  "confidence": 0.93
}
```

Never treat low-confidence identification as fact.

---

# Contact Policy

Every call should go through the AI by default.

Contacts do NOT automatically bypass the agent.

Default:

```text
EVERY CALL → AI ANSWERS
```

This includes:

- family
- friends
- colleagues
- saved contacts
- unknown numbers

Caller identity affects classification, not automatic forwarding.

---

# Language System

Support:

- English
- Hindi
- Hinglish

Do not perform a single one-time language classification for the entire call.

Maintain rolling language statistics.

Example:

```json
{
  "english_ratio": 0.35,
  "hindi_ratio": 0.65,
  "dominant_language": "hindi",
  "style": "hinglish"
}
```

The system should preserve natural code-switching.

Example:

Caller:

> Bhai kal meeting ko Wednesday pe shift kar sakte hain?

Agent:

> Haan bhai, Wednesday works. Main note kar leta hoon.

The goal is natural linguistic mirroring, not rigid translation.

---

# Language Detection Implementation

Do not immediately build a huge custom classifier.

Initially evaluate:

- Whisper language probabilities
- fastText language identification
- Lingua
- CLD3
- lightweight language-ID models

Benchmark on actual Hindi, English, and Hinglish speech.

The classifier must be evaluated on code-switched Indian speech, not only clean Hindi/English sentences.

---

# Intent Classification

Initial categories:

```text
PERSONAL
WORK
FAMILY
FRIEND
DELIVERY
BANKING
FINANCE
INTERVIEW
RECRUITER
COLLEGE
SALES
MARKETING
SPAM
SCAM
APPOINTMENT
SERVICE
EMERGENCY
UNKNOWN
```

The list must be configurable.

Do not hardcode business logic into prompts.

---

# Urgency

Use an urgency score:

```text
0.0 → definitely not urgent
0.25 → low
0.5 → moderate
0.75 → high
1.0 → critical
```

Do not rely exclusively on a single LLM-generated floating-point value.

Use multiple signals:

- keywords
- caller identity
- historical context
- intent
- sentiment/distress
- explicit urgency
- time sensitivity

Combine them in deterministic application logic.

---

# Decision Engine

This is one of the most important custom components.

Example:

```text
                    CALL
                     │
             caller identified?
               /           \
             yes            no
              │              │
        known profile     unknown
              │              │
              └──────┬───────┘
                     ▼
               detect intent
                     │
              detect urgency
                     │
               detect risk
                     │
                     ▼
              DecisionEngine
```

Possible output:

```json
{
  "action": "INTERRUPT_USER",
  "reason": "High urgency",
  "confidence": 0.94
}
```

Other possible actions:

- HANDLE
- COLLECT_MESSAGE
- NOTIFY
- INTERRUPT_USER
- TRANSFER
- END

---

# Human Intervention

The user must be able to intervene.

Example:

```text
AI_HANDLING
      ↓
USER_JOINING
      ↓
HUMAN_HANDLING
```

Dashboard should eventually provide:

- Take Call
- Keep AI
- End Call

When the user joins:

- AI stops speaking.
- Call is bridged to the user.
- Call state changes to human handling.
- Event is recorded.

---

# Caller Memory

Maintain two types of memory.

## Short-term

Current call:

- conversation history
- current caller
- current task
- current intent
- current language
- current action

## Long-term

Across calls:

- caller identity
- relationship
- previous interactions
- preferences
- important facts
- past actions

Do not blindly store everything the caller says.

Use a memory extraction policy.

---

# RAG

Use a knowledge base such as:

```text
knowledge/
├── personal_info.md
├── frequently_called_contacts.md
├── preferences.md
├── work.md
├── college.md
├── services.md
├── instructions.md
└── faq.md
```

Pipeline:

```text
document
   ↓
chunk
   ↓
embedding
   ↓
pgvector
```

At call time:

```text
caller question
       ↓
embedding
       ↓
pgvector
       ↓
relevant chunks
       ↓
LLM context
```

Use PostgreSQL + pgvector instead of adding a separate vector database initially.

---

# Tool System

Build a tool registry.

Initial tools:

```text
get_contact
get_caller_history
save_message
search_knowledge
notify_user
transfer_call
end_call
```

Later:

```text
get_calendar
create_calendar_event
create_reminder
```

Every tool must have:

- name
- description
- input schema
- output schema
- permission level
- validation
- audit logging

---

# Tool Permissions

Use:

```text
READ_ONLY
LOW_RISK_WRITE
HIGH_RISK_WRITE
USER_CONFIRMATION_REQUIRED
```

Examples:

```text
search knowledge       → READ_ONLY
read calendar          → READ_ONLY
save message           → LOW_RISK_WRITE
create calendar event  → LOW_RISK_WRITE
send important message → USER_CONFIRMATION_REQUIRED
financial action       → NEVER AUTOMATICALLY
OTP/password           → NEVER HANDLE
```

Never request or expose:

- OTPs
- passwords
- authentication codes
- card PINs
- private credentials

---

# Database

Use:

- PostgreSQL
- SQLAlchemy
- Alembic

Initial tables/models:

```text
UserSettings
Contacts
Calls
CallParticipants
CallEvents
Messages
Transcripts
CallSummaries
Classifications
Notifications
AgentActions
KnowledgeDocuments
KnowledgeChunks
CallerProfiles
CallerMemories
```

Use migrations from the beginning of the persistent-data phase.

---

# Transcript

Store:

```text
speaker
timestamp
text
language
confidence
```

Keep the raw transcript separate from the generated summary.

---

# Post-call Pipeline

After hangup:

```text
Call ends
   ↓
Finalize transcript
   ↓
Generate summary
   ↓
Extract action items
   ↓
Update caller memory
   ↓
Update caller profile
   ↓
Run classification audit
   ↓
Store everything
   ↓
Notify user if required
```

---

# Call Summary

Example:

```text
Caller: Rahul
Duration: 03:42
Language: Hinglish

Reason:
Wanted to confirm tomorrow's meetup.

Outcome:
AI handled the conversation.

Action:
Meet Rahul at 8 PM tomorrow.

Urgency:
Low

User notification:
No
```

---

# Notifications

Create:

```text
NotificationProvider
    ├── Telegram
    ├── Email
    └── Future providers
```

Initially Telegram can be implemented.

Do not make Telegram part of the core agent.

The core system must work without notifications.

Notifications should be triggered by application/decision logic, not arbitrary LLM output.

---

# Dashboard

Build only after the underlying call data exists.

Pages:

```text
/
 /calls
 /calls/[id]
 /contacts
 /contacts/[id]
 /knowledge
 /settings
```

## Home

Show:

- today's calls
- important calls
- missed/failed calls
- AI-handled calls
- calls requiring attention

## Call Details

Show:

- caller
- identity
- duration
- language
- intent
- urgency
- risk
- action
- transcript
- summary
- timeline

## Caller

Show:

- name
- number
- relationship
- trust level
- previous calls
- memories
- notes

## Settings

Show:

- AI greeting
- language preferences
- urgency threshold
- spam threshold
- forwarding rules
- notification rules
- privacy
- recording settings

---

# Observability

Every call gets a correlation ID:

```text
call_id
```

Every subsystem logs against it:

```text
ASTERISK
PIPECAT
STT
LANGUAGE
LLM
TOOL
DECISION
TTS
NOTIFICATION
```

Example:

```text
call=abc123
event=stt.completed
latency_ms=421
```

Track:

- STT latency
- LLM time-to-first-token
- LLM completion latency
- TTS first-audio latency
- end-to-end turn latency
- VAD timing
- tool latency
- call duration
- errors

---

# Evaluation System

Build evaluation before trusting the system with real calls.

Create:

```text
tests/evals/
├── english/
├── hindi/
├── hinglish/
├── spam/
├── scam/
├── urgent/
├── contacts/
├── unknown/
└── interruptions/
```

Each scenario should define expected behavior.

Example:

```json
{
  "input": "...",
  "expected_language": "hinglish",
  "expected_intent": "personal",
  "expected_action": "handle",
  "expected_urgency": "low"
}
```

Measure:

- STT WER
- language accuracy
- intent accuracy
- urgency accuracy
- spam accuracy
- caller identification accuracy
- decision accuracy
- tool success rate
- latency
- call completion rate
- handoff success rate

---

# Critical Voice Tests

Test at minimum:

### Normal

```text
Hello, can I speak to Manan?
```

### Hinglish

```text
Bhai Manan free hai kya?
```

### Hindi

```text
मुझे मनन से बात करनी है।
```

### Code switching

```text
Actually bhai mujhe kal ki meeting ke regarding baat karni thi.
```

### Interruption

```text
AI: Manan is currently—
Caller: No no, listen—
```

Also test:

- fast speech
- background noise
- poor network
- multiple speakers
- long pauses
- topic changes
- caller refuses to identify themselves
- scam calls
- telemarketing
- genuine urgent calls

---

# PHASE 0 — PROJECT FOUNDATION

## Goal

Create the repository and development environment.

Suggested structure:

```text
personal-ai-caller/
│
├── apps/
│   ├── agent/
│   ├── api/
│   └── dashboard/
│
├── packages/
│   ├── shared/
│   └── schemas/
│
├── infrastructure/
│   ├── docker/
│   ├── postgres/
│   └── asterisk/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── evals/
│
├── knowledge/
│
├── docs/
│
├── .env.example
├── docker-compose.yml
├── README.md
└── pyproject.toml
```

Use:

- `uv`
- Ruff
- pytest
- pre-commit
- Docker

Implement:

```text
GET /health
```

returning:

```json
{
  "status": "ok"
}
```

### Phase 0 QA

Verify:

- repository structure
- dependency installation
- linting
- tests
- API startup
- health endpoint
- Docker startup

### STOP HERE.

Do not begin Phase 1 until the user explicitly approves.

---

# PHASE 1 — LOCAL TEXT AGENT

Do not use voice yet.

Build:

```text
CLI
 ↓
Qwen
 ↓
response
```

Implement:

- system prompt
- conversation history
- structured output
- tool registry abstraction
- basic error handling

Benchmark appropriate local Qwen3 model sizes.

Goal:

A 10–20 turn local conversation with context retention.

### QA

Test:

- normal conversation
- context retention
- structured output
- latency
- model failure behavior
- prompt adherence

### STOP HERE.

Wait for explicit user approval.

---

# PHASE 2 — LOCAL STT

Add faster-whisper.

```text
audio file
 ↓
faster-whisper
 ↓
transcript
```

Create a simple CLI:

```bash
python transcribe.py sample.wav
```

Test:

- English
- Hindi
- Hinglish
- accents
- noisy audio

Record latency.

Benchmark appropriate model sizes.

### STOP HERE.

Wait for explicit user approval.

---

# PHASE 3 — LOCAL TTS

Add Kokoro.

```text
text
 ↓
Kokoro
 ↓
.wav
```

Then connect:

```text
STT
 ↓
LLM
 ↓
TTS
```

using local/recorded audio rather than telephone audio.

Create a TTS abstraction:

```text
TTSProvider
 ├── KokoroProvider
 └── PiperProvider
```

### QA

Evaluate:

- voice quality
- pronunciation
- latency
- English
- Hindi/Hinglish where supported

### STOP HERE.

Wait for explicit user approval.

---

# PHASE 4 — REALTIME VOICE PIPELINE

Introduce Pipecat.

Target:

```text
Microphone
 ↓
Pipecat
 ↓
VAD
 ↓
faster-whisper
 ↓
Qwen
 ↓
Kokoro
 ↓
Speaker
```

Implement:

- streaming
- VAD
- interruptions
- turn handling
- error recovery

Use existing Pipecat components/examples.

Do not recreate realtime infrastructure already provided by Pipecat.

### QA

Test:

- normal conversation
- short responses
- long responses
- interruption
- silence
- rapid speech
- STT errors
- TTS errors
- model errors

### STOP HERE.

This is a major QA checkpoint.

Do not continue until the voice conversation is reasonably natural.

---

# PHASE 5 — HINGLISH ENGINE

Implement:

```text
LanguageDetector
LanguageTracker
LanguagePolicy
```

Output:

```json
{
  "english_ratio": 0.32,
  "hindi_ratio": 0.68,
  "dominant_language": "hindi",
  "style": "hinglish"
}
```

The LLM should respond according to the language policy.

Create at least 50 Hinglish test conversations.

### STOP HERE.

Wait for explicit approval.

---

# PHASE 6 — AGENT STATE + DECISION ENGINE

Introduce:

```text
CallerResolver
IntentClassifier
UrgencyClassifier
RiskClassifier
DecisionEngine
```

Use simulated conversations first.

Example:

```text
Caller:
Sir I'm calling regarding your interview tomorrow.

Expected:
intent = interview
urgency = high
action = interrupt_user
```

Create automated evaluation cases.

### STOP HERE.

Manually QA every classification category.

---

# PHASE 7 — TOOLS

Implement initial tools:

```text
get_contact
get_caller_history
save_message
search_knowledge
notify_user
transfer_call
end_call
```

Every tool gets:

- Pydantic schema
- permission
- validation
- audit event
- tests

Test invalid arguments and hallucinated tool calls.

### STOP HERE.

Wait for approval.

---

# PHASE 8 — POSTGRESQL + MEMORY

Introduce:

```text
PostgreSQL
SQLAlchemy
Alembic
```

Implement:

```text
contacts
calls
messages
transcripts
caller_profiles
caller_memories
agent_actions
```

Implement persistent caller memory.

### QA

- create calls
- persist transcripts
- restart backend
- verify data remains
- run migrations
- test corrupted/invalid data

### STOP HERE.

Wait for approval.

---

# PHASE 9 — RAG

Add:

```text
pgvector
local embedding model
document ingestion
chunking
retrieval
```

Do not introduce a separate vector database unless necessary.

Test:

- correct retrieval
- irrelevant retrieval
- no-answer case
- hallucination prevention

### STOP HERE.

Wait for approval.

---

# PHASE 10 — CALL SIMULATOR

Build a simulated caller environment.

```text
simulated caller
       ↓
audio
       ↓
Pipecat
       ↓
agent
```

Create realistic scenarios.

Run at least 30–50 simulated calls.

### STOP HERE.

Review results before telephony integration.

---

# PHASE 11 — ASTERISK

Introduce Asterisk.

First:

```text
SIP softphone
      ↓
Asterisk
      ↓
basic answer
```

No AI initially.

Verify:

- SIP registration
- incoming call
- answering
- hangup
- caller ID
- audio

Then connect ARI.

### STOP HERE.

Manual SIP/telephony QA.

---

# PHASE 12 — ASTERISK ↔ PIPECAT

Connect:

```text
Asterisk
 ↓
WebSocket media
 ↓
Pipecat
```

Target:

```text
SIP caller
 ↓
Asterisk
 ↓
Pipecat
 ↓
Whisper
 ↓
Qwen
 ↓
Kokoro
 ↓
Asterisk
 ↓
caller
```

Use Asterisk's WebSocket media functionality where appropriate instead of implementing raw RTP handling unnecessarily.

### STOP HERE.

This is a major integration checkpoint.

Perform extensive manual phone/SIP QA.

---

# PHASE 13 — REAL PHONE NUMBER

Integrate the secondary phone number and call forwarding.

First determine exactly how the mobile carrier's forwarding works.

Do not assume call forwarding automatically provides SIP access.

Test:

- call forwarding
- caller ID preservation
- answering
- hangup
- audio quality
- latency

Test calls from:

- user's number
- family member
- friend
- unknown number
- spam/marketing call if available

### STOP HERE.

Wait for explicit approval.

---

# PHASE 14 — HUMAN HANDOFF

Implement:

```text
AI
 ↓
decision
 ↓
interrupt user
 ↓
user joins call
```

Test:

```text
AI speaking
 ↓
user presses TAKE CALL
 ↓
AI stops
 ↓
user joins
```

Also test failure cases.

### STOP HERE.

Do not continue until manual handoff works reliably.

---

# PHASE 15 — DASHBOARD

Build Next.js dashboard.

Pages:

```text
/
 /calls
 /calls/[id]
 /contacts
 /contacts/[id]
 /knowledge
 /settings
```

Implement call list, call details, transcripts, summaries, caller profiles, settings, and human-intervention controls.

### STOP HERE.

Manual UI QA.

---

# PHASE 16 — CALL MEMORY + LEARNING LOOP

Implement:

```text
call
 ↓
summary
 ↓
memory extraction
 ↓
caller profile
 ↓
future call
 ↓
retrieval
```

Add:

- Correct classification
- Mark important
- Mark spam
- Mark trusted
- Forget memory

The user should be able to correct the AI.

### STOP HERE.

Review memory accuracy manually.

---

# PHASE 17 — NOTIFICATIONS

Add Telegram behind the notification abstraction.

Example:

```text
HIGH_URGENCY
      ↓
notification service
      ↓
Telegram
```

Test:

- important calls
- routine calls
- spam
- failures
- duplicate notifications

### STOP HERE.

Wait for approval.

---

# PHASE 18 — RELIABILITY

Implement:

- retries
- timeouts
- circuit breakers
- model-unavailable fallback
- TTS failure fallback
- STT failure fallback
- database failure handling
- network failure handling
- call timeout
- graceful shutdown
- health checks
- structured logging
- call correlation IDs

Example fallback:

```text
Qwen unavailable
     ↓
Sorry, I'm having trouble right now.
Please call back shortly.
```

Never leave the caller in silence indefinitely.

### STOP HERE.

Run fault-injection tests.

---

# PHASE 19 — SECURITY

Audit:

- secrets
- authentication
- API authorization
- database access
- transcript access
- caller data
- logs
- recordings
- dashboard access
- tool permissions

Never log:

- passwords
- OTPs
- authentication tokens
- private credentials

### STOP HERE.

Perform security QA.

---

# PHASE 20 — EVALUATION HARNESS

Create a proper evaluation framework.

Target at least:

```text
100 simulated calls
```

Measure:

- STT WER
- language accuracy
- intent accuracy
- urgency accuracy
- spam accuracy
- caller identification accuracy
- decision accuracy
- tool success rate
- latency
- call completion rate
- handoff success rate

### STOP HERE.

Review metrics and fix major failures before production.

---

# PHASE 21 — REAL-WORLD SHADOW MODE

Before fully trusting the system:

```text
Incoming call
      ↓
AI handles
      ↓
USER OBSERVES
      ↓
AI decision logged
```

Use conservative behavior.

For uncertain cases:

```text
uncertain → notify user
```

rather than:

```text
uncertain → reject
```

Run the system for several days and review every call.

### STOP HERE.

Do not move to automatic production behavior until the user explicitly approves.

---

# PHASE 22 — PERSONAL PRODUCTION

Allow routine calls to be handled automatically.

Example policy:

```text
critical/uncertain → user
high-risk → user
known spam → AI handles
routine → AI handles
```

The user must always be able to override.

### STOP HERE.

Review real-world performance.

---

# PHASE 23 — OPTIMIZATION

Benchmark:

```text
Whisper model
Qwen model
Kokoro
VAD
quantization
CPU/RAM
streaming chunk size
```

Optimize:

- first response latency
- turn-to-turn latency
- memory usage
- CPU/GPU usage
- reliability
- voice quality

### STOP HERE.

---

# PHASE 24 — DEPLOYMENT

Deployment is intentionally postponed until the system is working.

Evaluate current options such as:

- Vercel
- Render
- Hugging Face
- free VPS options
- low-cost VPS
- self-hosting
- other suitable infrastructure

Separate:

```text
Dashboard/API
```

from:

```text
Realtime voice runtime
```

if necessary.

Do not choose a platform solely because it advertises a free tier.

Benchmark the actual workload.

### STOP HERE.

---

# PHASE 25 — AVAILABILITY / KEEP-ALIVE

If using infrastructure that sleeps, investigate:

```text
external scheduler
       ↓
/health
       ↓
service
```

Keep-alive pings may be tested, but must NOT be treated as a guaranteed production reliability solution.

If a platform is unsuitable for always-on realtime workloads, move the voice runtime elsewhere.

### STOP HERE.

---

# PHASE 26 — FINAL HARDENING

Run at least 100+ realistic calls covering:

- English
- Hindi
- Hinglish
- unknown callers
- contacts
- spam
- scams
- recruiters
- delivery
- family
- emergencies
- interruptions
- noisy audio
- poor connections
- model failures
- database failures
- TTS failures
- STT failures

Fix the highest-impact failures.

Only after this should the system be considered trustworthy for regular personal use.

---

# Technologies NOT to Add Too Early

## LangGraph

Add only when the conversation/state complexity genuinely requires it.

## n8n

Add only when there are external workflows worth automating.

## MCP

Add only when enough external tools/services exist that standardized tool connectivity becomes useful.

## Multi-agent architecture

Do not introduce unless one agent demonstrably cannot handle the workload.

## Separate vector database

Do not add unless pgvector proves insufficient.

## Kubernetes

Do not use initially.

## Microservices

Keep the system modular, but reasonably monolithic until scaling actually requires separation.

---

# Final Engineering Philosophy

The project should optimize for:

1. Reliability
2. Natural conversation
3. Low latency
4. Privacy
5. Correct decisions
6. Safe human escalation
7. Hindi/English/Hinglish quality
8. Maintainability
9. Open-source/local operation
10. Real-world usefulness

The project is NOT merely a demonstration of trendy technologies.

The goal is to create a personal AI call system that can eventually be trusted with real incoming calls.

Use existing open-source infrastructure for plumbing.

Build the intelligence, policy, decision-making, memory, evaluation, and reliability yourself.

Most importantly:

**BUILD ONE PHASE → TEST → STOP → GET USER APPROVAL → NEXT PHASE.**

Never skip the phase gate.
