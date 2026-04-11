"""
Bolna.ai VoiceEngine implementation (primary provider).

Bolna is an Indian open-source voice AI platform (YC-backed) with:
- Native Hindi/Hinglish support (10+ Indian languages, 50+ accents)
- Built-in Vobiz integration
- Claude support via LiteLLM/OpenRouter
- ~$0.06/min total cost (vs Vapi's $0.30/min)

API docs: https://docs.bolna.ai/
GitHub: https://github.com/bolna-ai/bolna
"""

import logging

import httpx
from app.voice.base import VoiceEngine, AgentConfig, AgentHandle, NormalizedEvent

logger = logging.getLogger(__name__)


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
            if not resp.is_success:
                logger.error(
                    "Bolna create_agent failed: status=%s body=%s payload_voice=%s",
                    resp.status_code,
                    resp.text[:500],
                    payload.get("agent_config", {})
                        .get("tasks", [{}])[0]
                        .get("tools_config", {})
                        .get("synthesizer", {})
                        .get("provider_config", {})
                        .get("voice_id", "MISSING"),
                )
            resp.raise_for_status()
            data = resp.json()

        agent_id = data.get("agent_id") or data.get("id") or ""
        if not agent_id:
            logger.error("Bolna create_agent returned no agent_id: %s", data)
            raise ValueError(f"Bolna returned no agent_id: {data}")

        handle = AgentHandle(
            provider="bolna",
            agent_id=agent_id,
            phone_number=config.telephony_number,
            raw_config=data,
        )
        logger.info(
            "Bolna agent created: id=%s voice=%s phone=%s",
            handle.agent_id,
            payload.get("agent_config", {})
                .get("tasks", [{}])[0]
                .get("tools_config", {})
                .get("synthesizer", {})
                .get("provider_config", {})
                .get("voice_id", "default"),
            config.telephony_number or "none",
        )
        return handle

    async def update_agent(self, agent_id: str, config: AgentConfig) -> AgentHandle:
        """Update an existing Bolna agent."""
        payload = self._build_agent_payload(config)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.put(
                f"{self.api_url}/v2/agent/{agent_id}",
                json=payload,
                headers=self.headers,
            )
            if not resp.is_success:
                logger.error(
                    "Bolna update_agent failed: agent_id=%s status=%s body=%s",
                    agent_id, resp.status_code, resp.text[:500],
                )
            resp.raise_for_status()
            data = resp.json()

        handle = AgentHandle(
            provider="bolna",
            agent_id=agent_id,
            phone_number=config.telephony_number,
            raw_config=data,
        )
        logger.info(
            "Bolna agent updated: id=%s telephony_provider=%s phone_number=%s",
            agent_id,
            payload.get("agent_config", {}).get("telephony_provider", "none"),
            config.telephony_number or "none",
        )
        return handle

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

    async def trigger_outbound_call(
        self,
        agent_id: str,
        recipient_phone: str,
        from_phone: str = "",
    ) -> dict:
        """
        Trigger an outbound call via Bolna.

        Bolna API: POST /call
        Required: agent_id, recipient_phone_number (E.164 format e.g. +919876543210)
        Optional: from_phone_number (override the number pool assignment)

        Returns Bolna response: {"message": "done", "status": "queued", "execution_id": "..."}
        """
        payload: dict = {
            "agent_id": agent_id,
            "recipient_phone_number": recipient_phone,
        }
        if from_phone:
            payload["from_phone_number"] = from_phone

        logger.info(
            "Triggering outbound call: agent_id=%s recipient=%s",
            agent_id,
            recipient_phone,
        )

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.api_url}/call",
                json=payload,
                headers=self.headers,
            )
            data = resp.json()

        logger.info(
            "Outbound call response: status=%s execution_id=%s",
            data.get("status"),
            data.get("execution_id"),
        )
        return data

    async def get_call_details(self, call_id: str) -> dict | None:
        """
        Fetch call details (recording URL, transcript) from Bolna API.

        Tries GET /call/{call_id} — returns dict with recording_url/transcript
        or None if unavailable.
        """
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.api_url}/call/{call_id}",
                    headers=self.headers,
                )
                if resp.is_success:
                    data = resp.json()
                    return {
                        "recording_url": data.get("recording_url", data.get("recording", {}).get("url")),
                        "transcript": data.get("transcript", ""),
                    }
                logger.warning("Bolna get_call_details: status=%s for call_id=%s", resp.status_code, call_id)
        except Exception as e:
            logger.warning("Bolna get_call_details failed for call_id=%s: %s", call_id, e)
        return None

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

    # Default voice (Priya) — used when client hasn't selected a voice yet.
    # Must be a voice_id registered in Bolna's voice_profiles.
    DEFAULT_VOICE_ID = "QTKSa2Iyv0yoxvXY2V8a"

    def _build_agent_payload(self, config: AgentConfig) -> dict:
        """Convert AgentConfig to Bolna API v2 payload."""
        # Bolna rejects empty voice_ids — fall back to default (Priya)
        voice_id = config.voice_id or self.DEFAULT_VOICE_ID

        agent_config = {
            "agent_name": config.agent_name,
            "agent_welcome_message": config.first_message,
            "agent_type": "conversational",
            "tasks": [
                {
                    "task_type": "conversation",
                    "task_config": {
                        "number_of_words_for_interruption": 3,
                        "interruption_backoff_period": 150,
                        "hangup_after_silence": 10,
                        "call_hangup_message": "Bye!",
                        "incremental_delay": 200,
                        "optimize_latency": True,
                        "check_if_user_online": True,
                        "trigger_user_online_message_after": 20,
                    },
                    "tools_config": {
                        "llm_agent": self._build_llm_config(config.system_prompt),
                        "synthesizer": {
                            "provider": "elevenlabs",
                            "stream": True,
                            "caching": True,
                            "audio_format": "wav",
                            "provider_config": {
                                "voice": voice_id,
                                "voice_id": voice_id,
                                "model": "eleven_turbo_v2_5",
                                "speed": 1.0,
                                "style": 0.4,
                                "similarity_boost": 0.75,
                            },
                        },
                        "transcriber": {
                            "provider": "deepgram",
                            "model": "nova-2",
                            "language": config.language_hints[0] if config.language_hints else "hi",
                            "keywords": ", ".join(config.language_hints),
                            "endpointing": 250,
                        },
                        "input": {
                            "provider": "vobiz",
                            "format": "pcm",
                        },
                        "output": {
                            "provider": "vobiz",
                            "format": "pcm",
                        },
                    },
                    "tools": self._convert_tools(config.tools, config.webhook_url),
                    "toolchain": {
                        "execution": "parallel",
                        "pipelines": [["llm_agent", "synthesizer"]],
                    },
                }
            ],
        }

        if config.telephony_number:
            agent_config["telephony_provider"] = "vobiz"
            agent_config["phone_number"] = config.telephony_number

        return {
            "agent_config": agent_config,
            "agent_prompts": {},
            "metadata": {
                "client_id": config.client_id,
                **(config.metadata or {}),
            },
        }

    def _build_llm_config(self, system_prompt: str) -> dict:
        """Build LLM agent config for Bolna v2 API."""
        return {
            "agent_type": "simple_llm_agent",
            "agent_flow_type": "streaming",
            "llm_config": {
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "family": "openai",
                "max_tokens": 400,
                "temperature": 0.35,
                "agent_flow_type": "streaming",
                "system_prompt": system_prompt,
            },
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
