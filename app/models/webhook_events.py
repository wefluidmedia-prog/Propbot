"""
Pydantic models for validating incoming webhook payloads.

These are used for basic request validation in the webhook router.
The actual normalization happens in VoiceEngine.parse_webhook().
"""

from pydantic import BaseModel
from typing import Any


class WebhookPayload(BaseModel):
    """Generic webhook payload — we accept any JSON and let the engine parse it."""
    class Config:
        extra = "allow"
