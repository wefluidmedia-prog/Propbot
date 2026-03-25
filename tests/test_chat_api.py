"""Tests for chat API — request/response models."""

from app.models.chat import ChatRequest, ChatResponse, ChatMessage


class TestChatModels:
    def test_chat_request_minimal(self):
        req = ChatRequest(message="Hello")
        assert req.message == "Hello"
        assert req.history == []
        assert req.visitor_id is None

    def test_chat_request_with_history(self):
        req = ChatRequest(
            message="2BHK ka price kya hai?",
            history=[
                ChatMessage(role="assistant", content="Namaste!"),
                ChatMessage(role="user", content="Hi"),
            ],
            visitor_id="v_abc123",
        )
        assert len(req.history) == 2
        assert req.history[0].role == "assistant"

    def test_chat_response(self):
        resp = ChatResponse(reply="Dwarka mein 2BHK ₹62 lakh se shuru hai.", visitor_id="v_abc123")
        assert "62 lakh" in resp.reply
