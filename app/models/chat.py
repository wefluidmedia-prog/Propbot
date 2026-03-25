from pydantic import BaseModel
from typing import Optional


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    visitor_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    visitor_id: str
