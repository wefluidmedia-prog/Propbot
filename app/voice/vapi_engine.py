"""
Vapi.ai VoiceEngine implementation (fallback provider).

Vapi is a managed voice AI platform. More mature than Bolna but
costs ~$0.30/min (5x more). Kept as a working fallback — switch to
it by setting VOICE_PROVIDER=vapi in .env.

API docs: https://docs.vapi.ai/
"""

import httpx
from app.voice.base import VoiceEngine, AgentConfig, AgentHandle, NormalizedEvent

VAPI_BASE_URL = "https://api.vapi.ai"


class VapiEngine(VoiceEngine):

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def create_agent(self, config: AgentConfig) -> AgentHandle:
        """Create a Vapi assistant."""
        payload = {
            "name": config.agent_name,
            "firstMessage": config.first_message,
            "model": {
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "messages": [{"role": "system", "content": config.system_prompt}],
                "temperature": 0.4,
                "tools": self._convert_tools(config.tools),
            },
            "voice": {
                "provider": "11labs",
                "voiceId": config.voice_id,
            },
            "transcriber": {
                "provider": "deepgram",
                "model": "nova-2",
                "language": "multi",
            },
            "serverUrl": config.webhook_url,
            "metadata": {"client_id": config.client_id},
            "silenceTimeoutSeconds": 30,
            "maxDurationSeconds": 300,
            "endCallMessage": "Dhanyavaad! Agent sahab aapse jald contact karenge. Aapka din shubh ho!",
        }
        payload.update(config.metadata)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{VAPI_BASE_URL}/assistant",
                json=payload,
                headers=self.headers,
            )
            resp.raise_for_status()
            data = resp.json()

        return AgentHandle(
            provider="vapi",
            agent_id=data["id"],
            phone_number=None,
            raw_config=data,
        )

    async def update_agent(self, agent_id: str, config: AgentConfig) -> AgentHandle:
        """Update a Vapi assistant."""
        payload = {
            "name": config.agent_name,
            "firstMessage": config.first_message,
            "model": {
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "messages": [{"role": "system", "content": config.system_prompt}],
                "temperature": 0.4,
                "tools": self._convert_tools(config.tools),
            },
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.patch(
                f"{VAPI_BASE_URL}/assistant/{agent_id}",
                json=payload,
                headers=self.headers,
            )
            resp.raise_for_status()
            data = resp.json()

        return AgentHandle(
            provider="vapi",
            agent_id=agent_id,
            raw_config=data,
        )

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete a Vapi assistant."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.delete(
                f"{VAPI_BASE_URL}/assistant/{agent_id}",
                headers=self.headers,
            )
            return resp.status_code in (200, 204)

    async def get_agent(self, agent_id: str) -> dict:
        """Get a Vapi assistant's config."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{VAPI_BASE_URL}/assistant/{agent_id}",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    def parse_webhook(self, payload: dict) -> NormalizedEvent:
        """Normalize Vapi webhook payloads."""
        msg = payload.get("message", {})
        event_type = msg.get("type", "unknown")
        call_obj = msg.get("call", {})
        call_id = call_obj.get("id", "")
        client_id = call_obj.get("metadata", {}).get("client_id", "")

        type_map = {
            "tool-calls": "tool_call",
            "end-of-call-report": "call_ended",
            "status-update": "call_started" if msg.get("status") == "in-progress" else "unknown",
            "assistant-request": "assistant_request",
        }
        normalized_type = type_map.get(event_type, "unknown")

        event = NormalizedEvent(
            event_type=normalized_type,
            call_id=call_id,
            client_id=client_id,
            raw=payload,
        )

        if normalized_type == "tool_call":
            event.tool_calls = []
            for t in msg.get("toolWithToolCallList", []):
                tc = t.get("toolCall", {})
                event.tool_calls.append({
                    "name": t.get("function", {}).get("name", ""),
                    "tool_call_id": tc.get("id", ""),
                    "parameters": tc.get("parameters", {}),
                })

        elif normalized_type == "call_ended":
            artifact = msg.get("artifact", {})
            event.transcript = artifact.get("transcript", "")
            event.messages = artifact.get("messages", [])
            event.recording_url = artifact.get("recording", {}).get("url") if isinstance(artifact.get("recording"), dict) else None
            event.ended_reason = msg.get("endedReason", "")

        return event

    def build_tool_response(self, tool_call_id: str, result: str) -> dict:
        """Build Vapi-format tool response."""
        return {
            "results": [
                {
                    "toolCallId": tool_call_id,
                    "result": result,
                }
            ]
        }

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        """Convert agnostic tools to Vapi format."""
        vapi_tools = []
        for tool in tools:
            vapi_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
                },
            })
        return vapi_tools
