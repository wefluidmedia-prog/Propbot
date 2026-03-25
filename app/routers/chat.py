"""
Chat widget API endpoints.

Two endpoints:
1. POST /api/chat/{client_id} — process a chat message via Claude
2. POST /api/chat/{client_id}/callback — handle "Request Callback" button
"""

from fastapi import APIRouter, HTTPException

from app.models.chat import ChatRequest, ChatResponse
from app.models.lead import CallbackRequest
from app.services.claude_service import get_chat_response
from app.services.lead_service import store_callback_request

router = APIRouter()


@router.post("/{client_id}", response_model=ChatResponse)
async def chat_message(client_id: str, req: ChatRequest):
    """Process a chat message for a client's widget."""
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
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@router.post("/{client_id}/callback")
async def request_callback(client_id: str, req: CallbackRequest):
    """Handle 'Request Callback' button from chat widget."""
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
        raise HTTPException(status_code=500, detail=f"Callback error: {str(e)}")
