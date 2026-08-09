# 🩺 MediVoice — Voice Conversational Intake Agent

A real-time voice conversational AI agent for clinical intake, built around
a **Speech-to-Text → LLM (with tool calling) → Text-to-Speech** pipeline
using LiveKit Agents.

This build focuses on the **core conversation engine**: real-time voice,
turn-taking, clinical data collection via tool calls, and urgency
detection. Avatar rendering and cross-visit memory (Supabase/pgvector) are
intentionally left out of scope here — see Roadmap.

## Pipeline

```
Microphone --> Deepgram (STT) --> GPT-4o-mini (LLM + tool calling) --> Cartesia (TTS) --> Speaker
```

| Stage | Provider | Notes |
|---|---|---|
| STT | Deepgram `nova-2-medical` | Tuned for clinical vocabulary |
| LLM | OpenAI `gpt-4o-mini` | Drives conversation + calls clinical tools |
| TTS | Cartesia `sonic-2` | Low-latency natural speech |
| VAD | Silero | Detects turn-taking / when patient is speaking |
| Transport | LiveKit (WebRTC) | Real-time audio room between browser and agent |

## Project structure

```
medivoice/
├── backend/
│   ├── agent.py           # Core pipeline: STT + LLM + TTS wiring
│   ├── tools.py            # 7 clinical function-tools + in-memory session state
│   ├── prompts.py          # System instructions for the intake conversation
│   ├── token_server.py     # Issues LiveKit access tokens to the browser
│   ├── main.py              # Entry point for the agent worker
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx
│       └── components/VoiceCall.jsx   # Mic capture, audio playback, transcript UI
├── .env.example
└── README.md
```

## Prerequisites

You'll need your own API keys/accounts (all paid, usage-based — no fully
free tier, though Deepgram/Cartesia typically include a small starting
credit):

- [LiveKit Cloud](https://cloud.livekit.io) account (free tier available for dev)
- [Deepgram](https://deepgram.com) API key
- [Cartesia](https://cartesia.ai) API key
- [OpenAI](https://platform.openai.com) API key
- Python 3.10+
- Node.js 18+

## Setup

### 1. Configure environment

```bash
cp .env.example .env
# fill in your LiveKit, Deepgram, Cartesia, and OpenAI keys
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt

# Terminal 1 — token server (lets the browser join a room)
python token_server.py

# Terminal 2 — the voice agent worker
python main.py dev
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# open http://localhost:3000
```

Click **Start Call**, allow microphone access, and speak. Maya (the agent)
will greet you and begin the intake conversation.

## Clinical tools

The LLM can call these during the conversation (defined in `tools.py`):

| Tool | Purpose |
|---|---|
| `identify_patient` | Capture name, DOB, phone |
| `record_symptoms` | Onset, severity (1–10), location, duration |
| `set_urgency_flag` | Triage: low / medium / high / emergency |
| `update_medical_history` | Conditions, medications, allergies, surgeries |
| `record_insurance` | Provider, member ID, group number |
| `book_appointment` | Preferred doctor/time |
| `generate_intake_summary` | Final structured handoff, called at end of call |

Session data is held **in memory per call** (see `SessionStore` in
`tools.py`). Nothing is persisted to a database in this build — swap in
your own storage inside `generate_intake_summary` when you're ready
(e.g. write to Postgres, push to a clinic dashboard, or email a PDF).

## Emergency handling

The system prompt in `prompts.py` instructs the agent to immediately call
`set_urgency_flag(level="emergency")` and tell the patient to contact
emergency services if it detects red-flag symptoms (chest pain, difficulty
breathing, altered consciousness, etc.), pausing the standard intake flow.

## Streaming & chunking configuration

`agent.py` explicitly configures how audio and text are chunked as they
flow through the pipeline (see `CHUNKING_CONFIG`), rather than relying on
framework defaults:

| Setting | Value | Why |
|---|---|---|
| `preemptive_generation` | `True` | Starts the LLM call speculatively before the patient's turn is fully confirmed over, cutting perceived latency in back-and-forth exchanges |
| `min_endpointing_delay` | `0.4s` | Minimum silence before the agent treats the patient's turn as complete |
| `max_endpointing_delay` | `6.0s` | Caps how long the agent waits for a hesitant patient recalling a date or medication name |
| `allow_interruptions` | `True` | Patient can talk over the agent |
| `min_interruption_duration` | `0.4s` | Minimum speech length to count as a real interruption (filters out coughs/noise) |
| `min_interruption_words` | `1` | Even a short urgent phrase ("wait, it hurts more") can interrupt |
| `resume_false_interruption` | `True` | If a false interruption is detected (noise, no real transcript), the agent resumes speaking from where it left off |
| `false_interruption_timeout` | `1.0s` | How long to wait before deciding an interruption was false |

On the text→speech side, LLM tokens are streamed and split into
sentence-sized chunks (via the framework's sentence tokenizer) before being
sent to Cartesia, so audio starts playing after the first sentence rather
than waiting for the full reply — this happens automatically once a
streaming LLM + streaming TTS plugin are wired in, no extra code required.

Tune these in `CHUNKING_CONFIG` at the top of `agent.py` for your own
call patterns.

## Customizing

**Change the voice**: swap the `voice` ID in `cartesia.TTS(...)` inside
`agent.py`. Browse voices at [cartesia.ai](https://cartesia.ai).

**Change the LLM**: replace `openai.LLM(model="gpt-4o-mini")` with any
LiveKit-supported LLM plugin (Anthropic, Groq, etc.).

**Change the STT model**: `deepgram.STT(model="nova-2-medical")` can be
swapped for `nova-2` (general) or another Deepgram model.

## ⚠️ Disclaimer

This is a **clinical intake and triage assistance tool only**. It does not
diagnose, prescribe, or replace clinical judgment. All collected
information should be reviewed by a qualified healthcare professional.

## Roadmap (not included in this build)

- [ ] Persist sessions to a real database (Supabase/Postgres)
- [ ] Cross-visit semantic memory (pgvector)
- [ ] Live avatar (e.g. TruGen)
- [ ] PDF summary generation + clinic dashboard push
- [ ] Multi-language support
