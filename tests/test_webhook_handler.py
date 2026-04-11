"""Tests for the webhook router — verifies payload routing."""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestWebhookRouter:
    @patch("app.routers.webhooks._verify_webhook_signature")
    @patch("app.routers.webhooks.get_voice_engine")
    def test_unknown_event_returns_200(self, mock_engine, mock_verify, client):
        """Unknown events should be acknowledged with 200."""
        mock_instance = mock_engine.return_value
        mock_instance.parse_webhook.return_value = type(
            "Event", (), {"event_type": "unknown", "call_id": "", "client_id": "", "tool_calls": None}
        )()

        resp = client.post("/api/webhooks/voice", json={"type": "some_event"})
        assert resp.status_code == 200

    @patch("app.routers.webhooks._verify_webhook_signature")
    @patch("app.routers.webhooks.store_conversation", new_callable=AsyncMock)
    @patch("app.routers.webhooks.get_voice_engine")
    def test_call_ended_stores_conversation(self, mock_engine, mock_store, mock_verify, client):
        """call_ended events should trigger conversation storage."""
        from app.voice.base import NormalizedEvent

        event = NormalizedEvent(
            event_type="call_ended",
            call_id="call_123",
            client_id="client_abc",
            transcript="Test transcript",
            recording_url="https://example.com/recording.wav",
            ended_reason="hangup",
        )
        mock_instance = mock_engine.return_value
        mock_instance.parse_webhook.return_value = event
        mock_instance.get_call_details = AsyncMock(return_value=None)

        resp = client.post("/api/webhooks/voice", json={"type": "end_of_call"})
        assert resp.status_code == 200
        mock_store.assert_called_once_with(event)
