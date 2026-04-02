"""
Alert service — sends email + SMS notifications to agents.

Email: Gmail SMTP with app password
SMS: Exotel SMS API
"""

import asyncio
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from html import escape

import httpx
from app.config import settings

logger = logging.getLogger(__name__)


async def send_lead_alert(client_data: dict, lead_data: dict) -> None:
    """
    Send email + SMS alert to the agent about a new lead.
    Called asynchronously — failures are logged but don't block the caller.
    """
    agent_email = client_data.get("agent_email", "")
    agent_phone = client_data.get("agent_phone", "")
    business_name = client_data.get("business_name", "")

    caller_name = lead_data.get("caller_name") or lead_data.get("name") or "Unknown"
    caller_phone = lead_data.get("caller_phone") or lead_data.get("phone") or "N/A"
    property_type = lead_data.get("property_type", "")
    area = lead_data.get("preferred_area", "")
    budget_min = lead_data.get("budget_min", "")
    budget_max = lead_data.get("budget_max", "")
    urgency = lead_data.get("urgency", "")
    source = lead_data.get("source", "voice")

    # Email
    if agent_email and settings.SMTP_EMAIL:
        try:
            await asyncio.to_thread(
                _send_email,
                to=agent_email,
                subject=f"New Lead: {caller_name} — {property_type} {area}",
                body=_format_lead_email(
                    business_name=business_name,
                    caller_name=caller_name,
                    caller_phone=caller_phone,
                    property_type=property_type,
                    area=area,
                    budget_min=budget_min,
                    budget_max=budget_max,
                    urgency=urgency,
                    viewing_time=lead_data.get("preferred_viewing_time") or lead_data.get("viewing_time", ""),
                    notes=lead_data.get("notes", ""),
                    source=source,
                ),
            )
            logger.info("Email alert sent")
        except Exception as e:
            logger.error(f"Email alert failed: {e}")

    # SMS
    if agent_phone and settings.EXOTEL_ACCOUNT_SID:
        sms_text = (
            f"PropBot: New {source} lead!\n"
            f"Name: {caller_name}\n"
            f"Phone: {caller_phone}\n"
            f"Looking: {property_type} in {area}\n"
            f"Budget: {budget_min}-{budget_max}\n"
            f"Urgency: {urgency}"
        )
        try:
            await _send_exotel_sms(to=agent_phone, message=sms_text)
            logger.info("SMS alert sent")
        except Exception as e:
            logger.error(f"SMS alert failed: {e}")


async def send_callback_alert(client_data: dict, callback_data: dict) -> None:
    """Send alert for a callback request from chat widget."""
    agent_email = client_data.get("agent_email", "")
    agent_phone = client_data.get("agent_phone", "")
    visitor_name = callback_data.get("visitor_name") or callback_data.get("name") or "Website visitor"
    visitor_phone = callback_data.get("visitor_phone") or callback_data.get("phone", "")

    if agent_email and settings.SMTP_EMAIL:
        try:
            await asyncio.to_thread(
                _send_email,
                to=agent_email,
                subject=f"Callback Request: {escape(visitor_name)}",
                body=(
                    f"<h2>Callback Request from Website</h2>"
                    f"<p><strong>Name:</strong> {escape(visitor_name)}</p>"
                    f"<p><strong>Phone:</strong> {escape(visitor_phone)}</p>"
                    f"<p><strong>Preferred time:</strong> {escape(callback_data.get('preferred_time', 'Not specified'))}</p>"
                    f"<p><strong>Context:</strong> {escape(callback_data.get('context', 'No context'))}</p>"
                    f"<br><p>Please call them back as soon as possible.</p>"
                ),
            )
        except Exception as e:
            logger.error(f"Callback email alert failed: {e}")

    if agent_phone and settings.EXOTEL_ACCOUNT_SID:
        sms_text = f"PropBot: Callback request! {visitor_name} — {visitor_phone}. Call them back ASAP."
        try:
            await _send_exotel_sms(to=agent_phone, message=sms_text)
        except Exception as e:
            logger.error(f"Callback SMS alert failed: {e}")


def _send_email(to: str, subject: str, body: str) -> None:
    """Send an HTML email via Gmail SMTP."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_EMAIL
    msg["To"] = to
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(settings.SMTP_EMAIL, settings.SMTP_APP_PASSWORD)
        server.send_message(msg)


async def _send_exotel_sms(to: str, message: str) -> None:
    """Send SMS via Exotel API."""
    url = (
        f"https://{settings.EXOTEL_SUBDOMAIN}/v1/Accounts/"
        f"{settings.EXOTEL_ACCOUNT_SID}/Sms/send"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            url,
            auth=(settings.EXOTEL_API_KEY, settings.EXOTEL_API_TOKEN),
            data={
                "From": settings.EXOTEL_CALLER_ID,
                "To": to,
                "Body": message,
            },
        )


def _format_lead_email(
    business_name: str,
    caller_name: str,
    caller_phone: str,
    property_type: str,
    area: str,
    budget_min: str,
    budget_max: str,
    urgency: str,
    viewing_time: str,
    notes: str,
    source: str,
) -> str:
    """Format lead data as an HTML email body."""
    budget_str = ""
    if budget_min and budget_max:
        budget_str = f"₹{budget_min:,} — ₹{budget_max:,}" if isinstance(budget_min, int) else f"₹{budget_min} — ₹{budget_max}"
    elif budget_min:
        budget_str = f"₹{budget_min}+"
    elif budget_max:
        budget_str = f"Up to ₹{budget_max}"

    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px;">
        <h2 style="color: #2563eb;">New Lead from PropBot AI — {escape(business_name)}</h2>
        <p style="color: #666;">Source: {escape(source.upper())} call</p>
        <table style="width: 100%; border-collapse: collapse; margin-top: 16px;">
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Name</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{escape(caller_name)}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Phone</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;"><a href="tel:{escape(caller_phone)}">{escape(caller_phone)}</a></td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Looking for</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{escape(property_type)}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Area</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{escape(area)}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Budget</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{escape(budget_str)}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Urgency</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{escape(urgency)}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Viewing time</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{escape(viewing_time)}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Notes</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{escape(notes)}</td></tr>
        </table>
        <p style="margin-top: 16px; color: #059669; font-weight: bold;">Please call this lead back as soon as possible.</p>
        <p style="color: #999; font-size: 12px; margin-top: 24px;">Sent by PropBot AI Receptionist</p>
    </div>
    """
