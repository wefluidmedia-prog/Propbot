"""
Seed the Sharma Properties demo client.

Quick script to create the demo without CLI arguments.
Uses default values for the demo.

Usage:
    python scripts/seed_demo.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.db.supabase_client import init_supabase, get_supabase


async def seed():
    print("Seeding Sharma Properties demo client...")

    init_supabase(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    db = get_supabase()

    # Load KB
    kb_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "knowledge_bases",
        "sharma_properties.md",
    )
    with open(kb_path, encoding="utf-8") as f:
        kb_content = f.read()

    # Check if demo client already exists
    existing = db.table("clients").select("id").eq("business_name", "Sharma Properties").execute()
    if existing.data:
        print(f"Demo client already exists: {existing.data[0]['id']}")
        print("Delete it first if you want to re-seed.")
        return

    # Create client (without voice agent — that requires API keys)
    client_data = {
        "business_name": "Sharma Properties",
        "agent_name": "Rahul Sharma",
        "agent_email": "rahul@sharmaproperties.in",
        "agent_phone": "+919876543210",
        "knowledge_base": kb_content,
        "assistant_persona_name": "Priya",
        "first_message": "Namaste! Sharma Properties mein aapka swagat hai. Main Priya hoon, aapki kya madad kar sakti hoon?",
        "subscription_status": "trial",
    }
    result = db.table("clients").insert(client_data).execute()
    client_id = result.data[0]["id"]

    print(f"\nDemo client created!")
    print(f"  Client ID: {client_id}")
    print(f"  Business:  Sharma Properties")
    print(f"\nUse this client_id in widget/demo.html and for testing.")
    print(f"\nTo add voice agent, run:")
    print(f"  python scripts/onboard_client.py \\")
    print(f'    --business-name "Sharma Properties" \\')
    print(f'    --agent-name "Rahul Sharma" \\')
    print(f'    --agent-email "rahul@sharmaproperties.in" \\')
    print(f'    --agent-phone "+919876543210" \\')
    print(f'    --kb-file "knowledge_bases/sharma_properties.md"')


if __name__ == "__main__":
    asyncio.run(seed())
