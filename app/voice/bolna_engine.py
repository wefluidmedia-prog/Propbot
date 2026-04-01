"""
Bolna.ai VoiceEngine implementation (primary provider).

Bolna is an Indian open-source voice AI platform (YC-backed) with:
- Native Hindi/Hinglish support (10+ Indian languages, 50+ accents)
- Built-in Exotel integration
- Claude support via LiteLLM/OpenRouter
- ~$0.06/min total cost (vs Vapi's $0.30/min)

API docs: https://docs.bolna.ai/
GitHub: https://github.com/bolna-ai/bolna
"""

import httpx
from app.voice.base import VoiceEngine, AgentConfig, AgentHandle, NormalizedEvent


class BolnaEngine(VoiceEngine):

    def __init__(self, api_key: str, api_url: str = "https://api.bolna.dev"):
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def create_agent(self, config: AgentConfig) -> AgentHandle:
        """Create a Bolna voice agent via their Agent API v2."""
        payload = self._build_agent_payload(config)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.api_url}/v2/agent",
                json=payload,
                headers=self.headers,
            )
            resp.raise_for_status()
            data = resp.json()

        return AgentHandle(
            provider="bolna",
            agent_id=data.get("agent_id", data.get("id", "")),
            phone_number=config.telephony_number,
            raw_config=data,
        )

    async def update_agent(self, agent_id: str, config: AgentConfig) -> AgentHandle:
        """Update an existing Bolna agent."""
        payload = self._build_agent_payload(config)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.put(
                f"{self.api_url}/v2/agent/{agent_id}",
                json=payload,
                headers=self.headers,
            )
            resp.raise_for_status()
            data = resp.json()

        return AgentHandle(
            provider="bolna",
            agent_id=agent_id,
            phone_number=config.telephony_number,
            raw_config=data,
        )

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete a Bolna agent."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.delete(
                f"{self.api_url}/v2/agent/{agent_id}",
                headers=self.headers,
            )
            return resp.status_code in (200, 204)

    async def get_agent(self, agent_id: str) -> dict:
        """Retrieve a Bolna agent's configuration."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.api_url}/v2/agent/{agent_id}",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    def parse_webhook(self, payload: dict) -> NormalizedEvent:
        """
        Normalize Bolna webhook payloads into NormalizedEvent.

        Bolna sends different event types:
        - "tool_call": when the agent invokes a tool
        - "call_ended" / "end_of_call": call completion with transcript
        - "call_started": call began
        """
        event_type = payload.get("type", payload.get("event", "unknown"))
        call_id = payload.get("call_id", payload.get("conversation_id", ""))
        metadata = payload.get("metadata", {})
        client_id = metadata.get("client_id", payload.get("client_id", ""))

        # Normalize event type names
        type_map = {
            "tool_call": "tool_call",
            "tool-calls": "tool_call",
            "function_call": "tool_call",
            "end_of_call": "call_ended",
            "end-of-call-report": "call_ended",
            "call_ended": "call_ended",
            "call_completed": "call_ended",
            "call_started": "call_started",
            "call-started": "call_started",
        }
        normalized_type = type_map.get(event_type, "unknown")

        event = NormalizedEvent(
            event_type=normalized_type,
            call_id=call_id,
            client_id=client_id,
            raw=payload,
        )

        if normalized_type == "tool_call":
            # Bolna may nest tool calls in different structures
            tool_calls_raw = payload.get("tool_calls", payload.get("function_calls", []))
            if not isinstance(tool_calls_raw, list):
                tool_calls_raw = [tool_calls_raw]

            event.tool_calls = []
            for tc in tool_calls_raw:
                event.tool_calls.append({
                    "name": tc.get("name", tc.get("function_name", "")),
                    "tool_call_id": tc.get("id", tc.get("tool_call_id", "")),
                    "parameters": tc.get("parameters", tc.get("arguments", {})),
                })

        elif normalized_type == "call_ended":
            event.transcript = payload.get("transcript", "")
            event.messages = payload.get("messages", [])
            event.recording_url = payload.get("recording_url", payload.get("recording", {}).get("url"))
            event.ended_reason = payload.get("ended_reason", payload.get("hangup_reason", ""))
            event.duration_seconds = payload.get("duration", payload.get("duration_seconds"))

        return event

    def build_tool_response(self, tool_call_id: str, result: str) -> dict:
        """Build Bolna-format tool call response."""
        return {
            "results": [
                {
                    "tool_call_id": tool_call_id,
                    "result": result,
                }
            ]
        }

    def _build_agent_payload(self, config: AgentConfig) -> dict:
        """Convert AgentConfig to Bolna API payload."""
        payload = {
            "agent_name": config.agent_name,
            "agent_welcome_message": config.first_message,
            "agent_type": "conversational",
            "tasks": [
                {
                    "task_type": "conversation",
                    "tools_config": {
                        "llm_agent": self._build_llm_config(config.system_prompt),
                        "synthesizer": {
                            "provider": "elevenlabs",
                            "voice_id": config.voice_id,
                            "model": "eleven_multilingual_v2",
                        },
                        "transcriber": {
                            "provider": "deepgram",
                            "model": "nova-2",
                            "language": "multi",
                            "keywords": config.language_hints,
                        },
                        "input": {
                            "provider": "exotel",
                            "format": "pcm",
                        },
                        "output": {
                            "provider": "exotel",
                            "format": "pcm",
                        },
                    },
                    "tools": self._convert_tools(config.tools, config.webhook_url),
                }
            ],
            "metadata": {
                "client_id": config.client_id,
                **(config.metadata or {}),
            },
        }

        if config.telephony_number:
            payload["telephony_provider"] = "exotel"
            payload["phone_number"] = config.telephony_number

        return payload

    def _build_llm_config(self, system_prompt: str) -> dict:
        """Build LLM config for Bolna — supports OpenAI or Claude via LiteLLM."""
        from app.config import settings

        if settings.LLM_PROVIDER.lower() == "openai":
            return {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "max_tokens": 500,
                "temperature": 0.4,
                "family": "openai",
                "agent_flow_type": "streaming",
                "system_prompt": system_prompt,
            }
        else:
            return {
                "provider": "openrouter",
                "model": "anthropic/claude-sonnet-4-20250514",
                "max_tokens": 500,
                "temperature": 0.4,
                "family": "anthropic",
                "agent_flow_type": "streaming",
                "system_prompt": system_prompt,
            }

    def _convert_tools(self, tools: list[dict], webhook_url: str) -> list[dict]:
        """Convert our agnostic tool definitions to Bolna's format."""
        from app.config import settings

        bolna_tools = []
        for tool in tools:
            tool_config = {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool.get("parameters", {}),
                "url": webhook_url,
                "method": "POST",
            }
            if settings.WEBHOOK_SECRET:
                tool_config["headers"] = {"X-Webhook-Secret": settings.WEBHOOK_SECRET}
            bolna_tools.append(tool_config)
        return bolna_tools
