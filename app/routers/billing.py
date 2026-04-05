"""
Billing router — Razorpay subscription management for PropBot.

Endpoints:
  POST /api/billing/subscribe       Create Razorpay subscription, return checkout URL.
  POST /api/billing/razorpay        Razorpay webhook receiver.
  GET  /api/billing/status          Return current billing status for logged-in client.
  POST /api/billing/cancel          Cancel subscription.
"""

import hashlib
import hmac
import json
import logging
import time

from fastapi import APIRouter, HTTPException, Request, Response

from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_client_id_from_session(request: Request) -> str:
    """Extract and validate client ID from the propbot_session cookie."""
    token = request.cookies.get("propbot_session")
    if not token:
        raise HTTPException(status_code=401, detail="Not logged in")
    try:
        client_id, ts_str, sig = token.split(":")
        ts = int(ts_str)
        if time.time() - ts > 7 * 24 * 3600:
            raise HTTPException(status_code=401, detail="Session expired")
        secret = (settings.WEBHOOK_SECRET or "propbot-default-secret").encode()
        expected = hmac.new(secret, f"{client_id}:{ts}".encode(), hashlib.sha256).hexdigest()[:32]
        if hmac.compare_digest(sig, expected):
            return client_id
    except (ValueError, AttributeError):
        pass
    raise HTTPException(status_code=401, detail="Invalid session")


@router.post("/subscribe")
async def subscribe(request: Request):
    """Create Razorpay subscription, return checkout URL. Requires session."""
    client_id = _get_client_id_from_session(request)
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_PLAN_ID:
        raise HTTPException(status_code=503, detail="Billing not configured")
    logger.info("Creating Razorpay subscription for client %s", client_id)
    from app.services.billing_service import create_subscription
    try:
        result = await create_subscription(client_id)
        return {"checkout_url": result["short_url"]}
    except Exception as e:
        logger.error("Subscription creation failed for client %s: %s", client_id, e)
        raise HTTPException(status_code=500, detail=f"Subscription error: {str(e)}")


@router.post("/razorpay")
async def razorpay_webhook(request: Request):
    """Razorpay webhook receiver. Verifies X-Razorpay-Signature header."""
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature header")

    payload = json.loads(body)
    logger.info("Received Razorpay webhook event: %s", payload.get("event"))

    from app.services.billing_service import handle_razorpay_webhook
    try:
        await handle_razorpay_webhook(payload, signature)
    except ValueError:
        logger.warning("Invalid Razorpay webhook signature")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    return Response(status_code=200)


@router.get("/status")
async def billing_status(request: Request):
    """Return current billing status for logged-in client."""
    client_id = _get_client_id_from_session(request)
    logger.info("Fetching billing status for client %s", client_id)
    from app.db.supabase_client import get_supabase
    from app.services.billing_service import PLAN_FEES_INR, STARTER_CALLS_LIMIT
    db = get_supabase()
    result = db.table("clients").select(
        "subscription_status, trial_ends_at, monthly_fee_inr, razorpay_subscription_id, plan_type"
    ).eq("id", client_id).single().execute()
    data = result.data or {}
    plan_type = data.get("plan_type") or "pro"
    data["plan_type"] = plan_type
    data["monthly_fee_inr"] = PLAN_FEES_INR.get(plan_type, 4999)
    data["calls_limit"] = STARTER_CALLS_LIMIT if plan_type == "starter" else None
    return data


@router.post("/cancel")
async def cancel(request: Request):
    """Cancel subscription. Requires session."""
    client_id = _get_client_id_from_session(request)
    logger.info("Cancelling subscription for client %s", client_id)
    from app.services.billing_service import cancel_subscription
    await cancel_subscription(client_id)
    return {"status": "cancelled"}
