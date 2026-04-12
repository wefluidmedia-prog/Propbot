"""
Phone OTP service via MSG91.

Generates 6-digit OTPs, sends via MSG91, and verifies them.
OTPs are stored in memory (safe for single-instance Render deploy).
"""

import logging
import random
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# In-memory store: {phone: {otp, expires_at, attempts, send_count, first_sent}}
_otp_store: dict[str, dict] = {}

OTP_EXPIRY_SECONDS = 300   # 5 minutes
MAX_ATTEMPTS = 3            # Wrong guesses before lockout
MAX_SENDS_PER_HOUR = 3     # OTPs per phone per hour


def normalize_phone(phone: str) -> str:
    """Return 10-digit number, stripping +91 or 91 prefix."""
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+91"):
        phone = phone[3:]
    elif phone.startswith("91") and len(phone) == 12:
        phone = phone[2:]
    return phone


async def send_otp(phone: str) -> dict:
    """Send OTP to phone number. Returns {"success": bool, "message": str}."""
    phone = normalize_phone(phone)
    if len(phone) != 10 or not phone.isdigit():
        return {"success": False, "message": "Enter a valid 10-digit Indian mobile number."}

    now = time.time()
    existing = _otp_store.get(phone, {})

    # Rate-limit: max 3 sends per hour
    send_count = existing.get("send_count", 0)
    first_sent = existing.get("first_sent", now)
    if send_count >= MAX_SENDS_PER_HOUR and (now - first_sent) < 3600:
        minutes_left = int((3600 - (now - first_sent)) / 60) + 1
        return {"success": False, "message": f"Too many attempts. Try again in {minutes_left} minutes."}

    otp = str(random.randint(100000, 999999))
    _otp_store[phone] = {
        "otp": otp,
        "expires_at": now + OTP_EXPIRY_SECONDS,
        "attempts": 0,
        "send_count": (send_count + 1) if (now - first_sent) < 3600 else 1,
        "first_sent": first_sent if (now - first_sent) < 3600 else now,
    }

    if settings.MSG91_AUTH_KEY and settings.MSG91_TEMPLATE_ID:
        ok = await _send_via_msg91(f"91{phone}", otp)
        if not ok:
            return {"success": False, "message": "Failed to send OTP. Please try again."}
    else:
        # Dev fallback — log OTP so developer can verify
        logger.warning("[DEV] OTP for %s: %s", phone, otp)

    return {"success": True, "message": "OTP sent to your mobile number."}


async def verify_otp(phone: str, otp: str) -> dict:
    """Verify OTP. Returns {"success": bool, "message": str}."""
    phone = normalize_phone(phone)
    otp = otp.strip()

    record = _otp_store.get(phone)
    if not record:
        return {"success": False, "message": "No OTP found. Please request a new OTP."}

    if time.time() > record["expires_at"]:
        _otp_store.pop(phone, None)
        return {"success": False, "message": "OTP has expired. Please request a new one."}

    if record["attempts"] >= MAX_ATTEMPTS:
        _otp_store.pop(phone, None)
        return {"success": False, "message": "Too many incorrect attempts. Please request a new OTP."}

    if otp != record["otp"]:
        _otp_store[phone]["attempts"] += 1
        remaining = MAX_ATTEMPTS - _otp_store[phone]["attempts"]
        return {"success": False, "message": f"Incorrect OTP. {remaining} attempt(s) left."}

    # Valid — clear from store
    _otp_store.pop(phone, None)
    return {"success": True, "message": "Phone verified successfully."}


async def _send_via_msg91(mobile_with_country: str, otp: str) -> bool:
    """Send OTP via MSG91 API. Returns True on success."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://control.msg91.com/api/v5/otp",
                json={
                    "template_id": settings.MSG91_TEMPLATE_ID,
                    "mobile": mobile_with_country,
                    "authkey": settings.MSG91_AUTH_KEY,
                    "otp_length": 6,
                    "otp_expiry": 5,
                    "otp": otp,
                },
                headers={"Content-Type": "application/json"},
            )
            data = resp.json() if resp.content else {}
            if resp.is_success and data.get("type") == "success":
                return True
            logger.warning("MSG91 send failed: status=%s body=%s", resp.status_code, data)
    except Exception as e:
        logger.error("MSG91 send exception: %s", e)
    return False
