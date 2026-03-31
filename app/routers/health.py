from fastapi import APIRouter
from app.config import settings
from app.db.supabase_client import get_supabase

router = APIRouter()


@router.get("/health")
async def health():
    """Health check endpoint. Also used as self-ping target to keep Render alive."""
    checks = {
        "supabase_configured": bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY),
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "llm_provider": settings.LLM_PROVIDER,
    }
    try:
        db = get_supabase()
        db.table("clients").select("id").limit(1).execute()
        checks["supabase_connection"] = "ok"
    except Exception as e:
        checks["supabase_connection"] = f"error: {type(e).__name__}"

    return {"status": "ok", "service": "propbot", "checks": checks}
