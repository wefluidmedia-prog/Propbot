"""
Chat widget API endpoints.

Two endpoints:
1. POST /api/chat/{client_id} — process a chat message via Claude
2. POST /api/chat/{client_id}/callback — handle "Request Callback" button
"""

import logging

from fastapi import APIRouter, HTTPException, Request

from app.models.chat import ChatRequest, ChatResponse
from app.models.lead import CallbackRequest
from app.rate_limit import rate_limit_chat, rate_limit_callback
from app.services.claude_service import get_chat_response
from app.services.lead_service import store_callback_request

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{client_id}", response_model=ChatResponse)
async def chat_message(client_id: str, req: ChatRequest, request: Request):
    """Process a chat message for a client's widget."""
    rate_limit_chat(request, client_id)

    # Enforce subscription
    from app.services.billing_service import check_subscription_active
    if not await check_subscription_active(client_id):
        return ChatResponse(
            reply="This service is currently unavailable. Please contact the business directly.",
            visitor_id=req.visitor_id or "",
        )

    # Chat widget is Pro-only
    from app.db.supabase_client import get_supabase
    db = get_supabase()
    _client = db.table("clients").select("plan_type").eq("id", client_id).single().execute()
    if (_client.data or {}).get("plan_type") == "starter":
        return ChatResponse(
            reply="Chat is available on the Pro plan. Please call us directly for assistance.",
            visitor_id=req.visitor_id or "",
        )

    try:
        history = [{"role": m.role, "content": m.content} for m in req.history]
        result = await get_chat_response(
            client_id=client_id,
            message=req.message,
            conversation_history=history,
            visitor_id=req.visitor_id,
        )
        return ChatResponse(reply=result["text"], visitor_id=result["visitor_id"])
    except Exception as e:
        logger.error("Chat error for client %s: %s", client_id, e)
        raise HTTPException(status_code=500, detail="An error occurred processing your message")


@router.post("/{client_id}/callback")
async def request_callback(client_id: str, req: CallbackRequest, request: Request):
    """Handle 'Request Callback' button from chat widget."""
    rate_limit_callback(request, client_id)

    # Enforce subscription
    from app.services.billing_service import check_subscription_active
    if not await check_subscription_active(client_id):
        raise HTTPException(status_code=403, detail="Service inactive — subscription required")

    try:
        await store_callback_request(
            client_id=client_id,
            name=req.name,
            phone=req.phone,
            preferred_time=req.preferred_time,
            context=req.context,
        )
        return {
            "status": "ok",
            "message": "Callback request received. Agent will call you shortly.",
        }
    except Exception as e:
        logger.error("Callback error for client %s: %s", client_id, e)
        raise HTTPException(status_code=500, detail="Failed to submit callback request")
