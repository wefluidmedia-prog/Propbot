"""
Leads API — client dashboard endpoint.

Authentication: per-client API keys (pb_...) or legacy WEBHOOK_SECRET.
Per-client keys enforce tenant isolation — a client can only see their own leads.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_client_key
from app.db.supabase_client import get_supabase

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/{client_id}")
async def list_leads(
    client_id: str,
    limit: int = Query(default=50, le=200, ge=1),
    status: str | None = Query(default=None, pattern="^(new|contacted|qualified|converted|lost)$"),
    auth_client_id: str = Depends(require_client_key),
):
    """List recent leads for a client. Sorted newest first."""
    # Tenant isolation: if using per-client key, enforce match
    if auth_client_id != "__legacy__" and auth_client_id != client_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        db = get_supabase()
        query = (
            db.table("leads")
            .select("*")
            .eq("client_id", client_id)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if status:
            query = query.eq("status", status)
        result = query.execute()
        return {"leads": result.data, "count": len(result.data)}
    except Exception as e:
        logger.error("Failed to list leads for %s: %s", client_id, e)
        raise HTTPException(status_code=500, detail="Failed to retrieve leads")


@router.get("/{client_id}/{lead_id}")
async def get_lead(
    client_id: str,
    lead_id: str,
    auth_client_id: str = Depends(require_client_key),
):
    """Get a single lead by ID."""
    if auth_client_id != "__legacy__" and auth_client_id != client_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        db = get_supabase()
        result = (
            db.table("leads")
            .select("*")
            .eq("id", lead_id)
            .eq("client_id", client_id)
            .single()
            .execute()
        )
        return result.data
    except Exception as e:
        logger.error("Failed to get lead %s: %s", lead_id, e)
        raise HTTPException(status_code=404, detail="Lead not found")


@router.patch("/{client_id}/{lead_id}")
async def update_lead_status(
    client_id: str,
    lead_id: str,
    status: str = Query(pattern="^(new|contacted|qualified|converted|lost)$"),
    notes: str | None = None,
    auth_client_id: str = Depends(require_client_key),
):
    """Update a lead's status and/or notes."""
    if auth_client_id != "__legacy__" and auth_client_id != client_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        db = get_supabase()
        update_data = {"status": status}
        if notes is not None:
            update_data["notes"] = notes

        result = (
            db.table("leads")
            .update(update_data)
            .eq("id", lead_id)
            .eq("client_id", client_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Lead not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update lead %s: %s", lead_id, e)
        raise HTTPException(status_code=500, detail="Failed to update lead")
