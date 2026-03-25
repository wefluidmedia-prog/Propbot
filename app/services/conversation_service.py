"""
Conversation storage service.

Stores call transcripts, recordings, and chat histories in Supabase.
"""

import logging
from app.db.supabase_client import get_supabase
from app.voice.base import NormalizedEvent

logger = logging.getLogger(__name__)


async def store_conversation(event: NormalizedEvent) -> None:
    """Store a completed voice conversation from an end-of-call webhook."""
    db = get_supabase()

    record = {
        "client_id": event.client_id,
        "source": "voice",
        "call_id": event.call_id,
        "transcript": event.transcript,
        "messages": event.messages,
        "recording_url": event.recording_url,
        "duration_seconds": event.duration_seconds,
        "ended_reason": event.ended_reason,
    }

    result = db.table("conversations").insert(record).execute()
    logger.info(f"Conversation stored: {result.data[0]['id']} for call {event.call_id}")
