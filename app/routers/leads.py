"""
Leads API — future agent dashboard endpoint.

MVP: simple GET endpoint to list leads for a client.
Phase 2: full dashboard with filtering, status updates.
"""

from fastapi import APIRouter, HTTPException
from app.db.supabase_client import get_supabase

router = APIRouter()


@router.get("/{client_id}")
async def list_leads(client_id: str, limit: int = 50):
    """List recent leads for a client. Sorted newest first."""
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
        raise HTTPException(status_code=500, detail=str(e))
