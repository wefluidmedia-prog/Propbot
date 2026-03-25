"""
Lead capture and storage service.

Handles:
1. Storing qualified leads from voice calls (via tool call webhook)
2. Storing callback requests from chat widget
3. Triggering alerts to agents
"""

import asyncio
import logging
from app.db.supabase_client import get_supabase
from app.services.alert_service import send_lead_alert, send_callback_alert

logger = logging.getLogger(__name__)


async def handle_lead_capture(
    client_id: str,
    call_id: str,
    lead_data: dict,
) -> str:
    """
    Store a lead and send alerts. Called from webhook handler
    when Bolna/Vapi triggers the capture_lead tool.

    Returns a confirmation string that the voice AI speaks to the caller.
    """
    db = get_supabase()

    # Store lead
    lead_record = {
        "client_id": client_id,
        "call_id": call_id,
        "source": lead_data.get("source", "voice"),
        "caller_name": lead_data.get("name"),
        "caller_phone": lead_data.get("phone"),
        "budget_min": lead_data.get("budget_min"),
        "budget_max": lead_data.get("budget_max"),
        "preferred_area": lead_data.get("preferred_area"),
        "property_type": lead_data.get("property_type"),
        "urgency": lead_data.get("urgency"),
        "preferred_viewing_time": lead_data.get("viewing_time"),
        "notes": lead_data.get("notes"),
    }

    result = db.table("leads").insert(lead_record).execute()
    lead_id = result.data[0]["id"]
    logger.info(f"Lead {lead_id} stored for client {client_id}")

    # Get client config for alert
    client_result = db.table("clients").select("*").eq("id", client_id).single().execute()
    client_data = client_result.data

    # Send alerts asynchronously (don't block the webhook response)
    asyncio.create_task(_send_alert_safe(client_data, {**lead_record, "id": lead_id}))

    return "Lead information saved successfully. The agent will contact you shortly."


async def handle_escalation(
    client_id: str,
    call_id: str,
    reason: str,
    caller_phone: str = "",
) -> str:
    """Handle escalation to human agent."""
    db = get_supabase()

    # Store as a lead with escalation note
    lead_record = {
        "client_id": client_id,
        "call_id": call_id,
        "source": "voice",
        "caller_phone": caller_phone,
        "notes": f"ESCALATED: {reason}",
        "status": "new",
    }
    db.table("leads").insert(lead_record).execute()

    # Get client and send urgent alert
    client_result = db.table("clients").select("*").eq("id", client_id).single().execute()
    asyncio.create_task(_send_alert_safe(client_result.data, lead_record))

    return "I have notified the agent. They will call you back shortly."


async def store_callback_request(
    client_id: str,
    name: str | None,
    phone: str,
    preferred_time: str | None = None,
    context: str | None = None,
) -> str:
    """Store a callback request from the chat widget and alert agent."""
    db = get_supabase()

    record = {
        "client_id": client_id,
        "visitor_name": name,
        "visitor_phone": phone,
        "preferred_time": preferred_time,
        "context": context,
    }
    result = db.table("callback_requests").insert(record).execute()
    logger.info(f"Callback request stored: {result.data[0]['id']}")

    # Get client and send alert
    client_result = db.table("clients").select("*").eq("id", client_id).single().execute()
    asyncio.create_task(_send_callback_alert_safe(client_result.data, record))

    return "Callback request received. The agent will call you shortly."


async def _send_alert_safe(client_data: dict, lead_data: dict) -> None:
    """Send alert with error handling — never raises."""
    try:
        await send_lead_alert(client_data, lead_data)
        # Mark alert as sent
        if lead_data.get("id"):
            db = get_supabase()
            db.table("leads").update({"alert_sent": True}).eq("id", lead_data["id"]).execute()
    except Exception as e:
        logger.error(f"Failed to send lead alert: {e}")


async def _send_callback_alert_safe(client_data: dict, callback_data: dict) -> None:
    """Send callback alert with error handling."""
    try:
        await send_callback_alert(client_data, callback_data)
    except Exception as e:
        logger.error(f"Failed to send callback alert: {e}")
