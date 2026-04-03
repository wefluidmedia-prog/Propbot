"""
Client onboarding service — provisions voice agents automatically.

Extracted from scripts/onboard_client.py for use by the signup wizard.
"""

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
        telephony_number=client.get("exotel_number", ""),
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

    # Assign phone number from pool and bind to Bolna agent
    from app.services.phone_service import assign_phone_number
    phone_number = await assign_phone_number(client_id)
    if phone_number:
        # Update Bolna agent with the phone number
        config.telephony_number = phone_number
        await engine.update_agent(handle.agent_id, config)
        db.table("clients").update({"setup_status": "ready"}).eq("id", client_id).execute()
        logger.info("Phone %s assigned and bound to agent for %s", phone_number, business)
    else:
        db.table("clients").update({"setup_status": "failed"}).eq("id", client_id).execute()
        logger.critical("No phone numbers available for client %s", client_id)

    # Generate API key
    raw_key = create_api_key(client_id, label="signup")
    logger.info("API key generated for %s", business)

    return handle.agent_id


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
        telephony_number=client.get("exotel_number", ""),
    )

    engine = get_voice_engine()
    await engine.update_agent(agent_id, config)
    logger.info("Voice agent updated for %s", client["business_name"])
