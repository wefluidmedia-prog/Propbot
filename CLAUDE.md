# PropBot — Claude Code Instructions

## Stack
FastAPI + Supabase (PostgreSQL) + Bolna.ai (voice) + Exotel (telephony) + Claude Sonnet 4 + Render (hosting)

## Environment
- OS: Windows 11 with OneDrive active
- Project is at `E:\Claude Code\properties` — this is NOT OneDrive-synced, safe to create/delete files freely
- Always confirm working directory is `E:\Claude Code\properties` before running commands
- Python 3.11+ is installed and on PATH

## Workflow Rules
- Always commit working code before making deployment changes, API calls to deployed endpoints, or starting new feature branches — run `git status` first
- Always check that dependencies are in requirements.txt before deploying — verify imports resolve locally before pushing
- When modifying existing pages or templates, verify no regressions before moving to the next task (curl affected routes, check for 200) — never inject raw code (e.g. GA scripts) via f-strings in HTML templates
- After completing each feature or fix, commit immediately with a descriptive message before starting the next task

## Python / FastAPI Rules
- Always include `python-multipart` in requirements.txt for any FastAPI project
- Define all module-level constants (e.g. _SHARED_CSS) before they are referenced
- Never put real API keys in .env.example — only in .env (which is gitignored)
- Use `python-dotenv` to load .env; confirm .env exists before running the app
- Always annotate FastAPI route parameters with types (e.g. `request: Request`) — missing types cause 404s
- Never call functions that return strings with `{` or `}` inside an f-string — use placeholder + `.replace()` pattern instead (e.g. `<!-- __GA__ -->` replaced at render time)

## Git Workflow
- Commit after each completed phase, not at the end of everything
- Use descriptive commit messages referencing the feature (e.g. "Add Razorpay subscription webhook handler")
- Never force push to main
- Always push to origin after committing — Render auto-deploys on push to main

## Deployment (Render)
- Plan: Render Starter (paid) — always-on, no cold starts, no self-ping needed
- Live URL: https://propbot.co.in (custom domain, purchased)
- Render subdomain: https://propbot-3wrp.onrender.com — DISABLED (custom domain only)
- Auto-deploys on push to main branch
- Health check: `curl https://propbot.co.in/health`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Local dev: `uvicorn app.main:app --reload`

## Testing
- Run tests: `python -m pytest tests/ -v`
- Always run tests before pushing to main
- 2 pre-existing test failures in test_webhook_handler.py (auth-related, not our bugs) — ignore these
- After pushing, wait ~2 min for Render to deploy, then curl https://propbot.co.in/health to confirm

## Key Files
- Entry point: `app/main.py`
- Landing page: `app/routers/health.py` (also has POST /contact)
- Pricing page: `app/routers/pricing.py`
- Dashboard SPA: `app/routers/dashboard.py`
- Signup wizard: `app/routers/signup.py`
- Admin dashboard: `app/routers/admin.py` (founder-only, auth via WEBHOOK_SECRET)
- Billing: `app/routers/billing.py` + `app/services/billing_service.py`
- Onboarding (Bolna provisioning): `app/services/onboarding_service.py`
- DB schema: `app/db/schema.sql`
- Config (all env vars): `app/config.py`

## Key Config / Env Vars
- WEBHOOK_SECRET — also used as admin dashboard password at /admin
- RAZORPAY_KEY_ID / KEY_SECRET / PLAN_ID / STARTER_PLAN_ID / WEBHOOK_SECRET
- GA_MEASUREMENT_ID — set → enables Google Analytics on all pages
- WHATSAPP_NUMBER — set (digits only, no +91) → shows WhatsApp floating button
- SUPABASE_URL / SUPABASE_SERVICE_KEY
- SMTP_EMAIL / SMTP_APP_PASSWORD
- BASE_URL — set to https://propbot.co.in

## Supabase
- Project ID: bnmilqrtxfxbzecydjda
- Use MCP supabase tools for migrations and SQL queries
- subscription_status values: trial | active | paused | cancelled | expired
