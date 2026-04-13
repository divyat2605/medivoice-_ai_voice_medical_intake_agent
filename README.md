<div align="center">

<img src="assets/architecture.gif" alt="MediVoice Architecture" width="100%"/>

# 🩺 MediVoice - AI Voice Medical Intake Agent

**A real-time voice AI agent that conducts clinical intake conversations, collects patient history, detects urgency, and hands off a structured summary to the care team — before the patient even walks in.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![LiveKit](https://img.shields.io/badge/LiveKit-Agents-00A896?style=flat-square)](https://livekit.io)
[![Supabase](https://img.shields.io/badge/Supabase-pgvector-3ECF8E?style=flat-square&logo=supabase&logoColor=white)](https://supabase.com)
[![TruGen](https://img.shields.io/badge/TruGen-Huma--1_Avatar-7C3AED?style=flat-square)](https://trugen.ai)

</div>

---

## ✨ What it does

MediVoice replaces paper intake forms with a warm, avatar-driven voice conversation. Patients speak naturally; the agent collects chief complaint, symptoms, medical history, medications, allergies, and insurance details — then generates a structured clinical summary for the care team.

- 🎙️ **Real-time voice** — sub-second STT + TTS, no awkward pauses
- 👤 **Live avatar** — TruGen Huma-1 lip-synced talking head, <80ms response
- 🧠 **Patient memory** — pgvector recalls history across visits ("you mentioned a penicillin allergy last time — is that still correct?")
- 🚨 **Urgency detection** — auto-escalates to emergency path on red-flag symptoms
- 📋 **Clinical handoff** — structured PDF summary pushed to clinic dashboard
- 🔒 **Persistent EHR** — Supabase stores conditions, medications, allergies, insurance

---

## 🏗️ Architecture

| Layer | Technology | Role |
|---|---|---|
| **Voice transport** | LiveKit (WebRTC) | Real-time audio rooms |
| **Avatar** | TruGen Huma-1 | Lip-synced talking face, ≤80ms |
| **STT** | Deepgram Nova-2 | Speech → text |
| **LLM** | GPT-4o-mini | Clinical reasoning + tool calling |
| **TTS** | Cartesia | Text → speech |
| **Memory** | Supabase + pgvector | Patient history + semantic recall |
| **Backend** | Python + livekit-agents SDK | Pipeline orchestration |
| **Frontend** | React + LiveKit SDK | Browser UI + avatar display |

---

## 🗂️ Project Structure

```
medivoice/
├── backend/
│   ├── agent.py              # LiveKit agent — pipeline + conversation flow
│   ├── tools.py              # Tool functions (8 clinical tools)
│   ├── database.py           # Supabase queries + pgvector memory manager
│   ├── summarizer.py         # End-of-call clinical summary extractor
│   ├── token_server.py       # FastAPI token generation :8080
│   └── main.py               # Entry point
│
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── VoiceCall.jsx         # Main call UI
│       │   ├── AvatarDisplay.jsx     # TruGen avatar renderer
│       │   ├── IntakeSummary.jsx     # Post-call clinical summary
│       │   └── UrgencyBanner.jsx     # Emergency escalation UI
│       └── App.jsx
│
├── database/
│   └── schema.sql            # Full Supabase schema + pgvector setup
│
└── .env.example
```

---

## 🛠️ Tool Functions

The agent has 8 clinical tools it can call during conversation:

| Tool | Description |
|---|---|
| `identify_patient` | Lookup or create patient by phone + date of birth |
| `record_symptoms` | Store onset, severity (1–10), location, duration |
| `set_urgency_flag` | Set triage level: low / medium / high / emergency |
| `fetch_medical_history` | Retrieve prior conditions, medications, allergies |
| `update_medical_history` | Upsert conditions, medications, surgeries |
| `record_insurance` | Capture provider, member ID, group number |
| `book_appointment` | Schedule with preferred doctor + urgency context |
| `generate_intake_summary` | Build structured clinical handoff PDF |

---

## 🧠 Patient Memory with pgvector

MediVoice uses **two memory layers** so returning patients feel recognised, not interrogated again:

**Structured memory** — exact facts in SQL: conditions, medications, allergies, insurance. Pulled at call start and confirmed with the patient.

**Semantic memory** — each call summary is embedded with `text-embedding-3-small` and stored in pgvector with an HNSW index. At the next visit, a cosine similarity search retrieves the most relevant past context and injects it into the system prompt.

```
"I can see from your last visit in March you were experiencing lower back pain
and are currently on metformin 500mg. Is that still the case, or has anything changed?"
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- LiveKit Cloud account
- Deepgram API key
- Cartesia API key
- OpenAI API key
- TruGen API key
- Supabase project

### 1. Clone & install

```bash
git clone https://github.com/yourname/medivoice.git
cd medivoice
```

```bash
# Backend
cd backend
pip install -r requirements.txt
```

```bash
# Frontend
cd frontend
npm install
```

### 2. Configure environment

```bash
cp .env.example .env
```

```env
# LiveKit
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...

# Voice pipeline
DEEPGRAM_API_KEY=...
CARTESIA_API_KEY=...
OPENAI_API_KEY=...

# Avatar
TRUGEN_API_KEY=...
TRUGEN_AVATAR_ID=45e3f732

# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=...
```

### 3. Set up the database

Run the schema in your Supabase SQL editor:

```bash
# Paste contents of database/schema.sql into Supabase SQL Editor
# This creates: patients, intake_sessions, medical_history,
#               insurance, appointments, memory_summaries (pgvector)
```

### 4. Run the backend

```bash
# Terminal 1 — token server
python token_server.py

# Terminal 2 — LiveKit agent
python main.py dev
```

### 5. Run the frontend

```bash
cd frontend
npm run dev
# Open http://localhost:3000
```

---

## 💬 Conversation Flow

```
1. Identity         →  Name · DOB · phone number
2. Reason for visit →  Chief complaint · appointment type
3. Symptom deep-dive→  Onset · severity · location · duration · aggravating factors
4. Medical history  →  Conditions · medications · allergies · surgeries
5. Lifestyle        →  Smoking · alcohol · family history · last visit
6. Insurance        →  Provider · member ID · consent to treat
7. Handoff          →  Clinical PDF summary → clinic dashboard
```

> ⚠️ **Emergency path**: If the patient describes red-flag symptoms (chest pain, difficulty breathing, altered consciousness), the agent immediately sets `urgency = emergency`, stops the intake flow, and instructs the patient to call emergency services.

---

## 🔧 Configuration

### Changing the avatar

Find available avatar IDs at [docs.trugen.ai/docs/avatars/overview](https://docs.trugen.ai/docs/avatars/overview). Set `TRUGEN_AVATAR_ID` in `.env`.

### Swapping the LLM

Replace `openai.LLM(model="gpt-4o-mini")` in `agent.py` with any OpenAI-compatible provider. For lower latency, Groq with `llama-3.3-70b-versatile` is a strong alternative.

### Swapping STT

The agent defaults to Deepgram Nova-2. To use Groq Whisper instead:

```python
# In agent.py
from livekit.plugins import groq
stt=groq.STT(model="whisper-large-v3-turbo")
```

---

## 📊 Database Schema (overview)

```
patients          → id · name · dob · phone
intake_sessions   → patient_id · symptoms (jsonb) · urgency · chief_complaint
medical_history   → patient_id · conditions · medications · allergies · surgeries
insurance         → patient_id · provider · member_id · group_number
appointments      → patient_id · datetime · doctor · urgency · session_id
memory_summaries  → patient_id · content · embedding vector(1536) [HNSW index]
```

---

## ⚠️ Important Disclaimer

MediVoice is a **clinical intake and triage assistance tool only**. It collects structured information and flags urgency — it does not diagnose, prescribe, or replace clinical judgment. All collected data is reviewed by a qualified healthcare professional before any clinical decision is made.

---

## 🗺️ Roadmap

- [ ] Multi-language support (Hindi, Spanish, Arabic)
- [ ] EHR integration (FHIR / HL7)
- [ ] Post-visit follow-up agent
- [ ] Medication reminder voice calls
- [ ] Clinic dashboard web app

---

## 🤝 Contributing

Contributions are welcome! Fork the repo, make your changes, and open a pull request.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add my feature'`
4. Push and open a PR

---

<div align="center">

Built with ❤️ using LiveKit · TruGen · Deepgram · OpenAI · Cartesia · Supabase

</div>