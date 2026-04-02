"""
Update Bolna agent voice tuning parameters.

Usage:
    python scripts/update_bolna_tuning.py --agent-id <AGENT_ID>

Reads BOLNA_API_KEY from environment or .env file.
"""

import argparse
import copy
import json
import os
import sys

import httpx

# Load from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BOLNA_API_KEY = os.environ.get("BOLNA_API_KEY", "")
BOLNA_API_URL = os.environ.get("BOLNA_API_URL", "https://api.bolna.dev")


def main():
    parser = argparse.ArgumentParser(description="Update Bolna agent voice tuning")
    parser.add_argument("--agent-id", required=True, help="Bolna agent UUID")
    parser.add_argument("--words-for-interruption", type=int, default=6)
    parser.add_argument("--interruption-backoff", type=int, default=250)
    parser.add_argument("--endpointing", type=int, default=350)
    parser.add_argument("--hangup-after-silence", type=int, default=15)
    parser.add_argument("--hangup-message", default="Bye!")
    args = parser.parse_args()

    if not BOLNA_API_KEY:
        print("ERROR: BOLNA_API_KEY not set. Set it in .env or environment.", file=sys.stderr)
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {BOLNA_API_KEY}",
        "Content-Type": "application/json",
    }

    # Fetch current config
    print(f"Fetching agent {args.agent_id}...")
    resp = httpx.get(f"{BOLNA_API_URL}/v2/agent/{args.agent_id}", headers=headers, timeout=30)
    resp.raise_for_status()
    current = resp.json()
    print(f"Agent: {current['agent_name']}")

    # Apply tuning
    updated_tasks = copy.deepcopy(current["tasks"])
    tc = updated_tasks[0]["task_config"]
    tc["number_of_words_for_interruption"] = args.words_for_interruption
    tc["interruption_backoff_period"] = args.interruption_backoff
    tc["hangup_after_silence"] = args.hangup_after_silence
    tc["call_hangup_message"] = args.hangup_message
    updated_tasks[0]["tools_config"]["transcriber"]["endpointing"] = args.endpointing

    payload = {
        "agent_config": {
            "agent_name": current["agent_name"],
            "agent_type": current.get("agent_type", "other"),
            "agent_welcome_message": current.get("agent_welcome_message", ""),
            "tasks": updated_tasks,
        },
        "agent_prompts": current.get("agent_prompts", {}),
    }

    print("Updating...")
    resp = httpx.put(f"{BOLNA_API_URL}/v2/agent/{args.agent_id}", json=payload, headers=headers, timeout=30)
    if resp.status_code == 200:
        print("Success!")
        v = resp.json() if resp.text else {}
        # Verify
        resp2 = httpx.get(f"{BOLNA_API_URL}/v2/agent/{args.agent_id}", headers=headers, timeout=30)
        v = resp2.json()
        vtc = v["tasks"][0]["task_config"]
        vtr = v["tasks"][0]["tools_config"]["transcriber"]
        print(f"  words_for_interruption: {vtc['number_of_words_for_interruption']}")
        print(f"  interruption_backoff: {vtc['interruption_backoff_period']}")
        print(f"  endpointing: {vtr['endpointing']}")
        print(f"  hangup_after_silence: {vtc['hangup_after_silence']}")
        print(f"  call_hangup_message: {vtc['call_hangup_message']}")
    else:
        print(f"Failed ({resp.status_code}): {resp.text[:500]}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
