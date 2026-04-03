"""
Client Dashboard — magic-link login + leads view + KB editor.

Serves a single-page dashboard app. Authentication via:
1. Magic link: GET /dashboard/login?email=x → sends email with token
2. Token login: GET /dashboard/auth?token=x → sets session cookie
3. API key: Authorization: Bearer pb_xxx (for API access)
"""

import hashlib
import hmac
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from app.config import settings
from app.db.supabase_client import get_supabase

router = APIRouter()
logger = logging.getLogger(__name__)

# Token validity: 15 minutes
MAGIC_LINK_TTL = 15 * 60


def _make_token(email: str, ts: int) -> str:
    """Create an HMAC token for magic link auth."""
    secret = (settings.WEBHOOK_SECRET or "propbot-default-secret").encode()
    payload = f"{email}:{ts}".encode()
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def _make_session_token(client_id: str) -> str:
    """Create a session token (HMAC of client_id + timestamp)."""
    secret = (settings.WEBHOOK_SECRET or "propbot-default-secret").encode()
    ts = int(time.time())
    payload = f"{client_id}:{ts}".encode()
    sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()[:32]
    return f"{client_id}:{ts}:{sig}"


def _verify_session(token: str) -> str | None:
    """Verify session token, return client_id or None."""
    try:
        client_id, ts_str, sig = token.split(":")
        ts = int(ts_str)
        # Sessions valid for 7 days
        if time.time() - ts > 7 * 24 * 3600:
            return None
        secret = (settings.WEBHOOK_SECRET or "propbot-default-secret").encode()
        expected = hmac.new(secret, f"{client_id}:{ts}".encode(), hashlib.sha256).hexdigest()[:32]
        if hmac.compare_digest(sig, expected):
            return client_id
    except (ValueError, AttributeError):
        pass
    return None


def _get_client_id_from_session(request: Request) -> str:
    """Extract and verify client_id from session cookie."""
    token = request.cookies.get("propbot_session")
    if not token:
        raise HTTPException(status_code=401, detail="Not logged in")
    client_id = _verify_session(token)
    if not client_id:
        raise HTTPException(status_code=401, detail="Session expired")
    return client_id


# ─── Magic Link Login ───────────────────────────────────────────

@router.get("/login")
async def request_magic_link(email: str = Query(...)):
    """Send a magic login link to the agent's email."""
    db = get_supabase()
    result = db.table("clients").select("id, agent_email, business_name").eq("agent_email", email).limit(1).execute()
    if not result.data:
        # Don't reveal whether email exists
        return {"message": "If that email is registered, a login link has been sent."}

    client = result.data[0]
    ts = int(time.time())
    token = _make_token(email, ts)
    login_url = f"{settings.BASE_URL}/dashboard/auth?email={email}&ts={ts}&token={token}"

    # Send email with login link
    if settings.SMTP_EMAIL:
        import asyncio
        from app.services.alert_service import _send_email
        try:
            await asyncio.to_thread(
                _send_email,
                to=email,
                subject=f"PropBot Dashboard Login — {client['business_name']}",
                body=f"""
                <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto;">
                    <h2 style="color: #2563eb;">PropBot Dashboard Login</h2>
                    <p>Click the button below to login to your dashboard:</p>
                    <a href="{login_url}"
                       style="display:inline-block;padding:12px 32px;background:#2563eb;color:#fff;text-decoration:none;border-radius:8px;font-weight:bold;">
                       Login to Dashboard
                    </a>
                    <p style="color:#666;font-size:13px;margin-top:16px;">
                        This link expires in 15 minutes. If you didn't request this, ignore this email.
                    </p>
                </div>
                """,
            )
        except Exception as e:
            logger.error(f"Failed to send magic link: {e}")

    return {"message": "If that email is registered, a login link has been sent."}


@router.get("/auth")
async def verify_magic_link(email: str, ts: int, token: str):
    """Verify magic link token and set session cookie."""
    # Check expiry
    if time.time() - ts > MAGIC_LINK_TTL:
        return HTMLResponse("<h2>Link expired. Please request a new login link.</h2>", status_code=401)

    # Verify token
    expected = _make_token(email, ts)
    if not hmac.compare_digest(token, expected):
        return HTMLResponse("<h2>Invalid link.</h2>", status_code=401)

    # Find client
    db = get_supabase()
    result = db.table("clients").select("id").eq("agent_email", email).limit(1).execute()
    if not result.data:
        return HTMLResponse("<h2>Account not found.</h2>", status_code=404)

    client_id = result.data[0]["id"]
    session_token = _make_session_token(client_id)

    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        "propbot_session",
        session_token,
        max_age=7 * 24 * 3600,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/logout")
async def logout():
    """Clear session and redirect to login."""
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.delete_cookie("propbot_session")
    return response


# ─── Dashboard API (JSON) ───────────────────────────────────────

@router.get("/api/me")
async def get_my_profile(client_id: str = Depends(_get_client_id_from_session)):
    """Get current client profile."""
    db = get_supabase()
    result = db.table("clients").select(
        "id, business_name, agent_name, agent_email, agent_phone, "
        "assistant_persona_name, subscription_status, trial_ends_at, "
        "exotel_number, setup_status, bolna_agent_id, created_at"
    ).eq("id", client_id).single().execute()
    return result.data


@router.get("/api/leads")
async def get_my_leads(
    client_id: str = Depends(_get_client_id_from_session),
    limit: int = Query(default=50, le=200),
    status: str | None = Query(default=None),
):
    """Get leads for the logged-in client."""
    db = get_supabase()
    query = (
        db.table("leads")
        .select("*")
        .eq("client_id", client_id)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    result = query.execute()
    return {"leads": result.data, "count": len(result.data)}


@router.patch("/api/leads/{lead_id}")
async def update_my_lead(
    lead_id: str,
    request: Request,
    client_id: str = Depends(_get_client_id_from_session),
):
    """Update a lead's status/notes."""
    body = await request.json()
    allowed = {"status", "notes"}
    update_data = {k: v for k, v in body.items() if k in allowed}
    if not update_data:
        raise HTTPException(400, "Nothing to update")

    db = get_supabase()
    result = (
        db.table("leads")
        .update(update_data)
        .eq("id", lead_id)
        .eq("client_id", client_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Lead not found")
    return result.data[0]


@router.get("/api/stats")
async def get_my_stats(client_id: str = Depends(_get_client_id_from_session)):
    """Quick stats for the dashboard header."""
    db = get_supabase()
    leads = db.table("leads").select("status, created_at").eq("client_id", client_id).execute()
    all_leads = leads.data or []

    now = datetime.now(timezone.utc)
    this_month = [l for l in all_leads if l.get("created_at", "")[:7] == now.strftime("%Y-%m")]

    status_counts = {}
    for l in all_leads:
        s = l.get("status", "new")
        status_counts[s] = status_counts.get(s, 0) + 1

    convos = db.table("conversations").select("created_at").eq("client_id", client_id).execute()
    all_convos = convos.data or []
    calls_this_month = len([c for c in all_convos if c.get("created_at", "")[:7] == now.strftime("%Y-%m")])

    return {
        "total_leads": len(all_leads),
        "this_month": len(this_month),
        "by_status": status_counts,
        "new": status_counts.get("new", 0),
        "contacted": status_counts.get("contacted", 0),
        "qualified": status_counts.get("qualified", 0),
        "converted": status_counts.get("converted", 0),
        "total_calls": len(all_convos),
        "calls_this_month": calls_this_month,
    }


@router.get("/api/callbacks")
async def get_my_callbacks(client_id: str = Depends(_get_client_id_from_session)):
    """Get callback requests."""
    db = get_supabase()
    result = (
        db.table("callback_requests")
        .select("*")
        .eq("client_id", client_id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    return {"callbacks": result.data, "count": len(result.data)}


@router.get("/api/conversations")
async def get_my_conversations(
    client_id: str = Depends(_get_client_id_from_session),
    limit: int = Query(default=50, le=200),
):
    """Get call/chat history for the logged-in client."""
    db = get_supabase()
    result = (
        db.table("conversations")
        .select("id, source, call_id, transcript, recording_url, duration_seconds, ended_reason, language_detected, created_at, lead_id")
        .eq("client_id", client_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return {"conversations": result.data, "count": len(result.data)}


@router.get("/api/embed-code")
async def get_embed_code(client_id: str = Depends(_get_client_id_from_session)):
    """Get the chat widget embed code for this client."""
    db = get_supabase()
    result = db.table("clients").select("id, assistant_persona_name").eq("id", client_id).single().execute()
    client = result.data
    persona = client.get("assistant_persona_name", "Priya")
    return {
        "embed_code": (
            f'<script src="{settings.BASE_URL}/static/chat-widget.js"\n'
            f'        data-client-id="{client_id}"\n'
            f'        data-api-url="{settings.BASE_URL}"\n'
            f'        data-persona-name="{persona}"\n'
            f'        data-subtitle="Property Assistant"></script>'
        )
    }


# ─── Admin: Phone Pool ─────────────────────────────────────────

def _require_admin(request: Request) -> None:
    """Simple admin auth via Authorization: Bearer {WEBHOOK_SECRET}."""
    auth = request.headers.get("Authorization", "")
    secret = settings.WEBHOOK_SECRET
    if not secret or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Admin auth required")
    token = auth[len("Bearer "):]
    if not hmac.compare_digest(token, secret):
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.post("/api/admin/phone-pool")
async def seed_phone_pool(request: Request):
    """Add phone numbers to the pool. Auth: Bearer {WEBHOOK_SECRET}."""
    _require_admin(request)
    body = await request.json()
    numbers = body.get("numbers", [])
    if not numbers:
        raise HTTPException(400, "Provide a 'numbers' list")
    db = get_supabase()
    added = 0
    for num in numbers:
        num = str(num).strip()
        if not num:
            continue
        try:
            db.table("phone_number_pool").insert({"phone_number": num}).execute()
            added += 1
        except Exception:
            pass  # Skip duplicates
    return {"added": added, "total_submitted": len(numbers)}


@router.get("/api/admin/phone-pool")
async def get_phone_pool_status(request: Request):
    """Get phone pool stats. Auth: Bearer {WEBHOOK_SECRET}."""
    _require_admin(request)
    from app.services.phone_service import get_pool_stats
    return await get_pool_stats()


# ─── Calendar OAuth ─────────────────────────────────────────────

@router.get("/api/calendar/status")
async def calendar_status(client_id: str = Depends(_get_client_id_from_session)):
    """Returns whether Google Calendar is connected."""
    from app.services.calendar_service import is_calendar_connected
    connected = await is_calendar_connected(client_id)
    return {"connected": connected}


@router.get("/google/connect")
async def connect_google_calendar(request: Request):
    """Redirect to Google OAuth consent screen."""
    client_id = _get_client_id_from_session(request)
    from app.services.calendar_service import get_oauth_url
    url = await get_oauth_url(client_id)
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_oauth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
):
    """Google OAuth callback. state = client_id."""
    from app.services.calendar_service import handle_oauth_callback
    await handle_oauth_callback(code=code, client_id=state)
    return RedirectResponse("/dashboard")


@router.post("/google/disconnect")
async def disconnect_google_calendar(client_id: str = Depends(_get_client_id_from_session)):
    """Remove Google Calendar connection."""
    from app.services.calendar_service import disconnect_calendar
    await disconnect_calendar(client_id)
    return {"status": "disconnected"}


# ─── Dashboard HTML (SPA) ───────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Serve the dashboard SPA."""
    # Check if logged in
    token = request.cookies.get("propbot_session")
    logged_in = bool(token and _verify_session(token))

    return DASHBOARD_HTML.replace("__LOGGED_IN__", "true" if logged_in else "false")


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PropBot Dashboard</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8fafc; color: #1e293b; }
.container { max-width: 1100px; margin: 0 auto; padding: 20px; }

/* Header */
.header { display: flex; justify-content: space-between; align-items: center; padding: 16px 0; margin-bottom: 24px; border-bottom: 1px solid #e2e8f0; }
.header h1 { font-size: 22px; color: #1e293b; }
.header h1 span { color: #2563eb; }
.header-right { display: flex; align-items: center; gap: 12px; }
.biz-name { font-size: 14px; color: #64748b; }
.btn-logout { padding: 6px 14px; font-size: 13px; background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 6px; cursor: pointer; color: #475569; }
.btn-logout:hover { background: #e2e8f0; }

/* Login */
.login-box { max-width: 400px; margin: 80px auto; padding: 40px; background: #fff; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); text-align: center; }
.login-box h2 { margin-bottom: 8px; font-size: 24px; }
.login-box p { color: #64748b; margin-bottom: 24px; font-size: 14px; }
.login-box input { width: 100%; padding: 12px 16px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 15px; margin-bottom: 12px; }
.login-box input:focus { outline: none; border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,0.1); }
.btn-primary { width: 100%; padding: 12px; background: #2563eb; color: #fff; border: none; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; }
.btn-primary:hover { background: #1d4ed8; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.login-msg { margin-top: 12px; font-size: 13px; color: #059669; }

/* Stats */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
.stat-card { background: #fff; padding: 20px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.stat-card .label { font-size: 13px; color: #64748b; margin-bottom: 4px; }
.stat-card .value { font-size: 28px; font-weight: 700; color: #1e293b; }
.stat-card .value.blue { color: #2563eb; }
.stat-card .value.green { color: #059669; }
.stat-card .value.orange { color: #d97706; }

/* Tabs */
.tabs { display: flex; gap: 4px; margin-bottom: 20px; border-bottom: 2px solid #e2e8f0; }
.tab { padding: 10px 20px; font-size: 14px; font-weight: 500; color: #64748b; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; background: none; border-top: none; border-left: none; border-right: none; }
.tab:hover { color: #1e293b; }
.tab.active { color: #2563eb; border-bottom-color: #2563eb; }

/* Leads Table */
.leads-table { width: 100%; background: #fff; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); overflow: hidden; }
.leads-table table { width: 100%; border-collapse: collapse; }
.leads-table th { text-align: left; padding: 12px 16px; font-size: 12px; font-weight: 600; color: #64748b; background: #f8fafc; text-transform: uppercase; letter-spacing: 0.5px; }
.leads-table td { padding: 12px 16px; font-size: 14px; border-top: 1px solid #f1f5f9; }
.leads-table tr:hover td { background: #f8fafc; }
.status-badge { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 500; }
.status-new { background: #dbeafe; color: #1d4ed8; }
.status-contacted { background: #fef3c7; color: #92400e; }
.status-qualified { background: #d1fae5; color: #065f46; }
.status-converted { background: #059669; color: #fff; }
.status-lost { background: #fee2e2; color: #991b1b; }
.status-select { padding: 4px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 12px; cursor: pointer; }
.phone-link { color: #2563eb; text-decoration: none; }
.phone-link:hover { text-decoration: underline; }

/* Embed Code */
.embed-box { background: #fff; padding: 24px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.embed-box h3 { margin-bottom: 12px; }
.embed-box pre { background: #1e293b; color: #e2e8f0; padding: 16px; border-radius: 8px; font-size: 13px; overflow-x: auto; white-space: pre-wrap; }
.btn-copy { margin-top: 12px; padding: 8px 20px; background: #2563eb; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; }
.btn-copy:hover { background: #1d4ed8; }

.empty-state { text-align: center; padding: 60px 20px; color: #94a3b8; }
.empty-state h3 { margin-bottom: 8px; color: #64748b; }

/* Calls Table */
.calls-table { width: 100%; background: #fff; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); overflow: hidden; }
.calls-table table { width: 100%; border-collapse: collapse; }
.calls-table th { text-align: left; padding: 12px 16px; font-size: 12px; font-weight: 600; color: #64748b; background: #f8fafc; text-transform: uppercase; letter-spacing: 0.5px; }
.calls-table td { padding: 12px 16px; font-size: 14px; border-top: 1px solid #f1f5f9; vertical-align: top; }
.calls-table tr:hover td { background: #f8fafc; }
.calls-table tr.expanded td { background: #f0f4ff; }
.duration-badge { display: inline-block; padding: 2px 8px; background: #f1f5f9; border-radius: 10px; font-size: 12px; color: #475569; }
.source-badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.source-voice { background: #dbeafe; color: #1d4ed8; }
.source-chat { background: #d1fae5; color: #065f46; }
.btn-expand { padding: 4px 10px; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; font-size: 12px; cursor: pointer; color: #475569; }
.btn-expand:hover { background: #f1f5f9; }
.transcript-row td { padding: 0 16px 16px; }
.transcript-box { background: #1e293b; color: #e2e8f0; padding: 16px; border-radius: 8px; font-size: 13px; font-family: monospace; line-height: 1.6; max-height: 300px; overflow-y: auto; white-space: pre-wrap; }
.audio-player { margin-top: 10px; }
.audio-player audio { width: 100%; border-radius: 6px; }
.no-recording { color: #94a3b8; font-size: 13px; font-style: italic; }

/* Phone Number Banner */
.phone-banner { display: flex; align-items: center; gap: 10px; padding: 14px 20px; border-radius: 10px; margin-bottom: 20px; font-size: 14px; font-weight: 500; }
.phone-banner.ready { background: #ecfdf5; border: 1px solid #6ee7b7; color: #065f46; }
.phone-banner.provisioning { background: #eff6ff; border: 1px solid #93c5fd; color: #1d4ed8; }
.phone-banner.failed { background: #fef2f2; border: 1px solid #fca5a5; color: #991b1b; }
.phone-number { font-size: 18px; font-weight: 700; letter-spacing: 0.5px; }

/* Trial Warning */
.trial-warning { background: #fffbeb; border: 1px solid #fcd34d; color: #92400e; padding: 12px 20px; border-radius: 10px; margin-bottom: 16px; font-size: 14px; }
.trial-expired { background: #fef2f2; border: 1px solid #fca5a5; color: #991b1b; padding: 12px 20px; border-radius: 10px; margin-bottom: 16px; font-size: 14px; }
.trial-warning a, .trial-expired a { font-weight: 600; color: inherit; text-decoration: underline; cursor: pointer; }

/* Billing Tab */
.billing-box { background: #fff; padding: 32px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); max-width: 600px; }
.billing-box h3 { font-size: 18px; margin-bottom: 6px; }
.billing-box .sub-label { color: #64748b; font-size: 14px; margin-bottom: 24px; }
.billing-status-badge { display: inline-block; padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; margin-bottom: 20px; }
.badge-trial { background: #dbeafe; color: #1d4ed8; }
.badge-active { background: #d1fae5; color: #065f46; }
.badge-paused { background: #fef3c7; color: #92400e; }
.badge-cancelled { background: #fee2e2; color: #991b1b; }
.billing-amount { font-size: 32px; font-weight: 700; color: #1e293b; margin-bottom: 4px; }
.billing-period { color: #64748b; font-size: 14px; margin-bottom: 24px; }
.btn-subscribe { padding: 14px 28px; background: #2563eb; color: #fff; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; }
.btn-subscribe:hover { background: #1d4ed8; }
.btn-subscribe:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-cancel-sub { padding: 10px 20px; background: #fff; color: #ef4444; border: 1px solid #fca5a5; border-radius: 8px; font-size: 14px; cursor: pointer; margin-top: 12px; }
.btn-cancel-sub:hover { background: #fef2f2; }
.trial-info { color: #64748b; font-size: 13px; margin-top: 16px; }

/* Calendar Tab */
.calendar-box { background: #fff; padding: 32px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); max-width: 600px; }
.calendar-box h3 { font-size: 18px; margin-bottom: 6px; }
.calendar-box .sub-label { color: #64748b; font-size: 14px; margin-bottom: 24px; }
.calendar-connected { display: flex; align-items: center; gap: 12px; padding: 16px; background: #ecfdf5; border: 1px solid #6ee7b7; border-radius: 10px; margin-bottom: 16px; }
.calendar-connected span { font-weight: 600; color: #065f46; }
.btn-connect-cal { padding: 12px 24px; background: #fff; color: #1e293b; border: 1px solid #d1d5db; border-radius: 8px; font-size: 15px; font-weight: 500; cursor: pointer; display: flex; align-items: center; gap: 8px; }
.btn-connect-cal:hover { background: #f8fafc; border-color: #2563eb; color: #2563eb; }
.btn-disconnect-cal { padding: 8px 16px; background: #fff; color: #64748b; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 13px; cursor: pointer; }
.btn-disconnect-cal:hover { background: #f8fafc; }
.calendar-benefit { display: flex; gap: 10px; padding: 12px 0; border-bottom: 1px solid #f1f5f9; font-size: 14px; color: #475569; }
.calendar-benefit:last-child { border-bottom: none; }

/* Mobile */
@media (max-width: 768px) {
  .leads-table { overflow-x: auto; }
  .calls-table { overflow-x: auto; }
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .tabs { overflow-x: auto; }
  .header { flex-direction: column; gap: 12px; align-items: flex-start; }
}
</style>
</head>
<body>
<div class="container" id="app"></div>

<script>
(function() {
  var loggedIn = __LOGGED_IN__;
  var app = document.getElementById('app');
  var profile = null;
  var stats = null;
  var leads = [];
  var conversations = [];
  var activeTab = 'leads';

  if (!loggedIn) {
    renderLogin();
  } else {
    loadDashboard();
  }

  function renderLogin() {
    app.innerHTML =
      '<div class="login-box">' +
        '<h2>PropBot Dashboard</h2>' +
        '<p>Enter your registered email to receive a login link</p>' +
        '<input type="email" id="login-email" placeholder="your@email.com" />' +
        '<button class="btn-primary" id="login-btn">Send Login Link</button>' +
        '<div class="login-msg" id="login-msg" style="display:none"></div>' +
      '</div>';

    document.getElementById('login-btn').addEventListener('click', function() {
      var email = document.getElementById('login-email').value.trim();
      if (!email) return;
      var btn = this;
      btn.disabled = true;
      btn.textContent = 'Sending...';
      fetch('/dashboard/login?email=' + encodeURIComponent(email))
        .then(function(r) { return r.json(); })
        .then(function(data) {
          var msg = document.getElementById('login-msg');
          msg.style.display = 'block';
          msg.textContent = 'Login link sent! Check your email.';
          btn.textContent = 'Link Sent';
        })
        .catch(function() {
          btn.disabled = false;
          btn.textContent = 'Send Login Link';
          alert('Error sending link. Try again.');
        });
    });

    document.getElementById('login-email').addEventListener('keydown', function(e) {
      if (e.key === 'Enter') document.getElementById('login-btn').click();
    });
  }

  function loadDashboard() {
    app.innerHTML = '<div style="text-align:center;padding:60px;color:#64748b;">Loading dashboard...</div>';
    Promise.all([
      fetch('/dashboard/api/me').then(function(r) { return r.ok ? r.json() : Promise.reject(); }),
      fetch('/dashboard/api/stats').then(function(r) { return r.ok ? r.json() : Promise.reject(); }),
      fetch('/dashboard/api/leads').then(function(r) { return r.ok ? r.json() : Promise.reject(); }),
      fetch('/dashboard/api/conversations').then(function(r) { return r.ok ? r.json() : {conversations: []}; }),
    ]).then(function(results) {
      profile = results[0];
      stats = results[1];
      leads = results[2].leads || [];
      conversations = results[3].conversations || [];
      render();
    }).catch(function() {
      // Session expired
      loggedIn = false;
      renderLogin();
    });
  }

  function render() {
    var html =
      '<div class="header">' +
        '<h1><span>PropBot</span> Dashboard</h1>' +
        '<div class="header-right">' +
          '<span class="biz-name">' + esc(profile.business_name) + ' &mdash; ' + esc(profile.agent_name) + '</span>' +
          '<button class="btn-logout" onclick="location.href=\\'/dashboard/logout\\'">Logout</button>' +
        '</div>' +
      '</div>';

    // Phone number banner
    if (profile.setup_status === 'ready' && profile.exotel_number) {
      html += '<div class="phone-banner ready">' +
        '<span>&#128222;</span>' +
        '<div>' +
          '<div>Your AI Receptionist Number</div>' +
          '<div class="phone-number">' + esc(profile.exotel_number) + '</div>' +
        '</div>' +
        '<div style="margin-left:auto;font-size:13px;color:#059669;">Share this number with your clients!</div>' +
      '</div>';
    } else if (profile.setup_status === 'provisioning') {
      html += '<div class="phone-banner provisioning">' +
        '<span>&#9203;</span>' +
        '<span>Setting up your phone number... This may take a minute. Refresh the page shortly.</span>' +
      '</div>';
    } else if (profile.setup_status === 'failed') {
      html += '<div class="phone-banner failed">' +
        '<span>&#9888;</span>' +
        '<span>Phone number setup pending. Please contact support.</span>' +
      '</div>';
    }

    // Trial warning
    if (profile.subscription_status === 'trial' && profile.trial_ends_at) {
      var daysLeft = Math.ceil((new Date(profile.trial_ends_at) - new Date()) / 86400000);
      if (daysLeft <= 0) {
        html += '<div class="trial-expired">&#9888; Your trial has expired. <a onclick="switchTab(\'billing\')">Subscribe now</a> to reactivate your AI receptionist.</div>';
      } else if (daysLeft <= 3) {
        html += '<div class="trial-warning">&#9888; Your trial expires in ' + daysLeft + ' day' + (daysLeft === 1 ? '' : 's') + '. <a onclick="switchTab(\'billing\')">Subscribe now</a> to keep your AI receptionist active.</div>';
      }
    }

    // Stats
    html +=
      '<div class="stats-grid">' +
        statCard('Total Calls', stats.total_calls, 'blue') +
        statCard('Calls This Month', stats.calls_this_month, 'blue') +
        statCard('Total Leads', stats.total_leads, 'orange') +
        statCard('Converted', stats.converted, 'green') +
      '</div>';

    // Tabs
    html +=
      '<div class="tabs">' +
        tabBtn('leads', 'Leads') +
        tabBtn('calls', 'Call History') +
        tabBtn('embed', 'Widget Code') +
        tabBtn('billing', 'Billing') +
        tabBtn('calendar', 'Calendar') +
      '</div>';

    // Content
    html += '<div id="tab-content"></div>';
    app.innerHTML = html;

    // Tab clicks
    document.querySelectorAll('.tab').forEach(function(t) {
      t.addEventListener('click', function() {
        activeTab = this.dataset.tab;
        document.querySelectorAll('.tab').forEach(function(x) { x.classList.remove('active'); });
        this.classList.add('active');
        renderTabContent();
      });
    });

    renderTabContent();
  }

  function renderTabContent() {
    var el = document.getElementById('tab-content');
    if (activeTab === 'leads') {
      renderLeads(el);
    } else if (activeTab === 'calls') {
      renderCalls(el);
    } else if (activeTab === 'embed') {
      renderEmbed(el);
    } else if (activeTab === 'billing') {
      renderBilling(el);
    } else if (activeTab === 'calendar') {
      renderCalendar(el);
    }
  }

  function renderLeads(el) {
    if (!leads.length) {
      el.innerHTML = '<div class="empty-state"><h3>No leads yet</h3><p>Leads will appear here when callers interact with your AI receptionist.</p></div>';
      return;
    }
    var html = '<div class="leads-table"><table><thead><tr>' +
      '<th>Name</th><th>Phone</th><th>Looking For</th><th>Budget</th><th>Status</th><th>Date</th>' +
      '</tr></thead><tbody>';
    leads.forEach(function(l) {
      var budget = '';
      if (l.budget_min && l.budget_max) budget = '₹' + fmt(l.budget_min) + ' - ₹' + fmt(l.budget_max);
      else if (l.budget_min) budget = '₹' + fmt(l.budget_min) + '+';
      else if (l.budget_max) budget = 'Up to ₹' + fmt(l.budget_max);

      var lookingFor = [l.property_type, l.preferred_area].filter(Boolean).join(', ') || '-';
      var date = l.created_at ? new Date(l.created_at).toLocaleDateString('en-IN', {day:'numeric',month:'short',year:'numeric'}) : '-';

      html += '<tr>' +
        '<td>' + esc(l.caller_name || '-') + '</td>' +
        '<td><a class="phone-link" href="tel:' + esc(l.caller_phone || '') + '">' + esc(l.caller_phone || '-') + '</a></td>' +
        '<td>' + esc(lookingFor) + '</td>' +
        '<td>' + esc(budget) + '</td>' +
        '<td>' + statusSelect(l) + '</td>' +
        '<td>' + esc(date) + '</td>' +
        '</tr>';
    });
    html += '</tbody></table></div>';
    el.innerHTML = html;

    // Status change handlers
    el.querySelectorAll('.status-select').forEach(function(sel) {
      sel.addEventListener('change', function() {
        var leadId = this.dataset.id;
        var newStatus = this.value;
        fetch('/dashboard/api/leads/' + leadId, {
          method: 'PATCH',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({status: newStatus})
        }).then(function(r) {
          if (!r.ok) throw new Error();
          // Update local data
          leads.forEach(function(l) { if (l.id === leadId) l.status = newStatus; });
        }).catch(function() { alert('Failed to update status'); });
      });
    });
  }

  function renderCalls(el) {
    if (!conversations.length) {
      el.innerHTML = '<div class="empty-state"><h3>No calls yet</h3><p>Call recordings and transcripts will appear here after your first AI-handled call.</p></div>';
      return;
    }
    var html = '<div class="calls-table"><table><thead><tr>' +
      '<th>Date &amp; Time</th><th>Type</th><th>Duration</th><th>Ended Reason</th><th>Recording</th><th></th>' +
      '</tr></thead><tbody id="calls-tbody">';
    conversations.forEach(function(c, i) {
      var date = c.created_at ? new Date(c.created_at).toLocaleString('en-IN', {day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'}) : '-';
      var dur = c.duration_seconds ? Math.floor(c.duration_seconds/60) + 'm ' + (c.duration_seconds%60) + 's' : '-';
      var reason = esc(c.ended_reason || '-');
      var src = c.source || 'voice';
      var srcBadge = '<span class="source-badge source-' + src + '">' + src.toUpperCase() + '</span>';
      var hasRecording = !!c.recording_url;
      var hasTranscript = !!c.transcript;
      var recCell = hasRecording
        ? '<a href="' + esc(c.recording_url) + '" target="_blank" style="color:#2563eb;font-size:13px;">Open Audio</a>'
        : '<span class="no-recording">No recording</span>';
      var expandBtn = (hasTranscript || hasRecording)
        ? '<button class="btn-expand" data-idx="' + i + '">View</button>'
        : '';
      html += '<tr id="call-row-' + i + '">' +
        '<td>' + date + '</td>' +
        '<td>' + srcBadge + '</td>' +
        '<td><span class="duration-badge">' + dur + '</span></td>' +
        '<td>' + reason + '</td>' +
        '<td>' + recCell + '</td>' +
        '<td>' + expandBtn + '</td>' +
        '</tr>';
    });
    html += '</tbody></table></div>';
    el.innerHTML = html;

    el.querySelectorAll('.btn-expand').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var idx = parseInt(this.dataset.idx);
        var c = conversations[idx];
        var existingDetail = document.getElementById('call-detail-' + idx);
        if (existingDetail) {
          existingDetail.remove();
          this.textContent = 'View';
          document.getElementById('call-row-' + idx).classList.remove('expanded');
          return;
        }
        this.textContent = 'Hide';
        document.getElementById('call-row-' + idx).classList.add('expanded');
        var detailRow = document.createElement('tr');
        detailRow.id = 'call-detail-' + idx;
        detailRow.className = 'transcript-row';
        var inner = '<td colspan="6">';
        if (c.recording_url) {
          inner += '<div class="audio-player"><audio controls preload="none"><source src="' + esc(c.recording_url) + '">Your browser does not support audio.</audio></div>';
        }
        if (c.transcript) {
          inner += '<div class="transcript-box" style="margin-top:' + (c.recording_url ? '12' : '0') + 'px">' + esc(c.transcript) + '</div>';
        }
        inner += '</td>';
        detailRow.innerHTML = inner;
        var callRow = document.getElementById('call-row-' + idx);
        callRow.parentNode.insertBefore(detailRow, callRow.nextSibling);
      });
    });
  }

  function renderEmbed(el) {
    fetch('/dashboard/api/embed-code')
      .then(function(r) { return r.json(); })
      .then(function(data) {
        el.innerHTML =
          '<div class="embed-box">' +
            '<h3>Chat Widget Embed Code</h3>' +
            '<p style="color:#64748b;font-size:14px;margin-bottom:16px;">Copy this code and paste it before the &lt;/body&gt; tag on your website:</p>' +
            '<pre id="embed-code">' + esc(data.embed_code) + '</pre>' +
            '<button class="btn-copy" id="copy-btn">Copy Code</button>' +
          '</div>';
        document.getElementById('copy-btn').addEventListener('click', function() {
          navigator.clipboard.writeText(data.embed_code).then(function() {
            document.getElementById('copy-btn').textContent = 'Copied!';
            setTimeout(function() { document.getElementById('copy-btn').textContent = 'Copy Code'; }, 2000);
          });
        });
      });
  }

  function statusSelect(lead) {
    var opts = ['new', 'contacted', 'qualified', 'converted', 'lost'];
    var html = '<select class="status-select" data-id="' + lead.id + '">';
    opts.forEach(function(o) {
      html += '<option value="' + o + '"' + (lead.status === o ? ' selected' : '') + '>' +
        o.charAt(0).toUpperCase() + o.slice(1) + '</option>';
    });
    return html + '</select>';
  }

  function statCard(label, value, color) {
    return '<div class="stat-card"><div class="label">' + label + '</div><div class="value ' + color + '">' + (value || 0) + '</div></div>';
  }

  function tabBtn(key, label) {
    return '<button class="tab' + (activeTab === key ? ' active' : '') + '" data-tab="' + key + '">' + label + '</button>';
  }

  function switchTab(tab) {
    activeTab = tab;
    document.querySelectorAll('.tab').forEach(function(x) { x.classList.remove('active'); });
    var t = document.querySelector('.tab[data-tab="' + tab + '"]');
    if (t) t.classList.add('active');
    renderTabContent();
  }

  function renderBilling(el) {
    fetch('/api/billing/status')
      .then(function(r) { return r.ok ? r.json() : Promise.reject(); })
      .then(function(data) {
        var status = data.subscription_status || 'trial';
        var badgeClass = 'badge-' + status;
        var badgeLabel = status.charAt(0).toUpperCase() + status.slice(1);
        var trialInfo = '';
        if (status === 'trial' && data.trial_ends_at) {
          var daysLeft = Math.ceil((new Date(data.trial_ends_at) - new Date()) / 86400000);
          trialInfo = '<p class="trial-info">Trial ' + (daysLeft > 0 ? 'expires in ' + daysLeft + ' day' + (daysLeft === 1 ? '' : 's') : 'has expired') + '.</p>';
        }
        var actionBtn = '';
        if (status === 'active') {
          actionBtn = '<button class="btn-cancel-sub" id="cancel-sub-btn">Cancel Subscription</button>';
        } else {
          actionBtn = '<button class="btn-subscribe" id="subscribe-btn">Subscribe Now &mdash; Rs 5,000 / month</button>' + trialInfo;
        }
        el.innerHTML =
          '<div class="billing-box">' +
            '<h3>Billing &amp; Subscription</h3>' +
            '<p class="sub-label">Manage your PropBot subscription</p>' +
            '<span class="billing-status-badge ' + badgeClass + '">' + badgeLabel + '</span>' +
            '<div class="billing-amount">Rs ' + fmt(data.monthly_fee_inr || 5000) + '</div>' +
            '<div class="billing-period">per month &middot; billed monthly via Razorpay</div>' +
            actionBtn +
          '</div>';

        var subBtn = document.getElementById('subscribe-btn');
        if (subBtn) {
          subBtn.addEventListener('click', function() {
            this.disabled = true;
            this.textContent = 'Creating subscription...';
            fetch('/api/billing/subscribe', {method: 'POST'})
              .then(function(r) { return r.ok ? r.json() : Promise.reject(); })
              .then(function(d) { window.location.href = d.checkout_url; })
              .catch(function() { alert('Failed to create subscription. Please try again.'); subBtn.disabled = false; subBtn.textContent = 'Subscribe Now — Rs 5,000 / month'; });
          });
        }

        var cancelBtn = document.getElementById('cancel-sub-btn');
        if (cancelBtn) {
          cancelBtn.addEventListener('click', function() {
            if (!confirm('Are you sure you want to cancel your subscription? Your AI receptionist will stop working.')) return;
            this.disabled = true;
            fetch('/api/billing/cancel', {method: 'POST'})
              .then(function(r) { return r.ok ? r.json() : Promise.reject(); })
              .then(function() { renderBilling(el); })
              .catch(function() { alert('Failed to cancel. Please try again.'); cancelBtn.disabled = false; });
          });
        }
      })
      .catch(function() {
        el.innerHTML = '<div class="empty-state"><h3>Could not load billing info</h3><p>Please refresh the page.</p></div>';
      });
  }

  function renderCalendar(el) {
    fetch('/dashboard/api/calendar/status')
      .then(function(r) { return r.ok ? r.json() : {connected: false}; })
      .then(function(data) {
        var connectedHtml = data.connected
          ? '<div class="calendar-connected">' +
              '<span style="font-size:24px;">&#10003;</span>' +
              '<span>Google Calendar connected</span>' +
              '<button class="btn-disconnect-cal" style="margin-left:auto;" onclick="disconnectCalendar()">Disconnect</button>' +
            '</div>'
          : '<button class="btn-connect-cal" onclick="location.href=\'/dashboard/google/connect\'">' +
              '<span style="font-size:18px;">&#128197;</span> Connect Google Calendar' +
            '</button>' +
              '<p style="color:#64748b;font-size:13px;margin-top:12px;">Required for the AI to book property viewings during calls</p>';

        el.innerHTML =
          '<div class="calendar-box">' +
            '<h3>Google Calendar</h3>' +
            '<p class="sub-label">Allow your AI receptionist to book property viewings automatically</p>' +
            connectedHtml +
            '<div style="margin-top:24px;">' +
              '<p style="font-size:13px;font-weight:600;color:#475569;margin-bottom:12px;">How it works</p>' +
              '<div class="calendar-benefit"><span>&#128222;</span><span>Caller asks to visit a property on Saturday 4pm</span></div>' +
              '<div class="calendar-benefit"><span>&#129302;</span><span>AI checks your calendar for availability</span></div>' +
              '<div class="calendar-benefit"><span>&#128197;</span><span>AI books the viewing and confirms with the caller</span></div>' +
              '<div class="calendar-benefit"><span>&#128276;</span><span>You get a calendar event with caller details</span></div>' +
            '</div>' +
          '</div>';
      });
  }

  function disconnectCalendar() {
    if (!confirm('Disconnect Google Calendar? The AI will no longer be able to book viewings.')) return;
    fetch('/dashboard/google/disconnect', {method: 'POST'})
      .then(function() { switchTab('calendar'); })
      .catch(function() { alert('Failed to disconnect. Please try again.'); });
  }

  function esc(s) { if (!s) return ''; var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
  function fmt(n) { return Number(n).toLocaleString('en-IN'); }
})();
</script>
</body>
</html>
"""
