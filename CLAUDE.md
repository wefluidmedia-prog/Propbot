# PropBot — Claude Code Instructions

## Stack
FastAPI + Supabase (PostgreSQL) + Bolna.ai (voice) + Exotel (telephony) + Claude Sonnet 4 + Render (hosting)

## Environment
- OS: Windows 11 with OneDrive active
- Project is at `E:\Claude Code\properties` — this is NOT OneDrive-synced, safe to create/delete files freely
- Always confirm working directory is `E:\Claude Code\properties` before running commands
- Python 3.11+ is installed and on PATH

## Python / FastAPI Rules
- Always include `python-multipart` in requirements.txt for any FastAPI project
- Define all module-level constants (e.g. _SHARED_CSS) before they are referenced
- Never put real API keys in .env.example — only in .env (which is gitignored)
- Use `python-dotenv` to load .env; confirm .env exists before running the app

## Git Workflow
- Commit after each completed phase, not at the end of everything
- Use descriptive commit messages referencing the feature (e.g. "Add Razorpay subscription webhook handler")
- Never force push to main

## Deployment (Render)
- Live URL: https://propbot-3wrp.onrender.com
- Auto-deploys on push to main branch
- Health check: `curl https://propbot-3wrp.onrender.com/health`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Local dev: `uvicorn app.main:app --reload`

## Testing
- Run tests: `python -m pytest tests/ -v`
- Always run tests before pushing to main

## Key Files
- Entry point: `app/main.py`
- Dashboard: `app/routers/dashboard.py`
- Signup wizard: `app/routers/signup.py`
- Onboarding (Bolna provisioning): `app/services/onboarding_service.py`
- DB schema: `app/db/schema.sql`
