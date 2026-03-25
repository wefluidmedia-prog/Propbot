# PropBot — AI Receptionist for Indian Real Estate Agents

AI-powered voice + chat receptionist that handles inbound calls, qualifies leads, and alerts agents instantly. Built for solo real estate agents in India, starting with Delhi NCR.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        VOICE CALL FLOW                              │
│                                                                     │
│  Caller (Hindi/English/Hinglish)                                    │
│    │                                                                │
│    ▼                                                                │
│  Exotel Virtual Number (Indian DID, +91-XXX)                       │
│    │                                                                │
│    ▼                                                                │
│  Bolna.ai Voice Platform                                            │
│    ├── Deepgram STT (multi-language, auto-detect Hindi/English)     │
│    ├── Claude claude-sonnet-4-20250514 (via LiteLLM/OpenRouter)                    │
│    └── ElevenLabs TTS (Hindi-capable female voice "Priya")         │
│    │                                                                │
│    ├── tool-calls webhook ──► FastAPI Backend (Render.com)         │
│    │                            ├── Supabase: store lead            │
│    │                            ├── Gmail SMTP: email to agent      │
│    │                            └── Exotel SMS: alert to agent      │
│    │                                                                │
│    └── end-of-call webhook ──► FastAPI Backend                     │
│                                 └── Supabase: store conversation    │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        CHAT WIDGET FLOW                             │
│                                                                     │
│  Website Visitor                                                    │
│    │                                                                │
│    ▼                                                                │
│  Vanilla JS Chat Widget (embedded via <script> tag)                │
│    │                                                                │
│    ├── POST /api/chat/{client_id}                                  │
│    │     └── FastAPI ──► Claude API (direct) ──► Response           │
│    │                                                                │
│    └── "Request Callback" button                                   │
│          └── POST /api/chat/{client_id}/callback                   │
│                └── Supabase: store request + email/SMS alert        │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      MULTI-TENANT MODEL                             │
│                                                                     │
│  Each Client (Real Estate Agent) gets:                              │
│    ├── 1 Exotel virtual number                                     │
│    ├── 1 Bolna voice agent (with personalized system prompt)       │
│    ├── 1 Supabase config row (tenant settings)                     │
│    └── 1 Markdown knowledge base (listings + FAQs)                 │
└─────────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Component | Service | Why |
|-----------|---------|-----|
| Voice AI | Bolna.ai (OSS, YC-backed) | ~$0.06/min, native Hindi/Hinglish, built-in Exotel |
| Telephony | Exotel | Indian numbers, INR billing, SMS API |
| Chat | Vanilla JS widget | Zero dependencies, mobile-first, embeddable |
| AI Brain | Claude claude-sonnet-4-20250514 | Best multilingual reasoning |
| Backend | Python FastAPI | Async, fast, easy to maintain |
| Database | Supabase (free tier) | Postgres + REST API, generous free tier |
| Alerts | Gmail SMTP + Exotel SMS | Free + INR billing |
| Payments | Razorpay (personal) | UPI + cards, no GST needed |
| Hosting | Render.com (free tier) | Easy deploy, self-ping for uptime |

## VoiceEngine Abstraction

The voice provider is swappable via a single env var:

```
VOICE_PROVIDER=bolna   # Primary (Bolna.ai)
VOICE_PROVIDER=vapi    # Fallback (Vapi.ai)
VOICE_PROVIDER=pipecat # Future (self-hosted)
```

All downstream code (lead capture, alerts, storage) is provider-agnostic.

## Quick Start

```bash
# 1. Clone and install
git clone <repo-url> && cd properties
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Fill in your API keys

# 3. Set up Supabase
# Run app/db/schema.sql in your Supabase SQL editor

# 4. Run locally
uvicorn app.main:app --reload

# 5. Onboard demo client
python scripts/seed_demo.py
```

## Cost per Client

| Item | Monthly Cost |
|------|-------------|
| Bolna.ai (~70 calls x 3 min @ $0.06/min) | ~₹1,050 |
| Exotel number + minutes | ~₹500 |
| Claude API (chat widget) | ~₹200 |
| Supabase | Free |
| Render.com | Free |
| Gmail SMTP | Free |
| **Total** | **~₹1,750** |
| **Revenue** | **₹5,000** |
| **Margin** | **~₹3,250 (65%)** |
