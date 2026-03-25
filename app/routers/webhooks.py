"""
Voice AI webhook handler.

Single endpoint that receives ALL events from the active voice provider
(Bolna or Vapi). Events are normalized via VoiceEngine.parse_webhook()
so this code is provider-agnostic.

Critical: tool-call responses must be returned quickly (within seconds)
so the voice AI can speak the result to the caller.
"""

import logging
from fastapi import APIRouter, Request, Response

from app.voice.factory import get_voice_engine
from app.services.lead_service import handle_lead_capture, handle_escalation
from app.services.knowledge_service import search_knowledge_base
from app.services.conversation_service import store_conversation

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/voice")
async def voice_webhook(request: Request):
    """
    Receive webhook events from Bolna/Vapi.

    Event types handled:
    - tool_call: process capture_lead / lookup_property / escalate_to_agent
    - call_ended: store conversation transcript + recording
    - Others: acknowledge with 200
    """
    payload = await request.json()
    engine = get_voice_engine()
    event = engine.parse_webhook(payload)

    logger.info(f"Webhook: {event.event_type} | call={event.call_id} | client={event.client_id}")

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

        logger.info(f"Tool call: {name} | params={params}")

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
