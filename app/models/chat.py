from pydantic import BaseModel, Field
from typing import Literal, Optional


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=10_000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5_000)
    history: list[ChatMessage] = Field(default=[], max_length=100)
    visitor_id: Optional[str] = Field(default=None, max_length=100)


class ChatResponse(BaseModel):
    reply: str
    visitor_id: str
