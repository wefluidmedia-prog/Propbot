"""
Pipecat VoiceEngine stub (future self-hosted option).

Pipecat is an open-source Python framework for real-time voice AI.
It gives full control over the STT → LLM → TTS pipeline and
eliminates per-minute platform fees, but requires self-hosting.

Implement this when you're ready to self-host for cost savings.
GitHub: https://github.com/pipecat-ai/pipecat
"""

from app.voice.base import VoiceEngine, AgentConfig, AgentHandle, NormalizedEvent


class PipecatEngine(VoiceEngine):

    async def create_agent(self, config: AgentConfig) -> AgentHandle:
        raise NotImplementedError(
            "Pipecat engine not implemented yet. "
            "Use VOICE_PROVIDER=bolna (primary) or VOICE_PROVIDER=vapi (fallback)."
        )

    async def update_agent(self, agent_id: str, config: AgentConfig) -> AgentHandle:
        raise NotImplementedError("Pipecat engine not implemented yet.")

    async def delete_agent(self, agent_id: str) -> bool:
        raise NotImplementedError("Pipecat engine not implemented yet.")

    async def get_agent(self, agent_id: str) -> dict:
        raise NotImplementedError("Pipecat engine not implemented yet.")

    def parse_webhook(self, payload: dict) -> NormalizedEvent:
        raise NotImplementedError("Pipecat engine not implemented yet.")

    def build_tool_response(self, tool_call_id: str, result: str) -> dict:
        raise NotImplementedError("Pipecat engine not implemented yet.")
