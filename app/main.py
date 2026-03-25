"""
PropBot — AI Receptionist SaaS for Indian Real Estate Agents.

FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db.supabase_client import init_supabase
from app.routers import webhooks, chat, leads, health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
        init_supabase(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        logging.getLogger(__name__).info("Supabase initialized")
    else:
        logging.getLogger(__name__).warning("Supabase not configured — running without DB")
    yield


app = FastAPI(
    title="PropBot AI Receptionist",
    version="1.0.0",
    description="AI-powered voice + chat receptionist for Indian real estate agents",
    lifespan=lifespan,
)

# CORS — allow all origins for the chat widget to work from any domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(webhooks.router, prefix="/api/webhooks")
app.include_router(chat.router, prefix="/api/chat")
app.include_router(leads.router, prefix="/api/leads")

# Serve chat widget static files
app.mount("/static", StaticFiles(directory="widget"), name="static")
