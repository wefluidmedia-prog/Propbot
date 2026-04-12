"""
Email OTP service via SMTP (Gmail).

Generates 6-digit OTPs, sends via SMTP, and verifies them.
OTPs are stored in memory (safe for single-instance Render deploy).
"""

import asyncio
import logging
import random
import re
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)

# In-memory store: {email: {otp, expires_at, attempts, send_count, first_sent}}
_otp_store: dict[str, dict] = {}

OTP_EXPIRY_SECONDS = 300   # 5 minutes
MAX_ATTEMPTS = 3            # Wrong guesses before lockout
MAX_SENDS_PER_HOUR = 3     # OTPs per email per hour

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(email: str) -> str:
    """Return lowercased, stripped email."""
    return email.strip().lower()


def _is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email))


async def send_otp(email: str) -> dict:
    """Send OTP to email address. Returns {"success": bool, "message": str}."""
    email = normalize_email(email)
    if not _is_valid_email(email):
        return {"success": False, "message": "Enter a valid email address."}

    now = time.time()
    existing = _otp_store.get(email, {})

    # Rate-limit: max 3 sends per hour
    send_count = existing.get("send_count", 0)
    first_sent = existing.get("first_sent", now)
    if send_count >= MAX_SENDS_PER_HOUR and (now - first_sent) < 3600:
        minutes_left = int((3600 - (now - first_sent)) / 60) + 1
        return {"success": False, "message": f"Too many attempts. Try again in {minutes_left} minutes."}

    otp = str(random.randint(100000, 999999))
    _otp_store[email] = {
        "otp": otp,
        "expires_at": now + OTP_EXPIRY_SECONDS,
        "attempts": 0,
        "send_count": (send_count + 1) if (now - first_sent) < 3600 else 1,
        "first_sent": first_sent if (now - first_sent) < 3600 else now,
    }

    if settings.SMTP_EMAIL and settings.SMTP_APP_PASSWORD:
        ok = await _send_via_smtp(email, otp)
        if not ok:
            return {"success": False, "message": "Failed to send OTP email. Please try again."}
    else:
        # Dev fallback — log OTP to console
        logger.warning("[DEV] OTP for %s: %s", email, otp)

    return {"success": True, "message": f"OTP sent to {email}"}


async def verify_otp(email: str, otp: str) -> dict:
    """Verify OTP. Returns {"success": bool, "message": str}."""
    email = normalize_email(email)
    otp = otp.strip()

    record = _otp_store.get(email)
    if not record:
        return {"success": False, "message": "No OTP found. Please request a new OTP."}

    if time.time() > record["expires_at"]:
        _otp_store.pop(email, None)
        return {"success": False, "message": "OTP has expired. Please request a new one."}

    if record["attempts"] >= MAX_ATTEMPTS:
        _otp_store.pop(email, None)
        return {"success": False, "message": "Too many incorrect attempts. Please request a new OTP."}

    if otp != record["otp"]:
        _otp_store[email]["attempts"] += 1
        remaining = MAX_ATTEMPTS - _otp_store[email]["attempts"]
        return {"success": False, "message": f"Incorrect OTP. {remaining} attempt(s) left."}

    # Valid — clear from store
    _otp_store.pop(email, None)
    return {"success": True, "message": "Email verified successfully."}


async def _send_via_smtp(to_email: str, otp: str) -> bool:
    """Send OTP email via Gmail SMTP (runs in thread to avoid blocking event loop)."""

    def _send_sync() -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"{otp} is your PropBot verification code"
            msg["From"] = f"PropBot <{settings.SMTP_EMAIL}>"
            msg["To"] = to_email

            text = (
                f"Your PropBot verification code is: {otp}\n\n"
                "This code expires in 5 minutes. Do not share it with anyone.\n\n"
                "— PropBot Team"
            )
            html = (
                "<!DOCTYPE html><html><body style=\"font-family:Inter,-apple-system,sans-serif;"
                "background:#f4f4f5;padding:40px 20px;margin:0;\">"
                "<div style=\"max-width:420px;margin:0 auto;background:#fff;border-radius:16px;"
                "padding:36px;border:1px solid #e4e4e7;\">"
                "<div style=\"margin-bottom:24px;\">"
                "<span style=\"font-size:22px;font-weight:800;color:#111827;\">Prop</span>"
                "<span style=\"font-size:22px;font-weight:800;color:#FF5722;\">Bot</span>"
                "</div>"
                "<h1 style=\"font-size:18px;font-weight:700;color:#111827;margin:0 0 8px;\">"
                "Your verification code</h1>"
                "<p style=\"font-size:14px;color:#6B7280;margin:0 0 28px;\">"
                "Enter this code to verify your email and complete signup.</p>"
                "<div style=\"background:#f4f4f5;border-radius:12px;padding:24px;"
                "text-align:center;margin-bottom:28px;\">"
                f"<span style=\"font-size:42px;font-weight:800;letter-spacing:10px;color:#111827;\">{otp}</span>"
                "</div>"
                "<p style=\"font-size:13px;color:#9CA3AF;margin:0;\">This code expires in "
                "<strong>5 minutes</strong>. Do not share it with anyone.</p>"
                "</div></body></html>"
            )

            msg.attach(MIMEText(text, "plain"))
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as smtp:
                smtp.login(settings.SMTP_EMAIL, settings.SMTP_APP_PASSWORD)
                smtp.sendmail(settings.SMTP_EMAIL, to_email, msg.as_string())
            logger.info("OTP email sent to %s", to_email)
            return True
        except Exception as e:
            logger.error("SMTP send failed to %s: %s", to_email, e)
            return False

    return await asyncio.to_thread(_send_sync)
