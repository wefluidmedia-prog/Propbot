"""
LLM service for the chat widget.

Supports OpenAI (gpt-4o-mini) and Anthropic (Claude) — controlled by LLM_PROVIDER env var.
Voice calls go through Bolna/Vapi (which handle their own LLM calls).
Chat widget messages call the LLM directly from our backend.
"""

import asyncio
import uuid
from functools import lru_cache

from app.config import settings
from app.services.knowledge_service import get_knowledge_base
from app.prompts.system_prompt import build_system_prompt


@lru_cache(maxsize=1)
def _get_openai_client():
    from openai import AsyncOpenAI
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


@lru_cache(maxsize=1)
def _get_anthropic_client():
    from anthropic import AsyncAnthropic
    return AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


def _load_chat_context(client_id: str, channel: str) -> str:
    """Load KB and build system prompt (sync — run via to_thread)."""
    from app.db.supabase_client import get_supabase
    db = get_supabase()
    result = db.table("clients").select("*").eq("id", client_id).single().execute()
    client = result.data
    kb = client.get("knowledge_base", "")
    return build_system_prompt(client_id=client_id, knowledge_base=kb, channel=channel)


async def get_chat_response(
    client_id: str,
    message: str,
    conversation_history: list[dict],
    visitor_id: str | None = None,
) -> dict:
    """
    Generate a chat response using OpenAI or Anthropic.

    Set LLM_PROVIDER in .env:
      - "openai"    → GPT-4o-mini (cheaper, good multilingual)
      - "anthropic"  → Claude Sonnet (better reasoning)
    """
    if not visitor_id:
        visitor_id = str(uuid.uuid4())

    # Supabase SDK is sync — offload DB + prompt assembly off the event loop
    system = await asyncio.to_thread(_load_chat_context, client_id, "chat")

    # Build message list
    messages = []
    for msg in conversation_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": message})

    provider = settings.LLM_PROVIDER.lower()

    if provider == "openai":
        text = await _call_openai(system, messages)
    elif provider == "anthropic":
        text = await _call_anthropic(system, messages)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: '{provider}'. Use 'openai' or 'anthropic'.")

    return {"text": text, "visitor_id": visitor_id}


async def _call_openai(system: str, messages: list[dict]) -> str:
    """Call OpenAI GPT-4o-mini for chat responses."""
    client = _get_openai_client()

    oai_messages = [{"role": "system", "content": system}]
    oai_messages.extend(messages)

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=oai_messages,
        max_tokens=500,
        temperature=0.4,
    )
    return response.choices[0].message.content


async def _call_anthropic(system: str, messages: list[dict]) -> str:
    """Call Claude Sonnet for chat responses."""
    client = _get_anthropic_client()
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=system,
        messages=messages,
    )
    return response.content[0].text
