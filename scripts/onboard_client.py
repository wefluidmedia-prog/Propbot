"""
Manual client onboarding script.

Creates a complete client setup in under 30 minutes:
1. Creates client record in Supabase
2. Stores the knowledge base
3. Builds the system prompt
4. Creates a Bolna/Vapi voice agent
5. Prints the chat widget embed code + test instructions

Usage:
    python scripts/onboard_client.py \
        --business-name "Sharma Properties" \
        --agent-name "Rahul Sharma" \
        --agent-email "rahul@sharma.com" \
        --agent-phone "+919876543210" \
        --kb-file "knowledge_bases/sharma_properties.md" \
        --phone-number "+911234567890" \
        --voice-id "YOUR_ELEVENLABS_VOICE_ID"
"""

import argparse
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.db.supabase_client import init_supabase, get_supabase
from app.voice.factory import get_voice_engine
from app.voice.base import AgentConfig, VOICE_TOOLS
from app.prompts.system_prompt import build_system_prompt_from_config
from app.auth import create_api_key


async def onboard(args):
    # Initialize Supabase
    print("[1/6] Connecting to Supabase...")
    init_supabase(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    db = get_supabase()

    # Read knowledge base
    print(f"[2/6] Loading knowledge base from {args.kb_file}...")
    with open(args.kb_file, encoding="utf-8") as f:
        kb_content = f.read()
    print(f"       KB loaded: {len(kb_content)} characters")

    # Create client record
    print("[3/6] Creating client record...")
    client_data = {
        "business_name": args.business_name,
        "agent_name": args.agent_name,
        "agent_email": args.agent_email,
        "agent_phone": args.agent_phone,
        "vobiz_number": args.phone_number,
        "knowledge_base": kb_content,
        "assistant_persona_name": args.persona_name,
    }
    result = db.table("clients").insert(client_data).execute()
    client_id = result.data[0]["id"]
    print(f"       Client ID: {client_id}")

    # Build system prompt
    print("[4/6] Building system prompt...")
    system_prompt = build_system_prompt_from_config(
        business_name=args.business_name,
        agent_name=args.agent_name,
        persona_name=args.persona_name,
        knowledge_base=kb_content,
        channel="voice",
    )
    print(f"       Prompt length: {len(system_prompt)} characters")

    # Create voice agent
    print(f"[5/6] Creating {settings.VOICE_PROVIDER} voice agent...")
    engine = get_voice_engine()
    first_message = (
        f"Namaste! {args.business_name} mein aapka swagat hai. "
        f"Main {args.persona_name} hoon, aapki kya madad kar sakti hoon?"
    )

    config = AgentConfig(
        agent_name=f"{args.persona_name} - {args.business_name}",
        first_message=first_message,
        system_prompt=system_prompt,
        voice_id=args.voice_id,
        language_hints=["hi", "en"],
        tools=VOICE_TOOLS,
        webhook_url=f"{settings.BASE_URL}/api/webhooks/voice",
        client_id=client_id,
        telephony_number=args.phone_number,
    )

    handle = await engine.create_agent(config)
    print(f"       Agent ID: {handle.agent_id}")
    print(f"       Provider: {handle.provider}")

    # Update client with agent ID
    agent_id_field = (
        "bolna_agent_id" if handle.provider == "bolna" else "vapi_assistant_id"
    )
    db.table("clients").update({
        agent_id_field: handle.agent_id,
        "first_message": first_message,
    }).eq("id", client_id).execute()

    # Generate API key for this client
    print("[6/7] Generating API key...")
    raw_api_key = create_api_key(client_id, label="onboarding")
    print(f"       API Key: {raw_api_key}")
    print(f"       (Save this — it cannot be retrieved again!)")

    # Print summary
    print(f"\n[7/7] Setup complete!")
    print(f"\n{'='*60}")
    print(f"  CLIENT ONBOARDING COMPLETE")
    print(f"{'='*60}")
    print(f"  Client ID:      {client_id}")
    print(f"  Business:        {args.business_name}")
    print(f"  Agent:           {args.agent_name}")
    print(f"  Voice Provider:  {handle.provider}")
    print(f"  Agent ID:        {handle.agent_id}")
    print(f"  Phone Number:    {args.phone_number}")
    print(f"  Webhook URL:     {settings.BASE_URL}/api/webhooks/voice")
    print(f"{'='*60}")
    print(f"\n  CHAT WIDGET EMBED CODE:")
    print(f'  <script src="{settings.BASE_URL}/static/chat-widget.js"')
    print(f'          data-client-id="{client_id}"')
    print(f'          data-api-url="{settings.BASE_URL}"')
    print(f'          data-persona-name="{args.persona_name}"')
    print(f'          data-subtitle="Property Assistant"></script>')
    print(f"\n  API KEY (for leads dashboard):")
    print(f"  {raw_api_key}")
    print(f"{'='*60}")
    print(f"\n  NEXT STEPS:")
    print(f"  1. Test voice: Call {args.phone_number}")
    print(f"  2. Test chat:  Open widget/demo.html (update CLIENT_ID)")
    print(f"  3. Create Razorpay payment link: https://dashboard.razorpay.com/app/payment-links")
    print(f"     Amount: INR 5000, Description: '{args.business_name} - AI Receptionist Monthly'")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Onboard a new PropBot client")
    parser.add_argument("--business-name", required=True, help="e.g. 'Sharma Properties'")
    parser.add_argument("--agent-name", required=True, help="e.g. 'Rahul Sharma'")
    parser.add_argument("--agent-email", required=True)
    parser.add_argument("--agent-phone", required=True, help="e.g. '+919876543210'")
    parser.add_argument("--kb-file", required=True, help="Path to markdown KB file")
    parser.add_argument("--phone-number", default="", help="Vobiz virtual number")
    parser.add_argument("--voice-id", default="", help="ElevenLabs voice ID")
    parser.add_argument("--persona-name", default="Priya", help="AI persona name")
    args = parser.parse_args()

    asyncio.run(onboard(args))


if __name__ == "__main__":
    main()
