"""
System prompt builder.

Assembles the final system prompt from:
1. Priya persona template (priya_template.txt)
2. Client config from Supabase (business name, agent name, persona)
3. Knowledge base markdown
4. Channel-specific instructions (voice vs chat)
"""

import os
from app.db.supabase_client import get_supabase

_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "priya_template.txt")

CHANNEL_INSTRUCTIONS = {
    "voice": (
        "## VOICE CHANNEL INSTRUCTIONS\n"
        "- Keep every response to 2-3 sentences maximum. NEVER give long paragraphs.\n"
        "- If the caller starts speaking while you are talking, STOP IMMEDIATELY mid-sentence. Do NOT finish your thought. Wait for them to finish, then respond to what THEY said — not what you were saying before.\n"
        "- When you hear words like 'ruko', 'suniye', 'wait', 'hold on', 'ek minute', 'let me speak', 'suno' — STOP TALKING INSTANTLY and say only 'Ji, boliye' then WAIT silently for them to speak.\n"
        "- Pause naturally between ideas — the caller needs time to process\n"
        "- Never list more than 2 items at once; offer to continue if there are more\n"
        "- Spell out numbers naturally: say 'pachpan lakh' not '55,00,000'\n"
        "- When the caller is dictating a phone number, be COMPLETELY SILENT until they finish. Then repeat the full number back to confirm.\n"
        "- If the caller is silent for a few seconds, gently prompt: 'Aur kuch jaanna hai?'"
    ),
    "chat": (
        "## CHAT CHANNEL INSTRUCTIONS\n"
        "- You can use slightly longer responses than voice\n"
        "- Use line breaks for readability\n"
        "- You may list up to 5 items\n"
        "- When the visitor seems interested, suggest: 'Agar aap chahein toh humara agent "
        "aapko call kar sakta hai — Request Callback button use karein'\n"
        "- Include property prices and key details inline"
    ),
}


def _load_template() -> str:
    """Load the prompt template file."""
    with open(_TEMPLATE_PATH, encoding="utf-8") as f:
        return f.read()


def build_system_prompt(
    client_id: str,
    knowledge_base: str,
    channel: str = "voice",
) -> str:
    """
    Build the complete system prompt for a client + channel.

    Args:
        client_id: UUID of the client in Supabase
        knowledge_base: Markdown KB content (already loaded)
        channel: "voice" or "chat" — changes response length/style instructions
    """
    db = get_supabase()
    result = db.table("clients").select("*").eq("id", client_id).single().execute()
    client = result.data

    template = _load_template()
    channel_instructions = CHANNEL_INSTRUCTIONS.get(channel, "")

    return template.format(
        persona_name=client.get("assistant_persona_name", "Priya"),
        business_name=client["business_name"],
        agent_name=client["agent_name"],
        knowledge_base=knowledge_base,
        channel_instructions=channel_instructions,
    )


def build_system_prompt_from_config(
    business_name: str,
    agent_name: str,
    persona_name: str,
    knowledge_base: str,
    channel: str = "voice",
) -> str:
    """
    Build system prompt without a DB lookup — used during onboarding
    before the client record has all fields populated.
    """
    template = _load_template()
    channel_instructions = CHANNEL_INSTRUCTIONS.get(channel, "")

    return template.format(
        persona_name=persona_name,
        business_name=business_name,
        agent_name=agent_name,
        knowledge_base=knowledge_base,
        channel_instructions=channel_instructions,
    )
