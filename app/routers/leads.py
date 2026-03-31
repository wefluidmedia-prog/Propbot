"""
Leads API — future agent dashboard endpoint.

MVP: simple GET endpoint to list leads for a client.
Phase 2: full dashboard with filtering, status updates.

Authentication: requires Authorization: Bearer <WEBHOOK_SECRET> header.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.db.supabase_client import get_supabase

router = APIRouter()
logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=True)


def _require_api_key(credentials: HTTPAuthorizationCredentials = Security(_bearer)) -> None:
    """Validate Bearer token against WEBHOOK_SECRET."""
    if not settings.WEBHOOK_SECRET:
        logger.warning("WEBHOOK_SECRET not set — leads API auth disabled")
        return
    if credentials.credentials != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.get("/{client_id}", dependencies=[Depends(_require_api_key)])
async def list_leads(client_id: str, limit: int = 50):
    """List recent leads for a client. Sorted newest first."""
    if limit > 200:
        limit = 200
    try:
        db = get_supabase()
        result = (
            db.table("leads")
            .select("*")
            .eq("client_id", client_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return {"leads": result.data, "count": len(result.data)}
    except Exception as e:
        logger.error("Failed to list leads for %s: %s", client_id, e)
        raise HTTPException(status_code=500, detail="Failed to retrieve leads")
