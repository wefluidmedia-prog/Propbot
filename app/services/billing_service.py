"""
Razorpay billing service — manages subscriptions for PropBot SaaS.

Handles customer creation, subscription lifecycle, webhook processing,
and subscription status checks. Rs 5,000/month plan via Razorpay.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

import razorpay

from app.config import settings
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# Lazy singleton — initialised on first use
_razorpay_client: razorpay.Client | None = None


def _get_razorpay_client() -> razorpay.Client:
    """Return a lazily-initialised Razorpay SDK client."""
    global _razorpay_client
    if _razorpay_client is None:
        _razorpay_client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        logger.debug("Razorpay client initialised")
    return _razorpay_client


async def create_razorpay_customer(
    client_id: str, name: str, email: str, phone: str
) -> str:
    """
    Create a Razorpay customer and persist the customer ID to the clients table.

    Returns the Razorpay customer_id string.
    """
    rz = _get_razorpay_client()

    customer = await asyncio.to_thread(
        rz.customer.create,
        {
            "name": name,
            "email": email,
            "contact": phone,
            "notes": {"client_id": client_id},
        },
    )
    customer_id: str = customer["id"]
    logger.info("Created Razorpay customer %s for client %s", customer_id, client_id)

    db = get_supabase()
    db.table("clients").update({"razorpay_customer_id": customer_id}).eq(
        "id", client_id
    ).execute()

    return customer_id


PLAN_FEES_INR = {"starter": 2499, "pro": 4999}
STARTER_CALLS_LIMIT = 50


async def create_subscription(client_id: str) -> dict:
    """
    Create a Razorpay subscription for an existing client.

    Creates a Razorpay customer first if one does not already exist.
    Persists the subscription ID to the clients table.
    Uses the correct Razorpay plan ID based on the client's plan_type.

    Returns {"subscription_id": str, "short_url": str}.
    """
    db = get_supabase()
    result = (
        db.table("clients")
        .select("agent_name, agent_email, agent_phone, razorpay_customer_id, plan_type")
        .eq("id", client_id)
        .single()
        .execute()
    )
    client = result.data

    plan_type: str = client.get("plan_type") or "pro"

    # Select the right Razorpay plan ID
    if plan_type == "starter" and settings.RAZORPAY_STARTER_PLAN_ID:
        plan_id = settings.RAZORPAY_STARTER_PLAN_ID
    elif settings.RAZORPAY_PLAN_ID:
        plan_id = settings.RAZORPAY_PLAN_ID
    else:
        raise ValueError("Razorpay plan ID not configured")

    cust_id: str | None = client.get("razorpay_customer_id")
    if not cust_id:
        cust_id = await create_razorpay_customer(
            client_id=client_id,
            name=client["agent_name"],
            email=client["agent_email"],
            phone=client["agent_phone"],
        )

    rz = _get_razorpay_client()
    sub = await asyncio.to_thread(
        rz.subscription.create,
        {
            "plan_id": plan_id,
            "customer_id": cust_id,
            "total_count": 120,
            "customer_notify": 1,
            "notes": {"client_id": client_id, "plan_type": plan_type},
        },
    )
    sub_id: str = sub["id"]
    logger.info("Created Razorpay subscription %s for client %s", sub_id, client_id)

    db.table("clients").update({"razorpay_subscription_id": sub_id}).eq(
        "id", client_id
    ).execute()

    return {"subscription_id": sub_id, "short_url": sub["short_url"]}


async def handle_razorpay_webhook(payload: dict, signature: str) -> None:
    """
    Verify a Razorpay webhook signature and process the event.

    Raises ValueError if the signature is invalid.
    """
    rz = _get_razorpay_client()

    # Verify signature — raises razorpay.errors.SignatureVerificationError on failure
    try:
        rz.utility.verify_webhook_signature(
            json.dumps(payload, separators=(",", ":")),
            signature,
            settings.RAZORPAY_WEBHOOK_SECRET,
        )
    except Exception as exc:
        logger.warning("Razorpay webhook signature verification failed: %s", exc)
        raise ValueError("Invalid Razorpay webhook signature") from exc

    event: str = payload.get("event", "")
    try:
        sub_id: str = payload["payload"]["subscription"]["entity"]["id"]
    except (KeyError, TypeError) as exc:
        logger.error("Could not extract subscription ID from webhook payload: %s", exc)
        return

    # Look up the client
    db = get_supabase()
    result = (
        db.table("clients")
        .select("id, agent_email, agent_name, exotel_number")
        .eq("razorpay_subscription_id", sub_id)
        .execute()
    )
    if not result.data:
        logger.warning(
            "No client found for Razorpay subscription %s (event: %s)", sub_id, event
        )
        return

    client = result.data[0]
    client_id: str = client["id"]

    logger.info("Razorpay event '%s' for client %s (sub %s)", event, client_id, sub_id)

    if event == "subscription.activated":
        db.table("clients").update({"subscription_status": "active"}).eq(
            "id", client_id
        ).execute()
        logger.info("Subscription activated for client %s", client_id)

        # Assign a phone number if the client doesn't have one yet
        if not client.get("exotel_number"):
            from app.services.phone_service import assign_phone_number  # noqa: PLC0415

            await assign_phone_number(client_id)

    elif event == "subscription.charged":
        logger.info(
            "Subscription charge successful for client %s (sub %s)", client_id, sub_id
        )

    elif event == "subscription.cancelled":
        db.table("clients").update({"subscription_status": "cancelled"}).eq(
            "id", client_id
        ).execute()
        logger.info("Subscription cancelled for client %s", client_id)

        from app.services.phone_service import release_phone_number  # noqa: PLC0415

        await release_phone_number(client_id)

    elif event == "subscription.paused":
        db.table("clients").update({"subscription_status": "paused"}).eq(
            "id", client_id
        ).execute()
        logger.info("Subscription paused for client %s", client_id)

    elif event == "payment.failed":
        logger.warning(
            "Payment failed for client %s (sub %s)", client_id, sub_id
        )

        agent_email: str = client.get("agent_email", "")
        if agent_email and settings.SMTP_EMAIL:
            from app.services import alert_service  # noqa: PLC0415

            asyncio.ensure_future(
                asyncio.to_thread(
                    alert_service._send_email,
                    to=agent_email,
                    subject="PropBot: Payment failed — action required",
                    body=(
                        "<h2>Payment Failed</h2>"
                        "<p>We were unable to process your PropBot subscription payment.</p>"
                        "<p>Please update your payment details to keep your AI receptionist active.</p>"
                        "<p>If you need help, reply to this email or contact PropBot support.</p>"
                    ),
                )
            )
    else:
        logger.debug("Unhandled Razorpay event '%s' — ignoring", event)


async def check_subscription_active(client_id: str) -> bool:
    """
    Return True if the client's subscription is currently active.

    Active means either:
    - subscription_status == 'active', or
    - subscription_status == 'trial' and trial_ends_at is in the future.
    """
    db = get_supabase()
    result = (
        db.table("clients")
        .select("subscription_status, trial_ends_at")
        .eq("id", client_id)
        .single()
        .execute()
    )
    client = result.data

    status: str = client.get("subscription_status", "")

    if status == "active":
        return True

    if status == "trial":
        trial_ends_at_raw: str | None = client.get("trial_ends_at")
        if trial_ends_at_raw:
            # Supabase returns ISO-8601; normalise timezone offset for fromisoformat
            trial_ends_at = datetime.fromisoformat(
                trial_ends_at_raw.replace("Z", "+00:00")
            )
            if trial_ends_at > datetime.now(timezone.utc):
                return True

        # Trial has expired — mark as 'expired' (write-on-read, no cron needed)
        db.table("clients").update({"subscription_status": "expired"}).eq(
            "id", client_id
        ).execute()
        logger.info("Auto-expired trial for client %s", client_id)

    return False


async def cancel_subscription(client_id: str) -> None:
    """
    Cancel the Razorpay subscription for a client immediately and release their phone number.
    """
    db = get_supabase()
    result = (
        db.table("clients")
        .select("razorpay_subscription_id")
        .eq("id", client_id)
        .single()
        .execute()
    )
    sub_id: str | None = result.data.get("razorpay_subscription_id")

    if sub_id:
        rz = _get_razorpay_client()
        await asyncio.to_thread(rz.subscription.cancel, sub_id)
        logger.info(
            "Cancelled Razorpay subscription %s for client %s", sub_id, client_id
        )
    else:
        logger.warning(
            "No Razorpay subscription ID found for client %s — skipping cancellation",
            client_id,
        )

    db.table("clients").update({"subscription_status": "cancelled"}).eq(
        "id", client_id
    ).execute()

    from app.services.phone_service import release_phone_number  # noqa: PLC0415

    await release_phone_number(client_id)
