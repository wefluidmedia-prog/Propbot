"""Tests for VoiceEngine abstraction — both Bolna and Vapi webhook parsing."""

from app.voice.bolna_engine import BolnaEngine
from app.voice.vapi_engine import VapiEngine


class TestBolnaEngine:
    def setup_method(self):
        self.engine = BolnaEngine(api_key="test_key")

    def test_parse_tool_call(self, sample_bolna_tool_call_payload):
        event = self.engine.parse_webhook(sample_bolna_tool_call_payload)
        assert event.event_type == "tool_call"
        assert event.call_id == "call_abc123"
        assert event.client_id == "client_xyz"
        assert len(event.tool_calls) == 1
        assert event.tool_calls[0]["name"] == "capture_lead"
        assert event.tool_calls[0]["parameters"]["name"] == "Amit Kumar"
        assert event.tool_calls[0]["parameters"]["phone"] == "+919999888877"

    def test_parse_call_ended(self, sample_bolna_call_ended_payload):
        event = self.engine.parse_webhook(sample_bolna_call_ended_payload)
        assert event.event_type == "call_ended"
        assert event.call_id == "call_abc123"
        assert event.client_id == "client_xyz"
        assert "Sharma Properties" in event.transcript
        assert event.recording_url == "https://recordings.bolna.dev/call_abc123.wav"
        assert event.duration_seconds == 185
        assert event.ended_reason == "caller_hangup"

    def test_build_tool_response(self):
        resp = self.engine.build_tool_response("tc_001", "Lead saved successfully")
        assert resp == {
            "results": [{"tool_call_id": "tc_001", "result": "Lead saved successfully"}]
        }

    def test_parse_unknown_event(self):
        event = self.engine.parse_webhook({"type": "some_future_event"})
        assert event.event_type == "unknown"


class TestVapiEngine:
    def setup_method(self):
        self.engine = VapiEngine(api_key="test_key")

    def test_parse_tool_call(self, sample_vapi_tool_call_payload):
        event = self.engine.parse_webhook(sample_vapi_tool_call_payload)
        assert event.event_type == "tool_call"
        assert event.call_id == "call_vapi_456"
        assert event.client_id == "client_xyz"
        assert len(event.tool_calls) == 1
        assert event.tool_calls[0]["name"] == "capture_lead"
        assert event.tool_calls[0]["tool_call_id"] == "tc_vapi_001"
        assert event.tool_calls[0]["parameters"]["name"] == "Priya Verma"

    def test_parse_call_ended(self, sample_vapi_call_ended_payload):
        event = self.engine.parse_webhook(sample_vapi_call_ended_payload)
        assert event.event_type == "call_ended"
        assert event.call_id == "call_vapi_456"
        assert "Namaste" in event.transcript
        assert event.recording_url == "https://recordings.vapi.ai/call_vapi_456.wav"
        assert event.ended_reason == "hangup"

    def test_build_tool_response(self):
        resp = self.engine.build_tool_response("tc_vapi_001", "Done")
        assert resp == {
            "results": [{"toolCallId": "tc_vapi_001", "result": "Done"}]
        }

    def test_both_engines_normalize_to_same_structure(
        self, sample_bolna_tool_call_payload, sample_vapi_tool_call_payload
    ):
        """Both engines must produce NormalizedEvent with same fields."""
        bolna = BolnaEngine(api_key="test").parse_webhook(sample_bolna_tool_call_payload)
        vapi = VapiEngine(api_key="test").parse_webhook(sample_vapi_tool_call_payload)

        # Both are tool_call events
        assert bolna.event_type == vapi.event_type == "tool_call"
        # Both have tool_calls list
        assert isinstance(bolna.tool_calls, list)
        assert isinstance(vapi.tool_calls, list)
        # Both tool calls have the same keys
        bolna_keys = set(bolna.tool_calls[0].keys())
        vapi_keys = set(vapi.tool_calls[0].keys())
        assert bolna_keys == vapi_keys == {"name", "tool_call_id", "parameters"}
