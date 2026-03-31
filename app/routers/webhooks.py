"""
Voice AI webhook handler.

Single endpoint that receives ALL events from the active voice provider
(Bolna or Vapi). Events are normalized via VoiceEngine.parse_webhook()
so this code is provider-agnostic.

Critical: tool-call responses must be returned quickly (within seconds)
so the voice AI can speak the result to the caller.
"""

import hashlib
import hmac
import logging

from fastapi import APIRouter, Request, Response, HTTPException

from app.config import settings
from app.voice.factory import get_voice_engine
from app.services.lead_service import handle_lead_capture, handle_escalation
from app.services.knowledge_service import search_knowledge_base
from app.services.conversation_service import store_conversation

router = APIRouter()
logger = logging.getLogger(__name__)


def _verify_webhook_signature(request: Request, body: bytes) -> None:
    """
    Validate webhook authenticity using WEBHOOK_SECRET.

    Supports:
    - Bolna: X-Bolna-Signature header (HMAC-SHA256 hex of body)
    - Vapi:  X-Vapi-Secret header (plain secret)
    - Generic: X-Webhook-Secret header (plain secret)

    If WEBHOOK_SECRET is not configured, verification is skipped (dev mode).
    """
    secret = settings.WEBHOOK_SECRET
    if not secret:
        logger.warning("WEBHOOK_SECRET not set — webhook auth disabled")
        return

    # Bolna sends HMAC-SHA256 signature
    bolna_sig = request.headers.get("X-Bolna-Signature", "")
    if bolna_sig:
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(bolna_sig, expected):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        return

    # Vapi sends plain secret
    vapi_secret = request.headers.get("X-Vapi-Secret", "")
    if vapi_secret:
        if not hmac.compare_digest(vapi_secret, secret):
            raise HTTPException(status_code=401, detail="Invalid webhook secret")
        return

    # Generic fallback header
    generic_secret = request.headers.get("X-Webhook-Secret", "")
    if generic_secret:
        if not hmac.compare_digest(generic_secret, secret):
            raise HTTPException(status_code=401, detail="Invalid webhook secret")
        return

    # No auth header present — reject
    raise HTTPException(status_code=401, detail="Missing webhook authentication")


@router.post("/voice")
async def voice_webhook(request: Request):
    """
    Receive webhook events from Bolna/Vapi.

    Event types handled:
    - tool_call: process capture_lead / lookup_property / escalate_to_agent
    - call_ended: store conversation transcript + recording
    - Others: acknowledge with 200
    """
    body = await request.body()
    _verify_webhook_signature(request, body)

    try:
        import json
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    engine = get_voice_engine()
    event = engine.parse_webhook(payload)

    logger.info("Webhook: %s | call=%s | client=%s", event.event_type, event.call_id, event.client_id)

    if event.event_type == "tool_call":
        return await _handle_tool_calls(engine, event)

    if event.event_type == "call_ended":
        try:
            await store_conversation(event)
        except Exception as e:
            logger.error(f"Failed to store conversation: {e}")
        return Response(status_code=200)

    # Acknowledge all other events
    return Response(status_code=200)


async def _handle_tool_calls(engine, event) -> dict:
    """
    Process tool calls and return results fast.

    Each tool returns a string that the voice AI speaks to the caller.
    """
    all_results = []

    for tc in (event.tool_calls or []):
        name = tc["name"]
        params = tc.get("parameters", {})
        tc_id = tc["tool_call_id"]

        logger.info("Tool call: %s", name)  # params excluded — may contain PII

        try:
            if name == "capture_lead":
                result = await handle_lead_capture(
                    client_id=event.client_id,
                    call_id=event.call_id,
                    lead_data=params,
                )
            elif name == "lookup_property":
                result = await search_knowledge_base(
                    client_id=event.client_id,
                    query=params.get("query", ""),
                )
            elif name == "escalate_to_agent":
                result = await handle_escalation(
                    client_id=event.client_id,
                    call_id=event.call_id,
                    reason=params.get("reason", "Caller requested agent"),
                    caller_phone=params.get("caller_phone", ""),
                )
            else:
                result = f"Unknown tool: {name}"
                logger.warning(f"Unknown tool call: {name}")

        except Exception as e:
            logger.error(f"Tool call {name} failed: {e}")
            result = "Sorry, there was an error processing your request. The agent will follow up."

        response = engine.build_tool_response(tc_id, result)
        all_results.extend(response.get("results", []))

    return {"results": all_results}
