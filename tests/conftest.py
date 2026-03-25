"""Test fixtures — mock Supabase and voice engine payloads."""

import pytest


@pytest.fixture
def sample_bolna_tool_call_payload():
    """Sample Bolna webhook payload for a tool call."""
    return {
        "type": "tool_call",
        "call_id": "call_abc123",
        "metadata": {"client_id": "client_xyz"},
        "tool_calls": [
            {
                "name": "capture_lead",
                "id": "tc_001",
                "parameters": {
                    "name": "Amit Kumar",
                    "phone": "+919999888877",
                    "budget_min": 5000000,
                    "budget_max": 8500000,
                    "preferred_area": "Dwarka",
                    "property_type": "2BHK",
                    "urgency": "1-3months",
                    "viewing_time": "Saturday morning",
                    "notes": "Wants park-facing flat",
                },
            }
        ],
    }


@pytest.fixture
def sample_bolna_call_ended_payload():
    """Sample Bolna webhook payload for call ended."""
    return {
        "type": "end_of_call",
        "call_id": "call_abc123",
        "metadata": {"client_id": "client_xyz"},
        "transcript": "Priya: Namaste! Sharma Properties...\nCaller: Mujhe 2BHK chahiye Dwarka mein...",
        "messages": [
            {"role": "assistant", "content": "Namaste! Sharma Properties mein aapka swagat hai."},
            {"role": "user", "content": "Mujhe 2BHK chahiye Dwarka mein"},
        ],
        "recording_url": "https://recordings.bolna.dev/call_abc123.wav",
        "duration": 185,
        "ended_reason": "caller_hangup",
    }


@pytest.fixture
def sample_vapi_tool_call_payload():
    """Sample Vapi webhook payload for a tool call."""
    return {
        "message": {
            "type": "tool-calls",
            "call": {
                "id": "call_vapi_456",
                "metadata": {"client_id": "client_xyz"},
            },
            "toolWithToolCallList": [
                {
                    "function": {"name": "capture_lead"},
                    "toolCall": {
                        "id": "tc_vapi_001",
                        "parameters": {
                            "name": "Priya Verma",
                            "phone": "+919888777666",
                            "preferred_area": "Noida Sector 75",
                            "property_type": "3BHK",
                        },
                    },
                }
            ],
        }
    }


@pytest.fixture
def sample_vapi_call_ended_payload():
    """Sample Vapi webhook payload for end of call."""
    return {
        "message": {
            "type": "end-of-call-report",
            "call": {
                "id": "call_vapi_456",
                "metadata": {"client_id": "client_xyz"},
            },
            "endedReason": "hangup",
            "artifact": {
                "transcript": "AI: Namaste!...\nUser: Hello...",
                "messages": [
                    {"role": "assistant", "content": "Namaste!"},
                    {"role": "user", "content": "Hello"},
                ],
                "recording": {"url": "https://recordings.vapi.ai/call_vapi_456.wav"},
            },
        }
    }
