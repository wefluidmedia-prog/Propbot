"""
PropBot — AI Receptionist SaaS for Indian Real Estate Agents.

FastAPI application entry point.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db.supabase_client import init_supabase
from app.routers import webhooks, chat, leads, health, dashboard, signup, billing, pricing

logger = logging.getLogger(__name__)


async def _self_ping():
    """No-op on App Runner (always warm). Kept for local/Render compatibility."""
    return

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
        init_supabase(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        logger.info("Supabase initialized")
    else:
        logger.warning("Supabase not configured — running without DB")
    # Start self-ping task to keep Render free tier alive
    ping_task = asyncio.create_task(_self_ping())
    yield
    ping_task.cancel()


app = FastAPI(
    title="PropBot AI Receptionist",
    version="1.0.0",
    description="AI-powered voice + chat receptionist for Indian real estate agents",
    lifespan=lifespan,
)

# CORS — allow all origins for the chat widget (embedded on customer sites).
# allow_credentials=False is required when allow_origins=["*"] per CORS spec.
# The widget uses no cookies, so credentials are not needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)

# Routers
app.include_router(health.router)
app.include_router(webhooks.router, prefix="/api/webhooks")
app.include_router(chat.router, prefix="/api/chat")
app.include_router(leads.router, prefix="/api/leads")
app.include_router(dashboard.router, prefix="/dashboard")
app.include_router(signup.router, prefix="/signup")
app.include_router(billing.router, prefix="/api/billing")
app.include_router(pricing.router, prefix="/pricing")

# Serve chat widget static files
app.mount("/static", StaticFiles(directory="widget"), name="static")
