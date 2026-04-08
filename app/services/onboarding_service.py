"""
Client onboarding service — provisions voice agents automatically.

Extracted from scripts/onboard_client.py for use by the signup wizard.
"""

import asyncio
import logging

from app.config import settings
from app.db.supabase_client import get_supabase
from app.voice.factory import get_voice_engine
from app.voice.base import AgentConfig, VOICE_TOOLS
from app.prompts.system_prompt import build_system_prompt_from_config
from app.auth import create_api_key

logger = logging.getLogger(__name__)


async def provision_voice_agent(client_id: str) -> str:
    """
    Create a Bolna voice agent for a client.

    Reads client data from DB, builds system prompt, creates agent,
    stores agent_id back in DB, generates API key.

    If the phone pool is empty, sets setup_status='pending_number' (not 'failed')
    so the founder can assign a number manually via /admin.

    Returns the agent_id.
    """
    db = get_supabase()
    result = db.table("clients").select("*").eq("id", client_id).single().execute()
    client = result.data

    persona = client.get("assistant_persona_name", "Priya")
    business = client["business_name"]
    agent_name = client["agent_name"]
    kb = client.get("knowledge_base", "")
    voice_id = client.get("voice_id", "")
    lang_pref = client.get("language_preference", "hi,en")

    # Build system prompt
    system_prompt = build_system_prompt_from_config(
        business_name=business,
        agent_name=agent_name,
        persona_name=persona,
        knowledge_base=kb,
        channel="voice",
    )

    # Build greeting
    first_message = client.get("first_message") or (
        f"Namaste! {business} mein aapka swagat hai. "
        f"Main {persona} bol rahi hoon. Boliye, kaise madad kar sakti hoon?"
    )

    config = AgentConfig(
        agent_name=f"{persona} - {business}",
        first_message=first_message,
        system_prompt=system_prompt,
        voice_id=voice_id,
        language_hints=lang_pref.split(","),
        tools=VOICE_TOOLS,
        webhook_url=f"{settings.BASE_URL}/api/webhooks/voice",
        client_id=client_id,
        telephony_number=client.get("vobiz_number", ""),
    )

    engine = get_voice_engine()
    handle = await engine.create_agent(config)
    logger.info("Voice agent created for %s: %s", business, handle.agent_id)

    # Store agent ID
    agent_field = "bolna_agent_id" if handle.provider == "bolna" else "vapi_assistant_id"
    db.table("clients").update({
        agent_field: handle.agent_id,
        "first_message": first_message,
        "onboarding_step": 3,
    }).eq("id", client_id).execute()

    # Try to assign phone number from pool and bind to Bolna agent
    from app.services.phone_service import assign_phone_number
    phone_number = await assign_phone_number(client_id)
    if phone_number:
        # Update Bolna agent with the phone number
        config.telephony_number = phone_number
        await engine.update_agent(handle.agent_id, config)
        db.table("clients").update({"setup_status": "ready"}).eq("id", client_id).execute()
        logger.info("Phone %s assigned and bound to agent for %s", phone_number, business)
    else:
        # Pool empty — agent is ready, just needs a number assigned manually
        db.table("clients").update({"setup_status": "pending_number"}).eq("id", client_id).execute()
        logger.warning("No phone in pool for client %s — set to pending_number", client_id)

    # Generate API key
    raw_key = create_api_key(client_id, label="signup")
    logger.info("API key generated for %s", business)

    # Fire-and-forget: notify founder of new signup
    asyncio.create_task(_notify_founder_signup(
        client_id=client_id,
        business_name=business,
        agent_name=agent_name,
        agent_email=client.get("agent_email", ""),
        agent_phone=client.get("agent_phone", ""),
        bolna_agent_id=handle.agent_id,
        phone_assigned=phone_number,
        setup_status="ready" if phone_number else "pending_number",
    ))

    return handle.agent_id


async def _notify_founder_signup(
    client_id: str,
    business_name: str,
    agent_name: str,
    agent_email: str,
    agent_phone: str,
    bolna_agent_id: str,
    phone_assigned: str | None,
    setup_status: str,
) -> None:
    """Send founder email alert on every new signup."""
    if not settings.SMTP_EMAIL:
        return
    try:
        from app.services.alert_service import _send_email
        phone_line = (
            phone_assigned if phone_assigned
            else "None — buy a Vobiz number and assign via /admin"
        )
        body = f"""
<div style="font-family:Arial,sans-serif;max-width:600px;">
  <h2 style="color:#FF5722;">New PropBot Signup</h2>
  <table style="width:100%;border-collapse:collapse;">
    <tr><td style="padding:8px;border-bottom:1px solid #eee;font-weight:bold;">Business</td>
        <td style="padding:8px;border-bottom:1px solid #eee;">{business_name}</td></tr>
    <tr><td style="padding:8px;border-bottom:1px solid #eee;font-weight:bold;">Agent Name</td>
        <td style="padding:8px;border-bottom:1px solid #eee;">{agent_name}</td></tr>
    <tr><td style="padding:8px;border-bottom:1px solid #eee;font-weight:bold;">Email</td>
        <td style="padding:8px;border-bottom:1px solid #eee;">{agent_email}</td></tr>
    <tr><td style="padding:8px;border-bottom:1px solid #eee;font-weight:bold;">Phone</td>
        <td style="padding:8px;border-bottom:1px solid #eee;">{agent_phone}</td></tr>
    <tr><td style="padding:8px;border-bottom:1px solid #eee;font-weight:bold;">Bolna Agent Created</td>
        <td style="padding:8px;border-bottom:1px solid #eee;">{'Yes: ' + bolna_agent_id if bolna_agent_id else 'No'}</td></tr>
    <tr><td style="padding:8px;border-bottom:1px solid #eee;font-weight:bold;">Phone Assigned</td>
        <td style="padding:8px;border-bottom:1px solid #eee;">{phone_line}</td></tr>
    <tr><td style="padding:8px;border-bottom:1px solid #eee;font-weight:bold;">Client ID</td>
        <td style="padding:8px;border-bottom:1px solid #eee;font-family:monospace;">{client_id}</td></tr>
    <tr><td style="padding:8px;font-weight:bold;">Setup Status</td>
        <td style="padding:8px;">{setup_status}</td></tr>
  </table>
  <p style="margin-top:16px;color:#999;font-size:12px;">PropBot Admin: {settings.BASE_URL}/admin</p>
</div>"""
        await asyncio.to_thread(
            _send_email,
            to=settings.SMTP_EMAIL,
            subject=f"New PropBot Signup — {business_name}",
            body=body,
        )
        logger.info("Founder signup alert sent for %s", business_name)
    except Exception as e:
        logger.warning("Founder signup alert failed: %s", e)


async def update_voice_agent(client_id: str) -> None:
    """
    Update an existing Bolna agent when client changes settings or KB.

    Rebuilds system prompt from scratch and pushes to Bolna.
    """
    db = get_supabase()
    result = db.table("clients").select("*").eq("id", client_id).single().execute()
    client = result.data

    agent_id = client.get("bolna_agent_id") or client.get("vapi_assistant_id")
    if not agent_id:
        logger.warning("No voice agent for client %s, provisioning new one", client_id)
        await provision_voice_agent(client_id)
        return

    persona = client.get("assistant_persona_name", "Priya")
    kb = client.get("knowledge_base", "")
    lang_pref = client.get("language_preference", "hi,en")

    system_prompt = build_system_prompt_from_config(
        business_name=client["business_name"],
        agent_name=client["agent_name"],
        persona_name=persona,
        knowledge_base=kb,
        channel="voice",
    )

    first_message = client.get("first_message") or (
        f"Namaste! {client['business_name']} mein aapka swagat hai. "
        f"Main {persona} bol rahi hoon. Boliye, kaise madad kar sakti hoon?"
    )

    config = AgentConfig(
        agent_name=f"{persona} - {client['business_name']}",
        first_message=first_message,
        system_prompt=system_prompt,
        voice_id=client.get("voice_id", ""),
        language_hints=lang_pref.split(","),
        tools=VOICE_TOOLS,
        webhook_url=f"{settings.BASE_URL}/api/webhooks/voice",
        client_id=client_id,
        telephony_number=client.get("vobiz_number", ""),
    )

    engine = get_voice_engine()
    await engine.update_agent(agent_id, config)
    logger.info("Voice agent updated for %s", client["business_name"])
