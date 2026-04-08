"""
Bolna API diagnostic — run from project root:
    python test_bolna.py

Checks:
1. Lists existing agents
2. Creates a test agent with a catalog voice (Priya)
3. Deletes the test agent
"""
import asyncio
import os
import sys
import json

from dotenv import load_dotenv
load_dotenv()

BOLNA_API_KEY = os.getenv("BOLNA_API_KEY", "")
BOLNA_API_URL = os.getenv("BOLNA_API_URL", "https://api.bolna.dev").rstrip("/")

# Must be a voice registered in Bolna's voice_profiles (from our catalog)
PRIYA_VOICE_ID = "QTKSa2Iyv0yoxvXY2V8a"

if not BOLNA_API_KEY:
    print("ERROR: BOLNA_API_KEY not set in .env")
    sys.exit(1)

import httpx

HEADERS = {
    "Authorization": f"Bearer {BOLNA_API_KEY}",
    "Content-Type": "application/json",
}


async def test_list_agents():
    print("\n=== 1. List agents (GET /v2/agent) ===")
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(f"{BOLNA_API_URL}/v2/agent", headers=HEADERS)
        print(f"Status: {r.status_code}")
        if r.status_code == 405:
            print("(405 Method Not Allowed -- GET /v2/agent not supported, that is OK)")
        else:
            print(r.text[:400])


async def test_create_agent():
    print("\n=== 2. Create test agent (POST /v2/agent) ===")
    payload = {
        "agent_config": {
            "agent_name": "PropBot-DiagTest-DELETE-ME",
            "agent_welcome_message": "Namaste! Test agent only.",
            "agent_type": "conversational",
            "tasks": [{
                "task_type": "conversation",
                "tools_config": {
                    "llm_agent": {
                        "agent_type": "simple_llm_agent",
                        "agent_flow_type": "streaming",
                        "llm_config": {
                            "provider": "openai", "model": "gpt-4.1-mini",
                            "family": "openai", "max_tokens": 100,
                            "temperature": 0.3, "agent_flow_type": "streaming",
                            "system_prompt": "You are a diagnostic test assistant. Say hi.",
                        },
                    },
                    "synthesizer": {
                        "provider": "elevenlabs", "stream": True, "caching": True,
                        "audio_format": "wav",
                        "provider_config": {
                            "voice": PRIYA_VOICE_ID, "voice_id": PRIYA_VOICE_ID,
                            "model": "eleven_turbo_v2_5", "speed": 1.0,
                            "style": 0.4, "similarity_boost": 0.75,
                        },
                    },
                    "transcriber": {"provider": "deepgram", "model": "nova-2", "language": "hi"},
                    "input": {"provider": "vobiz", "format": "pcm"},
                    "output": {"provider": "vobiz", "format": "pcm"},
                },
                "tools": [],
                "toolchain": {"execution": "parallel", "pipelines": [["llm_agent", "synthesizer"]]},
            }],
        },
        "agent_prompts": {},
        "metadata": {"client_id": "diagnostic-test"},
    }

    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{BOLNA_API_URL}/v2/agent", json=payload, headers=HEADERS)
        print(f"Status: {r.status_code}")
        data = r.json()
        print(json.dumps(data, indent=2))
        agent_id = data.get("agent_id") or data.get("id")
        if agent_id:
            print(f"\nSUCCESS: agent_id={agent_id}")
            return agent_id
        else:
            print("\nFAIL: No agent_id returned")
            return None


async def test_delete_agent(agent_id: str):
    print(f"\n=== 3. Delete test agent {agent_id} ===")
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.delete(f"{BOLNA_API_URL}/v2/agent/{agent_id}", headers=HEADERS)
        print(f"Status: {r.status_code} -- {'deleted OK' if r.status_code in (200, 204) else r.text[:200]}")


async def main():
    print(f"URL: {BOLNA_API_URL}")
    print(f"Key: {BOLNA_API_KEY[:12]}...{BOLNA_API_KEY[-4:]}")
    print(f"Test voice: {PRIYA_VOICE_ID}")

    await test_list_agents()
    agent_id = await test_create_agent()
    if agent_id:
        await test_delete_agent(agent_id)
    else:
        print("\nDIAGNOSIS: Agent creation failed -- see error above.")
        print("Common causes:")
        print("  - Empty voice_id (client never picked a voice -- now fixed with default fallback)")
        print("  - Invalid voice_id (not registered in Bolna voice_profiles)")
        print("  - Bad API key")


asyncio.run(main())
