"""
Google Calendar service for PropBot SaaS.

Allows real estate agents to connect their Google Calendar so the AI
can check availability and book property viewings during phone calls.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import google.auth.transport.requests
import google.oauth2.credentials
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.config import settings
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
]

IST = timezone(timedelta(hours=5, minutes=30))


def _get_client_config() -> dict:
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def _get_redirect_uri() -> str:
    redirect_uri = getattr(settings, "GOOGLE_REDIRECT_URI", None)
    if redirect_uri:
        return redirect_uri
    return f"{settings.BASE_URL}/dashboard/google/callback"


def _get_credentials(client_id: str) -> google.oauth2.credentials.Credentials | None:
    """Load and refresh Google OAuth credentials for a client."""
    db = get_supabase()
    try:
        response = (
            db.table("clients")
            .select("google_calendar_token")
            .eq("id", client_id)
            .single()
            .execute()
        )
    except Exception as exc:
        logger.error("Failed to fetch google_calendar_token for client %s: %s", client_id, exc)
        return None

    token_data = response.data.get("google_calendar_token") if response.data else None
    if not token_data or not token_data.get("access_token"):
        return None

    creds = google.oauth2.credentials.Credentials(
        token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(google.auth.transport.requests.Request())
            updated_token = {
                "access_token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "scopes": list(creds.scopes) if creds.scopes else [],
                "expiry": creds.expiry.isoformat() if creds.expiry else None,
            }
            db.table("clients").update({"google_calendar_token": updated_token}).eq(
                "id", client_id
            ).execute()
        except RefreshError as exc:
            logger.error("Failed to refresh credentials for client %s: %s", client_id, exc)
            return None

    return creds


def _get_calendar_service(credentials: google.oauth2.credentials.Credentials):
    """Build and return a Google Calendar API service object."""
    return build("calendar", "v3", credentials=credentials)


async def get_oauth_url(client_id: str) -> str:
    """Generate a Google OAuth authorization URL for a client."""
    flow = Flow.from_client_config(
        _get_client_config(),
        scopes=SCOPES,
        redirect_uri=_get_redirect_uri(),
    )
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=client_id,
    )
    return authorization_url


async def handle_oauth_callback(code: str, client_id: str) -> None:
    """Exchange an authorization code for tokens and persist them."""
    flow = Flow.from_client_config(
        _get_client_config(),
        scopes=SCOPES,
        redirect_uri=_get_redirect_uri(),
    )
    flow.fetch_token(code=code)
    creds = flow.credentials

    token_data = {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "scopes": list(creds.scopes) if creds.scopes else [],
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }

    db = get_supabase()
    db.table("clients").update({"google_calendar_token": token_data}).eq(
        "id", client_id
    ).execute()
    logger.info("Google Calendar connected for client %s", client_id)


async def is_calendar_connected(client_id: str) -> bool:
    """Return True if the client has a connected Google Calendar."""
    db = get_supabase()
    try:
        response = (
            db.table("clients")
            .select("google_calendar_token")
            .eq("id", client_id)
            .single()
            .execute()
        )
    except Exception as exc:
        logger.error("Error checking calendar connection for client %s: %s", client_id, exc)
        return False

    token_data = response.data.get("google_calendar_token") if response.data else None
    return bool(token_data and token_data.get("access_token"))


async def get_available_slots(client_id: str, date_str: str) -> list[dict]:
    """Return available 1-hour viewing slots for the given date (YYYY-MM-DD).

    Slots run from 9 AM to 7 PM IST in 1-hour increments; busy periods
    from the primary calendar are excluded.
    """
    creds = _get_credentials(client_id)
    if creds is None:
        logger.warning("No credentials for client %s; returning empty slots", client_id)
        return []

    date = datetime.strptime(date_str, "%Y-%m-%d").date()
    time_min = datetime(date.year, date.month, date.day, 9, 0, 0, tzinfo=IST)
    time_max = datetime(date.year, date.month, date.day, 19, 0, 0, tzinfo=IST)

    time_min_iso = time_min.isoformat()
    time_max_iso = time_max.isoformat()

    def _fetch_busy():
        service = _get_calendar_service(creds)
        return service.freebusy().query(
            body={
                "timeMin": time_min_iso,
                "timeMax": time_max_iso,
                "items": [{"id": "primary"}],
            }
        ).execute()

    try:
        result = await asyncio.to_thread(_fetch_busy)
    except Exception as exc:
        logger.error("FreeBusy query failed for client %s: %s", client_id, exc)
        return []

    busy_periods = result.get("calendars", {}).get("primary", {}).get("busy", [])

    def _parse_dt(iso: str) -> datetime:
        return datetime.fromisoformat(iso)

    busy = [
        (_parse_dt(b["start"]), _parse_dt(b["end"]))
        for b in busy_periods
    ]

    slots = []
    slot_start = time_min
    while slot_start < time_max - timedelta(minutes=1):
        slot_end = slot_start + timedelta(hours=1)
        overlaps = any(
            not (slot_end <= b_start or slot_start >= b_end)
            for b_start, b_end in busy
        )
        if not overlaps:
            slots.append({"start": slot_start.isoformat(), "end": slot_end.isoformat()})
        slot_start += timedelta(hours=1)

    return slots


async def book_viewing(
    client_id: str,
    attendee_name: str,
    attendee_phone: str,
    viewing_datetime: str,
    property_name: str,
) -> dict:
    """Book a 1-hour property viewing on the client's primary Google Calendar.

    Returns a dict with event_id, start, and end on success, or an "error" key
    on failure.
    """
    creds = _get_credentials(client_id)
    if creds is None:
        return {"error": "Calendar not connected. Please connect your Google Calendar from the dashboard."}

    start_dt = datetime.fromisoformat(viewing_datetime)
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=IST)
    end_dt = start_dt + timedelta(hours=1)

    start_iso = start_dt.isoformat()
    end_iso = end_dt.isoformat()

    date_str = start_dt.astimezone(IST).strftime("%Y-%m-%d")
    available_slots = await get_available_slots(client_id, date_str)

    slot_start_norm = start_dt.astimezone(IST).replace(second=0, microsecond=0)
    is_available = any(
        datetime.fromisoformat(s["start"]).astimezone(IST).replace(second=0, microsecond=0)
        == slot_start_norm
        for s in available_slots
    )

    if not is_available:
        return {
            "error": "Sorry, that time slot is not available. Would you like to try a different time?"
        }

    event = {
        "summary": f"Property Viewing: {property_name} — {attendee_name}",
        "description": (
            f"Caller: {attendee_name}\n"
            f"Phone: {attendee_phone}\n"
            f"Property: {property_name}\n\n"
            "Booked via PropBot AI Receptionist"
        ),
        "start": {"dateTime": start_iso, "timeZone": "Asia/Kolkata"},
        "end": {"dateTime": end_iso, "timeZone": "Asia/Kolkata"},
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": 30}],
        },
    }

    def _insert_event():
        service = _get_calendar_service(creds)
        return service.events().insert(calendarId="primary", body=event).execute()

    try:
        result = await asyncio.to_thread(_insert_event)
    except Exception as exc:
        logger.error("Failed to insert calendar event for client %s: %s", client_id, exc)
        return {"error": "Failed to book the viewing. Please try again."}

    logger.info(
        "Booked viewing for client %s: event %s at %s",
        client_id,
        result["id"],
        start_iso,
    )
    return {"event_id": result["id"], "start": start_iso, "end": end_iso}


async def disconnect_calendar(client_id: str) -> None:
    """Remove the stored Google Calendar token for a client."""
    db = get_supabase()
    db.table("clients").update({"google_calendar_token": None}).eq("id", client_id).execute()
    logger.info("Google Calendar disconnected for client %s", client_id)
