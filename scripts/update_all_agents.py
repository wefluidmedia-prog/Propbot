"""
Update all existing Bolna voice agents to push the latest tool definitions.

Run this once after adding the book_viewing tool to VOICE_TOOLS:
    python scripts/update_all_agents.py
"""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.WARNING)


async def main():
    from app.db.supabase_client import init_supabase, get_supabase
    from app.services.onboarding_service import update_voice_agent

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment or .env")
        sys.exit(1)

    init_supabase(supabase_url, supabase_key)
    db = get_supabase()

    result = db.table("clients").select("id, business_name").not_.is_("bolna_agent_id", "null").execute()
    clients = result.data or []

    print(f"Updating {len(clients)} agents...")
    success = 0
    for client in clients:
        try:
            await update_voice_agent(client["id"])
            print(f"  ✓ {client['business_name']}")
            success += 1
        except Exception as e:
            print(f"  ✗ {client['business_name']}: {e}")

    print(f"\nDone. {success}/{len(clients)} agents updated.")


if __name__ == "__main__":
    asyncio.run(main())
