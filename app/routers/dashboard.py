"""
Client Dashboard — magic-link login + full SPA.

Routes:
  GET  /dashboard           → SPA shell (login or dashboard)
  GET  /dashboard/login     → send magic-link email
  GET  /dashboard/auth      → verify token, set cookie
  GET  /dashboard/logout    → clear cookie
  GET  /dashboard/api/me           → profile
  PATCH/dashboard/api/me           → update profile / assistant settings
  GET  /dashboard/api/leads        → leads list + stats
  PATCH/dashboard/api/leads/{id}   → update lead status
  GET  /dashboard/api/calls        → call history (conversations)
  GET  /dashboard/api/callbacks    → callback requests
  PATCH/dashboard/api/callbacks/{id} → update callback status
  GET  /dashboard/api/stats        → summary stats
  GET  /dashboard/api/usage        → usage & cost this month
  GET  /dashboard/api/embed-code   → widget embed snippet
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


def _ga_snippet() -> str:
    """Return GA4 script tags if GA_MEASUREMENT_ID is configured, else empty string."""
    gid = settings.GA_MEASUREMENT_ID
    if not gid:
        return ""
    return (
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={gid}"></script>\n'
        f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}"
        f"gtag('js',new Date());gtag('config','{gid}');</script>\n"
    )

router = APIRouter()
logger = logging.getLogger(__name__)

MAGIC_LINK_TTL = 15 * 60  # 15 minutes


# ─── Auth helpers ────────────────────────────────────────────────

def _make_token(email: str, ts: int) -> str:
    secret = (settings.WEBHOOK_SECRET or "propbot-default-secret").encode()
    return hmac.new(secret, f"{email}:{ts}".encode(), hashlib.sha256).hexdigest()


def _make_session_token(client_id: str) -> str:
    secret = (settings.WEBHOOK_SECRET or "propbot-default-secret").encode()
    ts = int(time.time())
    sig = hmac.new(secret, f"{client_id}:{ts}".encode(), hashlib.sha256).hexdigest()[:32]
    return f"{client_id}:{ts}:{sig}"


def _verify_session(token: str) -> str | None:
    try:
        client_id, ts_str, sig = token.split(":")
        ts = int(ts_str)
        if time.time() - ts > 7 * 24 * 3600:
            return None
        secret = (settings.WEBHOOK_SECRET or "propbot-default-secret").encode()
        expected = hmac.new(secret, f"{client_id}:{ts}".encode(), hashlib.sha256).hexdigest()[:32]
        if hmac.compare_digest(sig, expected):
            return client_id
    except (ValueError, AttributeError):
        pass
    return None


def _get_client_id(request: Request) -> str:
    token = request.cookies.get("propbot_session")
    if not token:
        raise HTTPException(status_code=401, detail="Not logged in")
    client_id = _verify_session(token)
    if not client_id:
        raise HTTPException(status_code=401, detail="Session expired")
    return client_id


# ─── Magic-link login ─────────────────────────────────────────────

@router.get("/login")
async def request_magic_link(email: str = Query(...)):
    db = get_supabase()
    result = db.table("clients").select("id, agent_email, business_name").eq("agent_email", email.lower()).limit(1).execute()
    if not result.data:
        return {"message": "If that email is registered, a login link has been sent."}

    client = result.data[0]
    ts = int(time.time())
    token = _make_token(email.lower(), ts)
    login_url = f"{settings.BASE_URL}/dashboard/auth?email={email.lower()}&ts={ts}&token={token}"

    if settings.SMTP_EMAIL:
        import asyncio
        from app.services.alert_service import _send_email
        try:
            await asyncio.to_thread(
                _send_email,
                to=email,
                subject=f"PropBot Login — {client['business_name']}",
                body=f"""
<div style="font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;
            max-width:520px;margin:0 auto;">
  <div style="background:linear-gradient(135deg,#FF5722,#FF7043);padding:28px 32px;border-radius:12px 12px 0 0;">
    <h2 style="color:#fff;margin:0;font-size:22px;">PropBot Dashboard Login</h2>
  </div>
  <div style="background:#fff;padding:28px 32px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 12px 12px;">
    <p style="color:#475569;margin:0 0 20px;">Click the button below to log in to <strong>{client['business_name']}</strong> dashboard:</p>
    <a href="{login_url}"
       style="display:inline-block;padding:13px 36px;background:#FF5722;color:#fff;
              text-decoration:none;border-radius:8px;font-weight:700;font-size:15px;">
      Log in to Dashboard
    </a>
    <p style="color:#94a3b8;font-size:13px;margin-top:20px;">
      This link expires in 15 minutes. If you didn't request this, ignore this email.
    </p>
  </div>
</div>""",
            )
        except Exception as e:
            logger.error(f"Magic link email failed: {e}")

    return {"message": "If that email is registered, a login link has been sent."}


@router.get("/auth")
async def verify_magic_link(email: str, ts: int, token: str):
    if time.time() - ts > MAGIC_LINK_TTL:
        return HTMLResponse("<h2 style='font-family:sans-serif;padding:40px'>Link expired. Please request a new login link from the dashboard.</h2>", status_code=401)
    expected = _make_token(email.lower(), ts)
    if not hmac.compare_digest(token, expected):
        return HTMLResponse("<h2 style='font-family:sans-serif;padding:40px'>Invalid link.</h2>", status_code=401)

    db = get_supabase()
    result = db.table("clients").select("id").eq("agent_email", email.lower()).limit(1).execute()
    if not result.data:
        return HTMLResponse("<h2 style='font-family:sans-serif;padding:40px'>Account not found.</h2>", status_code=404)

    client_id = result.data[0]["id"]
    session_token = _make_session_token(client_id)
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie("propbot_session", session_token, max_age=7 * 24 * 3600, httponly=True, samesite="lax")
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.delete_cookie("propbot_session")
    return response


# ─── Dashboard API ────────────────────────────────────────────────

@router.get("/api/me")
async def get_profile(client_id: str = Depends(_get_client_id)):
    db = get_supabase()
    result = db.table("clients").select(
        "id, business_name, agent_name, agent_email, agent_phone, city, specialty, "
        "assistant_persona_name, voice_gender, voice_id, subscription_status, plan_type, "
        "trial_ends_at, exotel_number, setup_status, bolna_agent_id, created_at, first_message, "
        "knowledge_base, language_style"
    ).eq("id", client_id).single().execute()
    return result.data


@router.patch("/api/me")
async def update_profile(request: Request, client_id: str = Depends(_get_client_id)):
    body = await request.json()
    allowed = {
        "business_name", "agent_name", "agent_phone", "city", "specialty",
        "assistant_persona_name", "voice_gender", "voice_id", "first_message",
        "knowledge_base", "plan_type", "language_style",
    }
    update_data = {k: v for k, v in body.items() if k in allowed and v is not None}
    if not update_data:
        raise HTTPException(400, "Nothing to update")
    db = get_supabase()
    result = db.table("clients").update(update_data).eq("id", client_id).execute()
    if not result.data:
        raise HTTPException(404, "Client not found")
    return result.data[0]


@router.post("/api/assistant/sync")
async def sync_assistant(client_id: str = Depends(_get_client_id)):
    """Push updated assistant settings (name, greeting, language style) to Bolna."""
    from app.services.onboarding_service import update_voice_agent
    try:
        await update_voice_agent(client_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Bolna sync failed for %s: %s", client_id, e)
        # Don't fail the request — DB save already succeeded
    return {"ok": True}


@router.get("/api/leads")
async def get_leads(
    client_id: str = Depends(_get_client_id),
    limit: int = Query(default=100, le=200),
    status: str | None = Query(default=None),
):
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
async def update_lead(lead_id: str, request: Request, client_id: str = Depends(_get_client_id)):
    body = await request.json()
    allowed = {"status", "notes"}
    update_data = {k: v for k, v in body.items() if k in allowed}
    if not update_data:
        raise HTTPException(400, "Nothing to update")
    db = get_supabase()
    result = db.table("leads").update(update_data).eq("id", lead_id).eq("client_id", client_id).execute()
    if not result.data:
        raise HTTPException(404, "Lead not found")
    return result.data[0]


@router.get("/api/calls")
async def get_calls(
    client_id: str = Depends(_get_client_id),
    limit: int = Query(default=50, le=100),
):
    db = get_supabase()
    result = (
        db.table("conversations")
        .select("id, call_id, source, transcript, duration_seconds, ended_reason, recording_url, created_at")
        .eq("client_id", client_id)
        .eq("source", "voice")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return {"calls": result.data, "count": len(result.data)}


@router.get("/api/callbacks")
async def get_callbacks(
    client_id: str = Depends(_get_client_id),
    limit: int = Query(default=50, le=100),
):
    db = get_supabase()
    result = (
        db.table("callback_requests")
        .select("*")
        .eq("client_id", client_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return {"callbacks": result.data, "count": len(result.data)}


@router.patch("/api/callbacks/{cb_id}")
async def update_callback(cb_id: str, request: Request, client_id: str = Depends(_get_client_id)):
    body = await request.json()
    allowed = {"status"}
    update_data = {k: v for k, v in body.items() if k in allowed}
    if not update_data:
        raise HTTPException(400, "Nothing to update")
    db = get_supabase()
    result = (
        db.table("callback_requests")
        .update(update_data)
        .eq("id", cb_id)
        .eq("client_id", client_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Callback not found")
    return result.data[0]


@router.get("/api/stats")
async def get_stats(client_id: str = Depends(_get_client_id)):
    db = get_supabase()
    leads = db.table("leads").select("status, source, created_at").eq("client_id", client_id).execute()
    all_leads = leads.data or []
    now = datetime.now(timezone.utc)
    this_month = [l for l in all_leads if l.get("created_at", "")[:7] == now.strftime("%Y-%m")]
    status_counts = {}
    for l in all_leads:
        s = l.get("status", "new")
        status_counts[s] = status_counts.get(s, 0) + 1
    source_counts = {}
    for l in all_leads:
        s = l.get("source", "voice")
        source_counts[s] = source_counts.get(s, 0) + 1
    return {
        "total_leads": len(all_leads),
        "this_month": len(this_month),
        "by_status": status_counts,
        "by_source": source_counts,
        "new": status_counts.get("new", 0),
        "contacted": status_counts.get("contacted", 0),
        "qualified": status_counts.get("qualified", 0),
        "converted": status_counts.get("converted", 0),
    }


@router.get("/api/usage")
async def get_usage(client_id: str = Depends(_get_client_id)):
    """Return call minutes used this month and estimated cost."""
    db = get_supabase()
    now = datetime.now(timezone.utc)
    month_prefix = now.strftime("%Y-%m")

    calls = (
        db.table("conversations")
        .select("duration_seconds, created_at")
        .eq("client_id", client_id)
        .eq("source", "voice")
        .execute()
    )
    all_calls = calls.data or []
    month_calls = [c for c in all_calls if c.get("created_at", "")[:7] == month_prefix]

    total_seconds_month = sum(c.get("duration_seconds") or 0 for c in month_calls)
    total_seconds_all = sum(c.get("duration_seconds") or 0 for c in all_calls)

    # ₹0.06/min Bolna + Vobiz ≈ ₹5 per minute total (including platform)
    COST_PER_MIN_INR = 5
    minutes_month = round(total_seconds_month / 60, 1)
    estimated_cost_inr = round(minutes_month * COST_PER_MIN_INR)

    # Lead/callback breakdown for the month
    leads_month = (
        db.table("leads")
        .select("source, created_at")
        .eq("client_id", client_id)
        .execute()
    )
    leads_this_month = [l for l in (leads_month.data or []) if l.get("created_at", "")[:7] == month_prefix]
    voice_leads = sum(1 for l in leads_this_month if l.get("source") == "voice")
    chat_leads = sum(1 for l in leads_this_month if l.get("source") in ("chat", "callback"))

    return {
        "month": now.strftime("%B %Y"),
        "calls_this_month": len(month_calls),
        "total_calls": len(all_calls),
        "minutes_this_month": minutes_month,
        "total_minutes": round(total_seconds_all / 60, 1),
        "estimated_cost_inr": estimated_cost_inr,
        "subscription_fee_inr": 2499 if (db.table("clients").select("plan_type").eq("id", client_id).single().execute().data or {}).get("plan_type") == "starter" else 4999,
        "voice_leads_month": voice_leads,
        "chat_leads_month": chat_leads,
    }


@router.get("/api/embed-code")
async def get_embed_code(client_id: str = Depends(_get_client_id)):
    db = get_supabase()
    result = db.table("clients").select("id, assistant_persona_name, plan_type").eq("id", client_id).single().execute()
    client = result.data
    if (client.get("plan_type") or "pro") == "starter":
        return {
            "embed_code": "<!-- Chat widget is available on the Pro plan. Upgrade at your Billing tab. -->"
        }
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


# ─── Calendar OAuth ─────────────────────────────────────────────

@router.get("/api/calendar/status")
async def calendar_status(client_id: str = Depends(_get_client_id)):
    """Returns whether Google Calendar is connected."""
    from app.services.calendar_service import is_calendar_connected
    connected = await is_calendar_connected(client_id)
    return {"connected": connected}


@router.get("/google/connect")
async def connect_google_calendar(client_id: str = Depends(_get_client_id)):
    """Redirect to Google OAuth consent screen."""
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
async def disconnect_google_calendar(client_id: str = Depends(_get_client_id)):
    """Remove Google Calendar connection."""
    from app.services.calendar_service import disconnect_calendar
    await disconnect_calendar(client_id)
    return {"status": "disconnected"}


# ─── Dashboard SPA ────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    token = request.cookies.get("propbot_session")
    logged_in = bool(token and _verify_session(token))
    html = DASHBOARD_HTML.replace("__LOGGED_IN__", "true" if logged_in else "false")
    html = html.replace("<!-- __GA__ -->", _ga_snippet())
    return HTMLResponse(html)


# ─── Dashboard HTML/JS (full SPA) ────────────────────────────────

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PropBot Dashboard</title>
<!-- __GA__ -->
<script src="https://checkout.razorpay.com/v1/checkout.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');body{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:#F3F4F6;color:#111827;-webkit-font-smoothing:antialiased;}
a{color:inherit;text-decoration:none;}

/* ── Shell ── */
.shell{display:flex;min-height:100vh;}
.sidebar{width:220px;background:#111827;display:flex;flex-direction:column;flex-shrink:0;}
.sidebar-logo{padding:24px 20px;font-size:20px;font-weight:800;color:#fff;border-bottom:1px solid rgba(255,255,255,0.07);letter-spacing:-0.5px;}
.sidebar-logo span{color:#FF5722;}
.sidebar-nav{flex:1;padding:12px 0;}
.nav-item{display:flex;align-items:center;gap:10px;padding:11px 20px;font-size:14px;font-weight:500;color:#9CA3AF;cursor:pointer;border-left:3px solid transparent;transition:all .15s;}
.nav-item:hover{color:#F9FAFB;background:rgba(255,255,255,0.05);}
.nav-item.active{color:#fff;background:rgba(255,87,34,0.18);border-left-color:#FF5722;}
.nav-item .icon{font-size:16px;width:20px;text-align:center;}
.sidebar-footer{padding:16px 20px;border-top:1px solid rgba(255,255,255,0.07);}
.sidebar-user{font-size:12px;color:#6B7280;margin-bottom:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.btn-logout-side{width:100%;padding:8px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.09);border-radius:6px;color:#9CA3AF;font-size:13px;cursor:pointer;transition:all .15s;}
.btn-logout-side:hover{background:rgba(255,255,255,0.1);color:#F9FAFB;}

.main{flex:1;display:flex;flex-direction:column;min-width:0;}
.topbar{background:#fff;border-bottom:1px solid #e2e8f0;padding:0 28px;height:60px;display:flex;align-items:center;justify-content:space-between;}
.topbar-title{font-size:18px;font-weight:700;color:#1e293b;}
.topbar-sub{font-size:13px;color:#64748b;margin-top:2px;}
.topbar-right{display:flex;align-items:center;gap:12px;}
.trial-badge{padding:4px 12px;background:#fef3c7;border:1px solid #fcd34d;border-radius:20px;font-size:12px;font-weight:600;color:#92400e;}
.active-badge{padding:4px 12px;background:#d1fae5;border:1px solid #6ee7b7;border-radius:20px;font-size:12px;font-weight:600;color:#065f46;}
.content{flex:1;padding:28px;overflow-y:auto;}

/* ── Login ── */
.login-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#f0f6ff,#e0ecff);}
.login-card{width:400px;background:#fff;border-radius:20px;box-shadow:0 8px 40px rgba(0,0,0,0.1);overflow:hidden;}
.login-card-top{background:linear-gradient(135deg,#FF5722,#FF7043);padding:32px;text-align:center;}
.login-card-top h1{color:#fff;font-size:26px;font-weight:800;}
.login-card-top p{color:#bfdbfe;font-size:14px;margin-top:6px;}
.login-card-body{padding:32px;}
.login-card-body input{width:100%;padding:12px 14px;border:1.5px solid #d1d5db;border-radius:8px;font-size:15px;margin-bottom:12px;}
.login-card-body input:focus{outline:none;border-color:#FF5722;box-shadow:0 0 0 3px rgba(255,87,34,.1);}
.btn-primary{width:100%;padding:13px;background:#FF5722;color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;transition:background .15s;}
.btn-primary:hover{background:#E64A19;}
.btn-primary:disabled{opacity:.6;cursor:not-allowed;}
.login-msg{margin-top:12px;font-size:13px;color:#059669;text-align:center;}
.login-signup{text-align:center;margin-top:16px;font-size:14px;color:#64748b;}
.login-signup a{color:#FF5722;font-weight:500;}

/* ── Stats grid ── */
.stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px;}
.stat-card{background:#fff;padding:20px;border-radius:14px;box-shadow:0 1px 4px rgba(0,0,0,.06);border:1px solid #e2e8f0;}
.stat-card .label{font-size:12px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;}
.stat-card .value{font-size:30px;font-weight:800;color:#1e293b;}
.stat-card .sub{font-size:12px;color:#94a3b8;margin-top:4px;}
.stat-card.blue .value{color:#FF5722;}
.stat-card.green .value{color:#059669;}
.stat-card.orange .value{color:#d97706;}
.stat-card.purple .value{color:#7c3aed;}

/* ── Section card ── */
.section-card{background:#fff;border-radius:14px;box-shadow:0 1px 4px rgba(0,0,0,.06);border:1px solid #e2e8f0;overflow:hidden;}
.section-header{padding:16px 20px;border-bottom:1px solid #f1f5f9;display:flex;align-items:center;justify-content:space-between;}
.section-header h3{font-size:15px;font-weight:700;}
.section-header .count{font-size:13px;color:#64748b;}

/* ── Table ── */
.tbl{width:100%;border-collapse:collapse;}
.tbl th{text-align:left;padding:11px 16px;font-size:11px;font-weight:700;color:#64748b;background:#f8fafc;text-transform:uppercase;letter-spacing:.5px;}
.tbl td{padding:12px 16px;font-size:14px;border-top:1px solid #f1f5f9;vertical-align:top;}
.tbl tr:hover td{background:#f8fafc;}
.tbl .phone{color:#FF5722;}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;}
.badge-new{background:rgba(255,87,34,0.1);color:#E64A19;}
.badge-contacted{background:#fef3c7;color:#92400e;}
.badge-qualified{background:#d1fae5;color:#065f46;}
.badge-converted{background:#059669;color:#fff;}
.badge-lost{background:#fee2e2;color:#991b1b;}
.badge-pending{background:#fef3c7;color:#92400e;}
.badge-called{background:#d1fae5;color:#065f46;}
.badge-no_answer{background:#f1f5f9;color:#64748b;}
.badge-voice{background:#ede9fe;color:#6d28d9;}
.badge-chat{background:rgba(255,87,34,0.1);color:#E64A19;}
.badge-callback{background:#fce7f3;color:#9d174d;}
.status-sel{padding:4px 8px;border:1px solid #d1d5db;border-radius:6px;font-size:12px;cursor:pointer;background:#fff;}

/* ── Calls ── */
.call-row{border-top:1px solid #f1f5f9;}
.call-row td{padding:14px 16px;vertical-align:top;}
.call-meta{display:flex;align-items:center;gap:8px;margin-bottom:4px;}
.call-date{font-size:13px;color:#64748b;}
.call-dur{font-size:13px;font-weight:600;color:#1e293b;}
.transcript{font-size:13px;color:#475569;line-height:1.5;margin-top:6px;max-height:80px;overflow:hidden;white-space:pre-wrap;}
.transcript.expanded{max-height:none;}
.expand-btn{font-size:12px;color:#FF5722;cursor:pointer;margin-top:4px;display:inline-block;}
.recording-link{font-size:12px;color:#7c3aed;margin-left:12px;}

/* ── Callbacks ── */
.cb-name{font-weight:600;}
.cb-time{font-size:12px;color:#64748b;margin-top:2px;}
.cb-ctx{font-size:13px;color:#475569;margin-top:4px;}

/* ── Usage ── */
.usage-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:24px;}
.usage-card{background:#fff;padding:24px;border-radius:14px;box-shadow:0 1px 4px rgba(0,0,0,.06);border:1px solid #e2e8f0;}
.usage-card .u-label{font-size:12px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;}
.usage-card .u-value{font-size:34px;font-weight:800;color:#1e293b;}
.usage-card .u-sub{font-size:13px;color:#94a3b8;margin-top:4px;}
.cost-note{font-size:13px;color:#64748b;margin-top:8px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px 16px;}

/* ── Assistant Settings ── */
.settings-form{padding:24px;}
.s-field{margin-bottom:20px;}
.s-field label{display:block;font-size:13px;font-weight:600;color:#374151;margin-bottom:6px;}
.s-field input,.s-field select,.s-field textarea{
  width:100%;padding:10px 14px;border:1.5px solid #d1d5db;border-radius:8px;
  font-size:15px;color:#1e293b;background:#fff;
  transition:border-color .15s;}
.s-field input:focus,.s-field select:focus,.s-field textarea:focus{
  outline:none;border-color:#FF5722;box-shadow:0 0 0 3px rgba(255,87,34,.1);}
.s-field textarea{min-height:80px;resize:vertical;font-family:inherit;}
.s-field .hint{font-size:12px;color:#94a3b8;margin-top:4px;}
.s-row{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
.persona-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:4px;}
.persona-opt{padding:14px;border:2px solid #e2e8f0;border-radius:10px;cursor:pointer;text-align:center;transition:all .15s;}
.persona-opt:hover{border-color:rgba(255,87,34,0.35);background:#f0f9ff;}
.persona-opt.selected{border-color:#FF5722;background:rgba(255,87,34,0.06);}
.persona-opt .p-avatar{font-size:28px;margin-bottom:6px;}
.persona-opt .p-name{font-size:14px;font-weight:600;color:#1e293b;}
.persona-opt .p-lang{font-size:12px;color:#64748b;}
.gender-opts{display:flex;gap:10px;margin-top:4px;}
.gender-btn{flex:1;padding:10px;border:2px solid #e2e8f0;border-radius:8px;cursor:pointer;text-align:center;font-size:14px;font-weight:500;color:#475569;transition:all .15s;}
.gender-btn:hover{border-color:rgba(255,87,34,0.35);}
.gender-btn.selected{border-color:#FF5722;background:rgba(255,87,34,0.06);color:#E64A19;}
.btn-save{padding:12px 32px;background:#FF5722;color:#fff;border:none;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;transition:background .15s;}
.btn-save:hover{background:#E64A19;}
.btn-save:disabled{opacity:.6;cursor:not-allowed;}
.save-msg{display:inline-block;margin-left:12px;font-size:13px;color:#059669;opacity:0;transition:opacity .3s;}
.save-msg.show{opacity:1;}

/* ── Widget embed ── */
.embed-wrap{padding:24px;}
.embed-wrap h3{font-size:15px;font-weight:700;margin-bottom:8px;}
.embed-wrap p{font-size:14px;color:#475569;margin-bottom:16px;line-height:1.6;}
.embed-wrap pre{background:#1e293b;color:#e2e8f0;padding:18px;border-radius:10px;font-size:13px;overflow-x:auto;white-space:pre-wrap;line-height:1.6;}
.btn-copy{margin-top:12px;padding:9px 24px;background:#FF5722;color:#fff;border:none;border-radius:7px;cursor:pointer;font-size:13px;font-weight:600;}
.btn-copy:hover{background:#E64A19;}
.preview-note{margin-top:16px;font-size:13px;color:#64748b;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px 16px;}

/* ── Empty state ── */
.empty{text-align:center;padding:64px 20px;color:#94a3b8;}
.empty .e-icon{font-size:40px;margin-bottom:12px;}
.empty h3{font-size:16px;color:#64748b;margin-bottom:6px;}
.empty p{font-size:14px;}

/* ── Responsive ── */
@media(max-width:900px){
  .sidebar{display:none;}
  .stats-grid{grid-template-columns:repeat(2,1fr);}
  .usage-grid{grid-template-columns:1fr 1fr;}
  .persona-grid{grid-template-columns:repeat(2,1fr);}
  .s-row{grid-template-columns:1fr;}
}
@media(max-width:600px){
  .stats-grid{grid-template-columns:1fr 1fr;}
  .usage-grid{grid-template-columns:1fr;}
  .content{padding:16px;}
}

/* ── Phone Banner ── */
.phone-banner{display:flex;align-items:center;gap:10px;padding:14px 20px;border-radius:10px;margin-bottom:20px;font-size:14px;font-weight:500;}
.phone-banner.ready{background:#ecfdf5;border:1px solid #6ee7b7;color:#065f46;}
.phone-banner.provisioning{background:rgba(255,87,34,0.06);border:1px solid rgba(255,87,34,0.35);color:#E64A19;}
.phone-banner.failed{background:#fef2f2;border:1px solid #fca5a5;color:#991b1b;}
.phone-number{font-size:18px;font-weight:700;letter-spacing:0.5px;}

/* ── Trial Warning ── */
.trial-warning{background:#fffbeb;border:1px solid #fcd34d;color:#92400e;padding:12px 20px;border-radius:10px;margin-bottom:16px;font-size:14px;}
.trial-expired{background:#fef2f2;border:1px solid #fca5a5;color:#991b1b;padding:12px 20px;border-radius:10px;margin-bottom:16px;font-size:14px;}
.trial-warning a,.trial-expired a{font-weight:600;color:inherit;text-decoration:underline;cursor:pointer;}

/* ── Billing Tab ── */
.billing-box{background:#fff;padding:32px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);max-width:600px;}
.billing-box h3{font-size:18px;margin-bottom:6px;}
.billing-box .sub-label{color:#64748b;font-size:14px;margin-bottom:24px;}
.billing-status-badge{display:inline-block;padding:4px 14px;border-radius:20px;font-size:13px;font-weight:600;margin-bottom:20px;}
.badge-trial{background:rgba(255,87,34,0.1);color:#E64A19;}
.badge-active{background:#d1fae5;color:#065f46;}
.badge-paused{background:#fef3c7;color:#92400e;}
.badge-cancelled{background:#fee2e2;color:#991b1b;}
.billing-amount{font-size:32px;font-weight:700;color:#1e293b;margin-bottom:4px;}
.billing-period{color:#64748b;font-size:14px;margin-bottom:24px;}
.btn-subscribe{width:100%;padding:14px 28px;background:#FF5722;color:#fff;border:none;border-radius:10px;font-size:16px;font-weight:700;cursor:pointer;font-family:inherit;transition:all .2s;}
.btn-subscribe:hover{background:#E64A19;}
.btn-subscribe:disabled{opacity:.6;cursor:not-allowed;}
.plan-pick{border:2px solid #E5E7EB;border-radius:12px;padding:14px 16px;cursor:pointer;transition:all .15s;background:#FAFAF8;}
.plan-pick:hover{border-color:rgba(255,87,34,.4);background:#fff;}
.plan-pick-sel{border-color:#FF5722;background:rgba(255,87,34,.04);box-shadow:0 0 0 3px rgba(255,87,34,.1);}
.btn-cancel-sub{padding:10px 20px;background:#fff;color:#ef4444;border:1px solid #fca5a5;border-radius:8px;font-size:14px;cursor:pointer;margin-top:12px;}
.btn-cancel-sub:hover{background:#fef2f2;}
.trial-info{color:#64748b;font-size:13px;margin-top:16px;}

/* ── Calendar Tab ── */
.calendar-box{background:#fff;padding:32px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);max-width:600px;}
.calendar-box h3{font-size:18px;margin-bottom:6px;}
.calendar-box .sub-label{color:#64748b;font-size:14px;margin-bottom:24px;}
.calendar-connected{display:flex;align-items:center;gap:12px;padding:16px;background:#ecfdf5;border:1px solid #6ee7b7;border-radius:10px;margin-bottom:16px;}
.calendar-connected span{font-weight:600;color:#065f46;}
.btn-connect-cal{padding:12px 24px;background:#fff;color:#1e293b;border:1px solid #d1d5db;border-radius:8px;font-size:15px;font-weight:500;cursor:pointer;display:flex;align-items:center;gap:8px;}
.btn-connect-cal:hover{background:#f8fafc;border-color:#FF5722;color:#FF5722;}
.btn-disconnect-cal{padding:8px 16px;background:#fff;color:#64748b;border:1px solid #e2e8f0;border-radius:6px;font-size:13px;cursor:pointer;}
.btn-disconnect-cal:hover{background:#f8fafc;}
.calendar-benefit{display:flex;gap:10px;padding:12px 0;border-bottom:1px solid #f1f5f9;font-size:14px;color:#475569;}
.calendar-benefit:last-child{border-bottom:none;}
</style>
</head>
<body>
<div id="root"></div>
<script>
(function(){
'use strict';

var LOGGED_IN = __LOGGED_IN__;
var profile = null, stats = null, activeTab = 'leads';

if (!LOGGED_IN) { renderLogin(); return; }
boot();

/* ══════════════════════════════════════════════
   LOGIN
══════════════════════════════════════════════ */
function renderLogin(){
  document.getElementById('root').innerHTML =
    '<div class="login-wrap"><div class="login-card">' +
      '<div class="login-card-top"><h1>PropBot</h1><p>AI Receptionist for Real Estate</p></div>' +
      '<div class="login-card-body">' +
        '<p style="font-size:14px;color:#475569;margin-bottom:16px;">Enter your registered email to receive a one-click login link.</p>' +
        '<input type="email" id="lemail" placeholder="your@email.com" />' +
        '<button class="btn-primary" id="lbtn">Send Login Link</button>' +
        '<div class="login-msg" id="lmsg" style="display:none"></div>' +
        '<div class="login-signup">New here? <a href="/signup">Create a free account</a></div>' +
      '</div>' +
    '</div></div>';

  document.getElementById('lbtn').onclick = sendLink;
  document.getElementById('lemail').onkeydown = function(e){ if(e.key==='Enter') sendLink(); };

  function sendLink(){
    var email = document.getElementById('lemail').value.trim();
    if(!email) return;
    var btn = document.getElementById('lbtn');
    btn.disabled=true; btn.textContent='Sending…';
    fetch('/dashboard/login?email='+encodeURIComponent(email))
      .then(function(r){return r.json();})
      .then(function(){
        var m=document.getElementById('lmsg');
        m.style.display='block';
        m.textContent='Login link sent! Check your inbox (and spam folder).';
        btn.textContent='Link Sent ✓';
      })
      .catch(function(){ btn.disabled=false; btn.textContent='Send Login Link'; });
  }
}

/* ══════════════════════════════════════════════
   BOOT — load all data in parallel
══════════════════════════════════════════════ */
function boot(){
  Promise.all([
    api('/dashboard/api/me'),
    api('/dashboard/api/stats'),
  ]).then(function(r){
    profile = r[0]; stats = r[1];
    renderShell();
    switchTab(activeTab);
  }).catch(function(){
    LOGGED_IN=false; renderLogin();
  });
}

function api(url, opts){
  return fetch(url, opts).then(function(r){
    if(r.status===401){ LOGGED_IN=false; renderLogin(); return Promise.reject('session'); }
    if(!r.ok) return r.json().then(function(d){ return Promise.reject(d); });
    return r.json();
  });
}

/* ══════════════════════════════════════════════
   SHELL (sidebar + topbar)
══════════════════════════════════════════════ */
function renderShell(){
  var tabs = [
    {id:'leads',    icon:'🎯', label:'Leads'},
    {id:'calls',    icon:'📞', label:'Call History'},
    {id:'callbacks',icon:'🔔', label:'Callbacks'},
    {id:'usage',    icon:'📊', label:'Usage & Cost'},
    {id:'assistant',icon:'🤖', label:'AI Assistant'},
    {id:'listings', icon:'🏠', label:'My Listings'},
    {id:'widget',   icon:'💬', label:'Chat Widget'},
    {id:'billing',  icon:'💳', label:'Billing'},
    {id:'calendar', icon:'📅', label:'Calendar'},
  ];
  var navHtml = tabs.map(function(t){
    return '<div class="nav-item'+(activeTab===t.id?' active':'')+'" data-tab="'+t.id+'">' +
      '<span class="icon">'+t.icon+'</span>'+t.label+'</div>';
  }).join('');

  var statusBadge = profile.subscription_status === 'active'
    ? '<span class="active-badge">Active</span>'
    : '<span class="trial-badge">Trial</span>';

  document.getElementById('root').innerHTML =
    '<div class="shell">' +
      '<div class="sidebar">' +
        '<div class="sidebar-logo">Prop<span>Bot</span></div>' +
        '<nav class="sidebar-nav">'+navHtml+'</nav>' +
        '<div class="sidebar-footer">' +
          '<div class="sidebar-user">'+esc(profile.agent_email)+'</div>' +
          '<button class="btn-logout-side" id="logout-btn">Log out</button>' +
        '</div>' +
      '</div>' +
      '<div class="main">' +
        '<div class="topbar">' +
          '<div><div class="topbar-title">'+esc(profile.business_name)+'</div>' +
          '<div class="topbar-sub">'+esc(profile.agent_name)+'</div></div>' +
          '<div class="topbar-right">'+statusBadge+'</div>' +
        '</div>' +
        '<div class="content" id="content"></div>' +
      '</div>' +
    '</div>';

  document.querySelectorAll('.nav-item').forEach(function(el){
    el.addEventListener('click', function(){ switchTab(this.dataset.tab); });
  });
  document.getElementById('logout-btn').onclick = function(){
    location.href='/dashboard/logout';
  };
}

function switchTab(tab){
  activeTab = tab;
  document.querySelectorAll('.nav-item').forEach(function(el){
    el.classList.toggle('active', el.dataset.tab===tab);
  });
  var c = document.getElementById('content');
  c.innerHTML = '<div style="padding:40px;text-align:center;color:#94a3b8;">Loading…</div>';
  if(tab==='leads')     renderLeads();
  else if(tab==='calls')     renderCalls();
  else if(tab==='callbacks') renderCallbacks();
  else if(tab==='usage')     renderUsage();
  else if(tab==='assistant') renderAssistant();
  else if(tab==='listings')  renderListings();
  else if(tab==='widget')    renderWidget();
  else if(tab==='billing')   renderBilling();
  else if(tab==='calendar')  renderCalendar();
}

function phoneBanner(){
  if(!profile.setup_status) return '';
  if(profile.setup_status==='ready' && profile.exotel_number)
    return '<div class="phone-banner ready"><span>📞</span><div><div>Your AI Receptionist Number</div>' +
      '<div class="phone-number">'+esc(profile.exotel_number)+'</div></div>' +
      '<div style="margin-left:auto;font-size:13px;color:#059669;">Share this with your clients!</div></div>';
  if(profile.setup_status==='provisioning')
    return '<div class="phone-banner provisioning"><span>⏳</span>' +
      '<span>Setting up your phone number... Refresh in a moment.</span></div>';
  if(profile.setup_status==='failed')
    return '<div class="phone-banner failed"><span>⚠️</span>' +
      '<span>Phone number setup pending. Please contact support.</span></div>';
  return '';
}

function trialWarning(){
  if(profile.subscription_status!=='trial' || !profile.trial_ends_at) return '';
  var daysLeft = Math.ceil((new Date(profile.trial_ends_at)-new Date())/86400000);
  if(daysLeft<=0)
    return '<div class="trial-expired">⚠️ Your trial has expired. ' +
      '<a onclick="switchTab(\'billing\')">Subscribe now</a> to reactivate your AI receptionist.</div>';
  if(daysLeft<=3)
    return '<div class="trial-warning">⚠️ Your trial expires in '+daysLeft+' day'+(daysLeft===1?'':'s')+'. ' +
      '<a onclick="switchTab(\'billing\')">Subscribe now</a> to keep your AI receptionist active.</div>';
  return '';
}

/* ══════════════════════════════════════════════
   LEADS TAB
══════════════════════════════════════════════ */
function renderLeads(){
  api('/dashboard/api/leads').then(function(data){
    var c = document.getElementById('content');
    var leads = data.leads || [];

    // Phone banner + trial warning
    var statsHtml = phoneBanner() + trialWarning() +
      '<div class="stats-grid">' +
        statCard('Total Leads', stats.total_leads, 'blue') +
        statCard('This Month', stats.this_month, '') +
        statCard('New', stats.new, 'orange') +
        statCard('Converted', stats.converted, 'green') +
      '</div>';

    if(!leads.length){
      c.innerHTML = statsHtml + empty('🎯','No leads yet','Leads appear here the moment your AI assistant qualifies a caller.');
      return;
    }

    var rows = leads.map(function(l){
      var budget = '';
      if(l.budget_min && l.budget_max) budget = '₹'+fmt(l.budget_min)+' – ₹'+fmt(l.budget_max);
      else if(l.budget_min) budget = '₹'+fmt(l.budget_min)+'+';
      else if(l.budget_max) budget = 'Up to ₹'+fmt(l.budget_max);
      var lookingFor = [l.property_type,l.preferred_area].filter(Boolean).join(', ')||'—';
      var srcBadge = '<span class="badge badge-'+esc(l.source||'voice')+'">'+esc(l.source||'voice')+'</span>';
      return '<tr>' +
        '<td><strong>'+esc(l.caller_name||'—')+'</strong></td>' +
        '<td><span class="phone">'+esc(l.caller_phone||'—')+'</span></td>' +
        '<td>'+esc(lookingFor)+'</td>' +
        '<td>'+esc(budget)+'</td>' +
        '<td>'+srcBadge+'</td>' +
        '<td>'+statusSel(l,'leads')+'</td>' +
        '<td style="font-size:13px;color:#64748b;">'+fmtDate(l.created_at)+'</td>' +
        '</tr>';
    }).join('');

    c.innerHTML = statsHtml +
      '<div class="section-card">' +
        '<div class="section-header"><h3>All Leads</h3><span class="count">'+leads.length+' total</span></div>' +
        '<div style="overflow-x:auto"><table class="tbl">' +
          '<thead><tr><th>Name</th><th>Phone</th><th>Looking For</th><th>Budget</th><th>Source</th><th>Status</th><th>Date</th></tr></thead>' +
          '<tbody>'+rows+'</tbody>' +
        '</table></div>' +
      '</div>';

    // Status change listeners
    document.querySelectorAll('.status-sel[data-table="leads"]').forEach(function(sel){
      sel.addEventListener('change',function(){
        var id=this.dataset.id, val=this.value;
        api('/dashboard/api/leads/'+id, {method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:val})})
          .catch(function(){ alert('Failed to update status'); });
      });
    });
  });
}

/* ══════════════════════════════════════════════
   CALLS TAB
══════════════════════════════════════════════ */
function renderCalls(){
  api('/dashboard/api/calls').then(function(data){
    var c = document.getElementById('content');
    var calls = data.calls || [];
    if(!calls.length){
      c.innerHTML = empty('📞','No call history yet','Every call your AI assistant handles will appear here with a full transcript.');
      return;
    }
    var rows = calls.map(function(call, idx){
      var dur = call.duration_seconds ? Math.round(call.duration_seconds/60)+'m '+((call.duration_seconds%60))+'s' : '—';
      var trans = call.transcript ? esc(call.transcript).substring(0,300)+(call.transcript.length>300?'…':'') : '<em style="color:#94a3b8">No transcript</em>';
      var recLink = call.recording_url ? '<a class="recording-link" href="'+esc(call.recording_url)+'" target="_blank">▶ Recording</a>' : '';
      var endReason = call.ended_reason ? '<span class="badge" style="background:#f1f5f9;color:#64748b;margin-left:8px">'+esc(call.ended_reason)+'</span>' : '';
      return '<tr class="call-row">' +
        '<td style="width:140px">' +
          '<div class="call-date">'+fmtDate(call.created_at)+'</div>' +
          '<div class="call-dur">'+dur+'</div>' +
          endReason +
          recLink +
        '</td>' +
        '<td>' +
          '<div class="transcript" id="trans-'+idx+'">'+trans+'</div>' +
          (call.transcript && call.transcript.length>300 ?
            '<span class="expand-btn" data-idx="'+idx+'">Show more</span>' : '') +
        '</td>' +
        '</tr>';
    }).join('');

    c.innerHTML =
      '<div class="section-card">' +
        '<div class="section-header"><h3>Call History</h3><span class="count">'+calls.length+' calls</span></div>' +
        '<div style="overflow-x:auto"><table class="tbl">' +
          '<thead><tr><th style="width:140px">Call</th><th>Transcript</th></tr></thead>' +
          '<tbody>'+rows+'</tbody>' +
        '</table></div>' +
      '</div>';

    // Expand buttons
    document.querySelectorAll('.expand-btn').forEach(function(btn){
      btn.addEventListener('click', function(){
        var idx = this.dataset.idx;
        var el = document.getElementById('trans-'+idx);
        var call = calls[idx];
        if(el.classList.contains('expanded')){
          el.innerHTML = esc(call.transcript).substring(0,300)+'…';
          el.classList.remove('expanded');
          this.textContent='Show more';
        } else {
          el.innerHTML = esc(call.transcript);
          el.classList.add('expanded');
          this.textContent='Show less';
        }
      });
    });
  });
}

/* ══════════════════════════════════════════════
   CALLBACKS TAB
══════════════════════════════════════════════ */
function renderCallbacks(){
  api('/dashboard/api/callbacks').then(function(data){
    var c = document.getElementById('content');
    var cbs = data.callbacks || [];
    if(!cbs.length){
      c.innerHTML = empty('🔔','No callback requests','When website visitors request a callback through the chat widget, they appear here.');
      return;
    }
    var rows = cbs.map(function(cb){
      return '<tr>' +
        '<td><div class="cb-name">'+esc(cb.visitor_name||'Unknown')+'</div>' +
          '<div class="cb-time">Preferred: '+esc(cb.preferred_time||'Any time')+'</div>' +
          (cb.context?'<div class="cb-ctx">'+esc(cb.context)+'</div>':'')+
        '</td>' +
        '<td><span class="phone">'+esc(cb.visitor_phone||'—')+'</span></td>' +
        '<td>'+cbStatusSel(cb)+'</td>' +
        '<td style="font-size:13px;color:#64748b;">'+fmtDate(cb.created_at)+'</td>' +
        '</tr>';
    }).join('');

    c.innerHTML =
      '<div class="section-card">' +
        '<div class="section-header"><h3>Callback Requests</h3><span class="count">'+cbs.length+' total</span></div>' +
        '<div style="overflow-x:auto"><table class="tbl">' +
          '<thead><tr><th>Visitor</th><th>Phone</th><th>Status</th><th>Date</th></tr></thead>' +
          '<tbody>'+rows+'</tbody>' +
        '</table></div>' +
      '</div>';

    document.querySelectorAll('.cb-sel').forEach(function(sel){
      sel.addEventListener('change', function(){
        var id=this.dataset.id, val=this.value;
        api('/dashboard/api/callbacks/'+id, {method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:val})})
          .catch(function(){ alert('Failed to update status'); });
      });
    });
  });
}

/* ══════════════════════════════════════════════
   USAGE TAB
══════════════════════════════════════════════ */
function renderUsage(){
  api('/dashboard/api/usage').then(function(u){
    var c = document.getElementById('content');
    c.innerHTML =
      '<div class="usage-grid">' +
        usageCard('Calls This Month', u.calls_this_month, 'total calls', '') +
        usageCard('Minutes Used', u.minutes_this_month+'m', 'of talk time', '') +
        usageCard('Est. Usage Cost', '₹'+u.estimated_cost_inr, 'this month', '') +
      '</div>' +
      '<div class="stats-grid" style="margin-bottom:24px">' +
        statCard('Voice Leads', u.voice_leads_month, 'blue', 'this month') +
        statCard('Chat Leads', u.chat_leads_month, 'purple', 'this month') +
        statCard('Total Calls Ever', u.total_calls, '', '') +
        statCard('Total Minutes', u.total_minutes+'m', '', 'all time') +
      '</div>' +
      '<div class="cost-note">' +
        '<strong>About this estimate:</strong> Usage cost is estimated at ₹5/min (Bolna AI + Vobiz telephony). ' +
        'Your monthly subscription is ₹'+u.subscription_fee_inr+'. ' +
        'Actual billing is a flat monthly fee — you won\'t be charged per minute.' +
      '</div>';
  });
}

/* ══════════════════════════════════════════════
   ASSISTANT TAB
══════════════════════════════════════════════ */
function renderAssistant(){
  var c = document.getElementById('content');
  var assistantName = profile.assistant_persona_name || 'Priya';
  var langStyle = profile.language_style || 'hinglish';

  c.innerHTML =
    '<div class="section-card">' +
      '<div class="section-header"><h3>AI Assistant Settings</h3></div>' +
      '<div class="settings-form">' +
        '<div class="s-field">' +
          '<label>Assistant Name</label>' +
          '<input type="text" id="assistant-name" value="'+esc(assistantName)+'" placeholder="Priya" maxlength="30" />' +
          '<div class="hint">What should callers call your assistant? (e.g. Priya, Rekha, Anjali)</div>' +
        '</div>' +
        '<div class="s-field">' +
          '<label>Language Style</label>' +
          '<select id="lang-style">' +
            '<option value="hinglish"'+(langStyle==='hinglish'?' selected':'')+'>Hindi + English mix (recommended)</option>' +
            '<option value="english"'+(langStyle==='english'?' selected':'')+'>Mostly English</option>' +
            '<option value="casual_hinglish"'+(langStyle==='casual_hinglish'?' selected':'')+'>Casual Hinglish</option>' +
          '</select>' +
          '<div class="hint">Controls how your assistant speaks during calls.</div>' +
        '</div>' +
        '<div class="s-field">' +
          '<label>Opening Greeting</label>' +
          '<textarea id="first-msg" placeholder="What the assistant says when picking up a call">'+esc(profile.first_message||'')+'</textarea>' +
          '<div class="hint">Use {business_name} for your business name. Keep it under 2 sentences.</div>' +
        '</div>' +
        '<div>' +
          '<button class="btn-save" id="save-assistant-btn">Save Changes</button>' +
          '<span class="save-msg" id="save-msg">Assistant updated!</span>' +
        '</div>' +
      '</div>' +
    '</div>';

  document.getElementById('save-assistant-btn').addEventListener('click', function(){
    var btn = this;
    var name = document.getElementById('assistant-name').value.trim() || 'Priya';
    var lang = document.getElementById('lang-style').value;
    var firstMsg = document.getElementById('first-msg').value.trim();
    btn.disabled=true; btn.textContent='Saving…';
    api('/dashboard/api/me', {
      method:'PATCH',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({assistant_persona_name:name, language_style:lang, first_message:firstMsg})
    }).then(function(updated){
      profile = Object.assign(profile, updated);
      // Push updated first_message to Bolna agent
      return api('/dashboard/api/assistant/sync', {method:'POST'});
    }).then(function(){
      btn.disabled=false; btn.textContent='Save Changes';
      var msg=document.getElementById('save-msg');
      msg.classList.add('show');
      setTimeout(function(){ msg.classList.remove('show'); }, 2500);
    }).catch(function(){
      btn.disabled=false; btn.textContent='Save Changes';
      alert('Failed to save. Please try again.');
    });
  });
}

/* ══════════════════════════════════════════════
   LISTINGS TAB
══════════════════════════════════════════════ */
function renderListings(){
  var c = document.getElementById('content');
  c.innerHTML = '<div class="section-card"><p style="color:#6B7280;font-size:14px;">Loading listings...</p></div>';
  api('/dashboard/api/me').then(function(data){
    var kb = data.knowledge_base || '';
    c.innerHTML =
      '<div class="section-card">' +
        '<h2 style="font-size:18px;font-weight:700;margin-bottom:6px;">My Property Listings</h2>' +
        '<p style="font-size:14px;color:#6B7280;margin-bottom:20px;line-height:1.55;">Your AI assistant uses this to answer buyer questions. Update anytime — changes take effect instantly.</p>' +
        '<div style="background:rgba(255,87,34,0.05);border:1px solid rgba(255,87,34,0.2);border-radius:10px;padding:14px 16px;margin-bottom:16px;font-size:13px;color:#374151;line-height:1.6;">' +
          '<strong style="color:#FF5722;">Tip:</strong> Use <code style="background:rgba(255,87,34,0.1);color:#E64A19;padding:1px 5px;border-radius:4px;">##</code> for each property name, then add details on separate lines. The more detail, the better your AI answers.' +
        '</div>' +
        '<textarea id="kb-input" style="width:100%;min-height:360px;padding:14px;border:1.5px solid #E5E7EB;border-radius:10px;font-size:13px;font-family:monospace;line-height:1.65;resize:vertical;background:#FAFAF8;color:#111827;transition:all .15s;" ' +
          'onfocus="this.style.borderColor=\'#FF5722\';this.style.boxShadow=\'0 0 0 3px rgba(255,87,34,0.1)\'" ' +
          'onblur="this.style.borderColor=\'#E5E7EB\';this.style.boxShadow=\'none\'">' + esc(kb) + '</textarea>' +
        '<div style="display:flex;align-items:center;gap:12px;margin-top:16px;">' +
          '<button id="kb-save" style="padding:13px 32px;background:#FF5722;color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer;font-family:inherit;box-shadow:0 4px 14px rgba(255,87,34,0.3);transition:all .2s;">Save Listings</button>' +
          '<span id="kb-status" style="font-size:13px;color:#6B7280;"></span>' +
        '</div>' +
      '</div>';
    document.getElementById('kb-save').addEventListener('click', saveListings);
  });
}
function saveListings(){
  var btn = document.getElementById('kb-save');
  var status = document.getElementById('kb-status');
  var kb = document.getElementById('kb-input').value.trim();
  if(!kb){ status.textContent = 'Please add at least some property details.'; status.style.color='#EF4444'; return; }
  btn.disabled = true; btn.textContent = 'Saving...';
  status.textContent = ''; status.style.color='#6B7280';
  fetch('/dashboard/api/me', {
    method:'PATCH',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({knowledge_base: kb})
  }).then(function(r){ return r.json(); }).then(function(){
    btn.disabled = false; btn.textContent = 'Save Listings';
    status.textContent = '✓ Saved successfully'; status.style.color='#10B981';
    setTimeout(function(){ status.textContent=''; }, 3000);
  }).catch(function(){
    btn.disabled = false; btn.textContent = 'Save Listings';
    status.textContent = 'Save failed — please try again'; status.style.color='#EF4444';
  });
}

/* ══════════════════════════════════════════════
   WIDGET TAB
══════════════════════════════════════════════ */
function renderWidget(){
  api('/dashboard/api/embed-code').then(function(data){
    var c = document.getElementById('content');
    c.innerHTML =
      '<div class="section-card">' +
        '<div class="section-header"><h3>Chat Widget</h3></div>' +
        '<div class="embed-wrap">' +
          '<h3>Embed on your website</h3>' +
          '<p>Copy this one line of code and paste it just before the <code>&lt;/body&gt;</code> tag on your website. ' +
          'A chat bubble will appear for visitors to ask questions and request callbacks.</p>' +
          '<pre id="embed-code">'+esc(data.embed_code)+'</pre>' +
          '<button class="btn-copy" id="copy-btn">Copy Code</button>' +
          '<div class="preview-note">' +
            '<strong>Tip:</strong> Works on any website — WordPress, Wix, Squarespace, or custom HTML. ' +
            'The widget is mobile-friendly and loads in Hindi/English automatically.' +
          '</div>' +
        '</div>' +
      '</div>';
    document.getElementById('copy-btn').addEventListener('click', function(){
      navigator.clipboard.writeText(data.embed_code).then(function(){
        document.getElementById('copy-btn').textContent='Copied! ✓';
        setTimeout(function(){ document.getElementById('copy-btn').textContent='Copy Code'; },2000);
      });
    });
  });
}

/* ══════════════════════════════════════════════
   HELPERS
══════════════════════════════════════════════ */
function statCard(label, value, cls, sub){
  return '<div class="stat-card'+(cls?' '+cls:'')+'">'+
    '<div class="label">'+label+'</div>'+
    '<div class="value">'+(value||0)+'</div>'+
    (sub?'<div class="sub">'+sub+'</div>':'')+
  '</div>';
}

function usageCard(label, value, sub){
  return '<div class="usage-card">'+
    '<div class="u-label">'+label+'</div>'+
    '<div class="u-value">'+value+'</div>'+
    '<div class="u-sub">'+sub+'</div>'+
  '</div>';
}

function statusSel(item, tbl){
  var opts=['new','contacted','qualified','converted','lost'];
  var html='<select class="status-sel" data-table="'+tbl+'" data-id="'+item.id+'">';
  opts.forEach(function(o){
    html+='<option value="'+o+'"'+(item.status===o?' selected':'')+'>'+o.charAt(0).toUpperCase()+o.slice(1)+'</option>';
  });
  return html+'</select>';
}

function cbStatusSel(cb){
  var opts=['pending','called','no_answer'];
  var html='<select class="cb-sel status-sel" data-id="'+cb.id+'">';
  opts.forEach(function(o){
    var label=o==='no_answer'?'No Answer':o.charAt(0).toUpperCase()+o.slice(1);
    html+='<option value="'+o+'"'+(cb.status===o?' selected':'')+'>'+label+'</option>';
  });
  return html+'</select>';
}

function empty(icon, title, body){
  return '<div class="empty"><div class="e-icon">'+icon+'</div><h3>'+title+'</h3><p>'+body+'</p></div>';
}

function esc(s){
  if(!s) return '';
  var d=document.createElement('div'); d.textContent=String(s); return d.innerHTML;
}

function fmt(n){ return Number(n).toLocaleString('en-IN'); }

function fmtDate(iso){
  if(!iso) return '—';
  var d=new Date(iso);
  return d.toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'}) +
    ' ' + d.toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'});
}

/* ══════════════════════════════════════════════
   BILLING TAB
══════════════════════════════════════════════ */
function renderBilling(){
  var c = document.getElementById('content');
  c.innerHTML = '<div style="padding:40px;text-align:center;color:#94a3b8;">Loading…</div>';
  api('/api/billing/status').then(function(data){
    var status = data.subscription_status || 'trial';
    var badgeClass = 'badge-'+status;
    var badgeLabel = status.charAt(0).toUpperCase()+status.slice(1);
    var daysLeft = data.trial_ends_at
      ? Math.ceil((new Date(data.trial_ends_at)-new Date())/86400000) : null;

    var planType = data.plan_type || 'pro';
    var fee = data.monthly_fee_inr || (planType === 'starter' ? 2499 : 4999);
    var feeStr = '₹' + fee.toLocaleString('en-IN');
    var planLabel = planType === 'starter' ? 'Starter' : 'Pro';
    var callsLimit = data.calls_limit;

    var html = '<div class="billing-box">' +
      '<h3>Billing &amp; Subscription</h3>' +
      '<div class="sub-label">Manage your PropBot subscription</div>' +
      '<span class="billing-status-badge '+badgeClass+'">'+badgeLabel+'</span>' +
      ' <span style="background:#f1f5f9;color:#475569;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600;">'+planLabel+' Plan</span>';

    if(status==='trial' || status==='cancelled'){
      // Plan picker
      html +=
        '<div style="margin:20px 0 6px;font-size:13px;font-weight:600;color:#374151;">Choose your plan:</div>' +
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px;" id="plan-picker">' +
          '<div class="plan-pick'+(planType==='starter'?' plan-pick-sel':'')+'" data-plan="starter">' +
            '<div style="font-size:16px;font-weight:800;">₹2,499<span style="font-size:12px;font-weight:500;color:#6B7280;">/mo</span></div>' +
            '<div style="font-size:13px;font-weight:600;margin:4px 0 2px;">Starter</div>' +
            '<div style="font-size:12px;color:#6B7280;">50 calls/month</div>' +
          '</div>' +
          '<div class="plan-pick'+(planType==='pro'?' plan-pick-sel':'')+'" data-plan="pro">' +
            '<div style="font-size:16px;font-weight:800;">₹4,999<span style="font-size:12px;font-weight:500;color:#6B7280;">/mo</span></div>' +
            '<div style="font-size:13px;font-weight:600;margin:4px 0 2px;">Pro</div>' +
            '<div style="font-size:12px;color:#6B7280;">Unlimited calls</div>' +
          '</div>' +
        '</div>';

      if(daysLeft!==null && daysLeft>0)
        html += '<div class="trial-info">⏳ '+daysLeft+' day'+(daysLeft===1?'':'s')+' remaining in your free trial.</div>';
      else if(daysLeft!==null && daysLeft<=0)
        html += '<div class="trial-info" style="color:#ef4444;">Your trial has expired.</div>';
      html += '<button class="btn-subscribe" id="sub-btn">Subscribe Now — '+feeStr+'/month</button>';
    } else if(status==='active'){
      html += '<div class="billing-amount">'+feeStr+'</div>' +
        '<div class="billing-period">per month · Active</div>' +
        '<div class="trial-info">Your subscription is active. Thank you!</div>';
      if(callsLimit)
        html += '<div class="trial-info">📞 '+callsLimit+' calls/month included. <a href="/pricing" target="_blank">Upgrade to Pro</a> for unlimited calls.</div>';
      html += '<br><button class="btn-cancel-sub" id="cancel-btn">Cancel Subscription</button>';
    } else if(status==='paused'){
      html += '<div class="trial-info" style="color:#d97706;">Your subscription is paused.</div><br>' +
        '<button class="btn-subscribe" id="sub-btn">Reactivate — '+feeStr+'/month</button>';
    } else {
      html += '<div class="trial-info" style="color:#ef4444;">Subscription cancelled.</div><br>' +
        '<button class="btn-subscribe" id="sub-btn">Subscribe Again — '+feeStr+'/month</button>';
    }

    html += '</div>';
    c.innerHTML = html;

    // Track selected plan locally (fixes IIFE scope bug with inline onclick)
    var selectedPlan = planType;
    var fees = {starter:'₹2,499', pro:'₹4,999'};
    document.querySelectorAll('.plan-pick').forEach(function(el){
      el.addEventListener('click', function(){
        selectedPlan = el.dataset.plan;
        document.querySelectorAll('.plan-pick').forEach(function(x){
          x.classList.toggle('plan-pick-sel', x.dataset.plan === selectedPlan);
        });
        var btn = document.getElementById('sub-btn');
        if(btn) btn.textContent = 'Subscribe Now — '+fees[selectedPlan]+'/month';
        // Persist to DB so billing service reads correct plan on subscribe
        fetch('/dashboard/api/me', {
          method:'PATCH',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({plan_type: selectedPlan})
        });
      });
    });

    var subBtn = document.getElementById('sub-btn');
    if(subBtn) subBtn.onclick = function(){
      subBtn.disabled=true; subBtn.textContent='Processing…';
      api('/api/billing/subscribe', {method:'POST'}).then(function(res){
        if(res.subscription_id && res.razorpay_key){
          var rzp = new Razorpay({
            key: res.razorpay_key,
            subscription_id: res.subscription_id,
            name: 'PropBot',
            description: 'AI Receptionist — Monthly Subscription',
            theme: {color: '#FF5722'},
            handler: function(){
              subBtn.textContent = 'Payment received! ✓';
              setTimeout(function(){ renderBilling(); }, 2000);
            },
            modal: {
              ondismiss: function(){
                subBtn.disabled=false;
                subBtn.textContent='Subscribe Now — '+fees[selectedPlan]+'/month';
              }
            }
          });
          rzp.open();
          subBtn.disabled=false;
        } else {
          subBtn.disabled=false; subBtn.textContent='Subscribe Now';
          alert('Could not create subscription. Please try again.');
        }
      }).catch(function(e){ subBtn.disabled=false; subBtn.textContent='Subscribe Now'; alert('Error: ' + (e && e.detail ? e.detail : 'Could not create subscription. Please try again.')); });
    };

    var cancelBtn = document.getElementById('cancel-btn');
    if(cancelBtn) cancelBtn.onclick = function(){
      if(!confirm('Cancel your subscription? Your AI receptionist will stop working at period end.')) return;
      this.disabled=true;
      api('/api/billing/cancel', {method:'POST'}).then(function(){
        renderBilling();
      }).catch(function(){ alert('Error cancelling subscription.'); });
    };
  }).catch(function(){
    c.innerHTML = '<div class="empty"><div class="e-icon">💳</div><h3>Billing unavailable</h3><p>Please try again later.</p></div>';
  });
}

/* ══════════════════════════════════════════════
   CALENDAR TAB
══════════════════════════════════════════════ */
function renderCalendar(){
  var c = document.getElementById('content');
  c.innerHTML = '<div style="padding:40px;text-align:center;color:#94a3b8;">Loading…</div>';
  api('/dashboard/api/calendar/status').then(function(data){
    var connected = data.connected;
    var html = '<div class="calendar-box">' +
      '<h3>Google Calendar</h3>' +
      '<div class="sub-label">Let your AI receptionist book property viewings directly into your calendar.</div>';

    if(connected){
      html += '<div class="calendar-connected"><span>✅ Google Calendar Connected</span></div>' +
        '<button class="btn-disconnect-cal" id="disc-cal">Disconnect</button>';
    } else {
      html += '<div style="margin-bottom:24px;">' +
        '<div class="calendar-benefit"><span>📅</span><span>Callers can book viewings mid-call — no back and forth</span></div>' +
        '<div class="calendar-benefit"><span>⚡</span><span>Instant confirmation spoken to the caller</span></div>' +
        '<div class="calendar-benefit"><span>🔒</span><span>Read-only access to check availability, write to create events</span></div>' +
        '</div>' +
        '<a href="/dashboard/google/connect"><button class="btn-connect-cal">🔗 Connect Google Calendar</button></a>';
    }

    html += '</div>';
    c.innerHTML = html;

    var discBtn = document.getElementById('disc-cal');
    if(discBtn) discBtn.onclick = function(){
      if(!confirm('Disconnect Google Calendar? Callers will no longer be able to book viewings.')) return;
      fetch('/dashboard/google/disconnect', {method:'POST'}).then(function(){ renderCalendar(); });
    };
  }).catch(function(){
    c.innerHTML = '<div class="empty"><div class="e-icon">📅</div><h3>Calendar unavailable</h3><p>Please try again later.</p></div>';
  });
}

})();
</script>
</body>
</html>
"""
