from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    """Health check endpoint. Also used as self-ping target to keep Render alive."""
    return {"status": "ok", "service": "propbot"}
