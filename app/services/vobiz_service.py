"""
Vobiz API client — fetches call recordings from Vobiz telephony platform.

Vobiz stores recordings for all calls. We fetch them after call_ended
events since Bolna doesn't forward recording URLs.
"""

import logging
from datetime import datetime, timezone

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 15


def _headers() -> dict:
    return {
        "X-Auth-ID": settings.VOBIZ_AUTH_ID,
        "X-Auth-Token": settings.VOBIZ_AUTH_TOKEN,
        "Content-Type": "application/json",
    }


def _base_url() -> str:
    return f"{settings.VOBIZ_API_URL}/Account/{settings.VOBIZ_AUTH_ID}"


async def get_recordings(limit: int = 20, offset: int = 0) -> list[dict]:
    """Fetch recent recordings from Vobiz."""
    if not settings.VOBIZ_AUTH_ID or not settings.VOBIZ_AUTH_TOKEN:
        logger.debug("Vobiz credentials not configured, skipping recording fetch")
        return []

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_base_url()}/Recording/",
                headers=_headers(),
                params={"limit": limit, "offset": offset},
            )
            if resp.is_success:
                data = resp.json()
                return data.get("objects", data) if isinstance(data, dict) else data
            logger.warning("Vobiz get_recordings: status=%s", resp.status_code)
    except Exception as e:
        logger.warning("Vobiz get_recordings failed: %s", e)
    return []


async def get_call_recording(call_uuid: str) -> str | None:
    """
    Fetch recording URL for a specific call UUID from Vobiz CDR.

    Tries the CDR endpoint filtered by call_uuid, then extracts the
    recording URL from the response.
    """
    if not settings.VOBIZ_AUTH_ID or not settings.VOBIZ_AUTH_TOKEN:
        return None

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # Try CDR endpoint filtered by call UUID
            resp = await client.get(
                f"{_base_url()}/CDR/",
                headers=_headers(),
                params={"call_uuid": call_uuid},
            )
            if resp.is_success:
                data = resp.json()
                records = data.get("objects", []) if isinstance(data, dict) else []
                for record in records:
                    rec_url = record.get("recording_url") or record.get("recording_resource_url")
                    if rec_url:
                        return rec_url

            # Fallback: try direct recording endpoint
            resp = await client.get(
                f"{_base_url()}/Recording/",
                headers=_headers(),
                params={"call_uuid": call_uuid, "limit": 1},
            )
            if resp.is_success:
                data = resp.json()
                records = data.get("objects", []) if isinstance(data, dict) else []
                if records:
                    return records[0].get("recording_url") or records[0].get("url")

    except Exception as e:
        logger.warning("Vobiz get_call_recording failed for %s: %s", call_uuid, e)
    return None


async def fetch_recent_recording_url(phone_number: str, call_time: datetime | None = None) -> str | None:
    """
    Find a recording by phone number and approximate call time.

    Useful when we don't have the Vobiz call UUID but know the
    phone number and when the call happened.
    """
    if not settings.VOBIZ_AUTH_ID or not settings.VOBIZ_AUTH_TOKEN:
        return None

    try:
        params: dict = {"limit": 5}
        if phone_number:
            params["to_number"] = phone_number

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_base_url()}/CDR/",
                headers=_headers(),
                params=params,
            )
            if resp.is_success:
                data = resp.json()
                records = data.get("objects", []) if isinstance(data, dict) else []
                for record in records:
                    rec_url = record.get("recording_url") or record.get("recording_resource_url")
                    if rec_url:
                        return rec_url
    except Exception as e:
        logger.warning("Vobiz fetch_recent_recording_url failed: %s", e)
    return None
