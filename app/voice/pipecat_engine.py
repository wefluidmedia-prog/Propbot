"""
Pipecat VoiceEngine — self-hosted voice pipeline.

Creating an agent stores its config locally; the Pipecat worker process
fetches it when an inbound call arrives via the SIP trunk (Vobiz).
"""

import logging
import uuid
from dataclasses import asdict

from app.voice.base import VoiceEngine, AgentConfig, AgentHandle, NormalizedEvent

logger = logging.getLogger(__name__)


class PipecatEngine(VoiceEngine):

    async def create_agent(self, config: AgentConfig) -> AgentHandle:
        agent_id = f"pc_{uuid.uuid4().hex[:12]}"
        handle = AgentHandle(
            provider="pipecat",
            agent_id=agent_id,
            phone_number=config.telephony_number,
            raw_config=asdict(config),
        )
        logger.info(f"Pipecat agent registered: id={agent_id} phone={config.telephony_number}")
        return handle

    async def update_agent(self, agent_id: str, config: AgentConfig) -> AgentHandle:
        logger.info(f"Pipecat agent updated: id={agent_id}")
        return AgentHandle(
            provider="pipecat",
            agent_id=agent_id,
            phone_number=config.telephony_number,
            raw_config=asdict(config),
        )

    async def delete_agent(self, agent_id: str) -> bool:
        logger.info(f"Pipecat agent deleted: id={agent_id}")
        return True

    async def get_agent(self, agent_id: str) -> dict:
        return {"agent_id": agent_id, "status": "active"}

    def parse_webhook(self, payload: dict) -> NormalizedEvent:
        event_type = payload.get("type", "unknown")
        call_id = payload.get("call_id", "")
        client_id = payload.get("client_id", "")
        
        event = NormalizedEvent(
            event_type=event_type,
            call_id=call_id,
            client_id=client_id,
            raw=payload,
        )

        if event_type == "tool_call":
            event.tool_calls = payload.get("tool_calls", [])
        elif event_type == "call_ended":
            event.transcript = payload.get("transcript", "")
            event.messages = payload.get("messages", [])
            event.recording_url = payload.get("recording_url")
            event.ended_reason = payload.get("ended_reason", "")
            event.duration_seconds = payload.get("duration_seconds", 0)

        return event

    def build_tool_response(self, tool_call_id: str, result: str) -> dict:
        return {
            "results": [
                {
                    "tool_call_id": tool_call_id,
                    "result": result,
                }
            ]
        }
