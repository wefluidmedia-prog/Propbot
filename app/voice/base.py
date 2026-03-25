"""
VoiceEngine abstraction layer.

This is the core interface that allows swapping voice AI providers
(Bolna, Vapi, Pipecat) with a single config change: VOICE_PROVIDER env var.

All downstream code (webhooks, lead capture, alerts) depends only on
this interface and the normalized data classes below — never on
provider-specific APIs directly.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AgentConfig:
    """Provider-agnostic voice agent configuration."""
    agent_name: str                          # "Priya - Sharma Properties"
    first_message: str                       # Greeting spoken at call start
    system_prompt: str                       # Full system prompt with KB embedded
    voice_id: str                            # Provider-specific voice identifier
    language_hints: list[str]                # ["hi", "en"] for Hindi + English
    tools: list[dict]                        # Tool definitions (see VOICE_TOOLS)
    webhook_url: str                         # URL Bolna/Vapi will POST tool calls to
    client_id: str                           # Our internal tenant ID (stored in metadata)
    telephony_number: Optional[str] = None   # Exotel number to bind
    metadata: dict = field(default_factory=dict)  # Provider-specific overrides


@dataclass
class AgentHandle:
    """Returned after creating/updating an agent. Stores provider IDs."""
    provider: str           # "bolna" | "vapi" | "pipecat"
    agent_id: str           # Provider's agent/assistant ID
    phone_number: Optional[str] = None
    raw_config: dict = field(default_factory=dict)  # Full provider response


@dataclass
class NormalizedEvent:
    """
    Provider-agnostic webhook event.

    Every provider's webhook payload gets normalized into this structure
    by parse_webhook(). All downstream handlers work with this only.
    """
    event_type: str                          # "tool_call" | "call_ended" | "call_started" | "unknown"
    call_id: str = ""
    client_id: str = ""
    tool_calls: Optional[list[dict]] = None  # [{name, tool_call_id, parameters}]
    transcript: Optional[str] = None
    messages: Optional[list[dict]] = None    # [{role, content}]
    recording_url: Optional[str] = None
    ended_reason: Optional[str] = None
    duration_seconds: Optional[int] = None
    raw: dict = field(default_factory=dict)  # Original payload for debugging


class VoiceEngine(ABC):
    """
    Abstract interface for voice AI providers.

    To swap providers, change VOICE_PROVIDER in .env:
      - "bolna"   → BolnaEngine  (primary, cheapest for India)
      - "vapi"    → VapiEngine   (fallback, more mature)
      - "pipecat" → PipecatEngine (future, fully self-hosted)

    The factory in factory.py returns the right implementation.
    """

    @abstractmethod
    async def create_agent(self, config: AgentConfig) -> AgentHandle:
        """Create a voice agent with the given configuration."""
        ...

    @abstractmethod
    async def update_agent(self, agent_id: str, config: AgentConfig) -> AgentHandle:
        """Update an existing agent's config (e.g. new knowledge base)."""
        ...

    @abstractmethod
    async def delete_agent(self, agent_id: str) -> bool:
        """Delete/deactivate an agent. Returns True on success."""
        ...

    @abstractmethod
    async def get_agent(self, agent_id: str) -> dict:
        """Retrieve current agent config from the provider."""
        ...

    @abstractmethod
    def parse_webhook(self, payload: dict) -> NormalizedEvent:
        """
        Normalize a provider-specific webhook payload.

        This is the critical method for provider-agnosticism:
        Bolna, Vapi, and Pipecat all send different webhook formats.
        This method maps them to NormalizedEvent so all downstream
        code (lead capture, alerts, storage) doesn't care which
        provider is active.
        """
        ...

    @abstractmethod
    def build_tool_response(self, tool_call_id: str, result: str) -> dict:
        """
        Build the provider-specific JSON response for a tool call.

        When our backend processes a tool call (e.g. capture_lead),
        it returns a result string. This method wraps it in whatever
        format the provider expects.
        """
        ...


# Tool definitions shared across all providers.
# Each provider's engine converts these to its own format.
VOICE_TOOLS = [
    {
        "name": "capture_lead",
        "description": (
            "Save the caller's lead information. Call this once you have collected "
            "their name, phone number, and at least two other details (budget, area, "
            "property type, urgency, or preferred viewing time)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Caller's full name"},
                "phone": {"type": "string", "description": "Caller's phone number"},
                "budget_min": {"type": "integer", "description": "Minimum budget in INR"},
                "budget_max": {"type": "integer", "description": "Maximum budget in INR"},
                "preferred_area": {"type": "string", "description": "Preferred locality or area"},
                "property_type": {"type": "string", "description": "2BHK, 3BHK, plot, villa, commercial"},
                "urgency": {
                    "type": "string",
                    "enum": ["immediate", "1-3months", "3-6months", "exploring"],
                    "description": "How soon they want to buy",
                },
                "viewing_time": {"type": "string", "description": "When they want to visit properties"},
                "notes": {"type": "string", "description": "Any additional requirements or comments"},
            },
            "required": ["name", "phone"],
        },
    },
    {
        "name": "lookup_property",
        "description": (
            "Search the property listings when the caller asks about specific "
            "properties, prices, availability, or features."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The property-related question to look up"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "escalate_to_agent",
        "description": (
            "Escalate to the human agent when the caller explicitly asks to speak "
            "with a person, or when you cannot answer their question after two attempts."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Why the call is being escalated"},
                "caller_phone": {"type": "string", "description": "Caller's phone number if available"},
            },
            "required": ["reason"],
        },
    },
]
