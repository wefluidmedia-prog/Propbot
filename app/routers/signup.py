"""
Self-serve signup wizard — 3-step onboarding flow.

Step 1: Business details → creates client row
Step 2: Choose voice → saves voice selection
Step 3: Property listings → saves KB, provisions Bolna agent, redirects to dashboard
"""

import logging
import time
import hmac
import hashlib

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import settings
from app.db.supabase_client import get_supabase
from app.voice.voice_catalog import get_catalog

router = APIRouter()
logger = logging.getLogger(__name__)


def _set_session_cookie(response, client_id: str):
    """Set session cookie after signup (same as dashboard auth)."""
    secret = (settings.WEBHOOK_SECRET or "propbot-default-secret").encode()
    ts = int(time.time())
    sig = hmac.new(secret, f"{client_id}:{ts}".encode(), hashlib.sha256).hexdigest()[:32]
    token = f"{client_id}:{ts}:{sig}"
    response.set_cookie("propbot_session", token, max_age=7 * 24 * 3600, httponly=True, samesite="lax")


def _get_client_from_session(request: Request) -> str | None:
    """Get client_id from session cookie, or None."""
    token = request.cookies.get("propbot_session")
    if not token:
        return None
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


# ─── Step 1: Business Details ────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def signup_step1(request: Request, plan: str = Query(default="pro")):
    plan = plan if plan in ("starter", "pro") else "pro"
    # If already signed up, redirect to appropriate step
    client_id = _get_client_from_session(request)
    if client_id:
        try:
            db = get_supabase()
            result = db.table("clients").select("onboarding_step").eq("id", client_id).single().execute()
            if result.data:
                step = result.data.get("onboarding_step") or 0
                if step >= 3:
                    return RedirectResponse("/dashboard", status_code=302)
                elif step == 2:
                    return RedirectResponse("/signup/step3", status_code=302)
                elif step == 1:
                    return RedirectResponse("/signup/step2", status_code=302)
        except Exception:
            pass  # If DB query fails (e.g. column missing), just show the form
    return HTMLResponse(_build_step1_html(plan))


@router.post("")
@router.post("/")
async def signup_step1_submit(request: Request):
    form = await request.form()
    business_name = str(form.get("business_name", "")).strip()
    agent_name = str(form.get("agent_name", "")).strip()
    agent_email = str(form.get("agent_email", "")).strip()
    agent_phone = str(form.get("agent_phone", "")).strip()
    city = str(form.get("city", "")).strip()

    plan = str(form.get("plan", "pro")).strip()
    plan = plan if plan in ("starter", "pro") else "pro"

    if not all([business_name, agent_name, agent_email, agent_phone]):
        return HTMLResponse(_build_step1_html(plan).replace("<!-- ERROR -->", '<p class="error">Please fill all required fields.</p>'))

    # Check if email already exists
    db = get_supabase()
    try:
        existing = db.table("clients").select("id").eq("agent_email", agent_email).limit(1).execute()
    except Exception as e:
        logger.error("DB error checking email: %s", e)
        return HTMLResponse(_build_step1_html(plan).replace("<!-- ERROR -->", '<p class="error">Database error. Please try again.</p>'))

    if existing.data:
        # Resume existing signup
        client_id = existing.data[0]["id"]
        response = RedirectResponse("/signup/step2", status_code=302)
        _set_session_cookie(response, client_id)
        return response

    # Create new client — try with new columns, fall back to core if migration not applied
    from datetime import datetime, timezone, timedelta
    trial_end = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    try:
        result = db.table("clients").insert({
            "business_name": business_name,
            "agent_name": agent_name,
            "agent_email": agent_email,
            "agent_phone": agent_phone,
            "city": city,
            "onboarding_step": 1,
            "subscription_status": "trial",
            "setup_status": "provisioning",
            "trial_ends_at": trial_end,
            "plan_type": plan,
        }).execute()
    except Exception:
        # Migration may not have been applied — insert without new columns
        result = db.table("clients").insert({
            "business_name": business_name,
            "agent_name": agent_name,
            "agent_email": agent_email,
            "agent_phone": agent_phone,
            "subscription_status": "trial",
            "setup_status": "provisioning",
            "trial_ends_at": trial_end,
        }).execute()

    client_id = result.data[0]["id"]
    logger.info("New signup: %s (%s)", business_name, client_id)

    response = RedirectResponse("/signup/step2", status_code=302)
    _set_session_cookie(response, client_id)
    return response


# ─── Step 2: Choose Voice ────────────────────────────────────────

@router.get("/step2", response_class=HTMLResponse)
async def signup_step2(request: Request):
    client_id = _get_client_from_session(request)
    if not client_id:
        return RedirectResponse("/signup", status_code=302)
    return HTMLResponse(_build_step2_html())


@router.post("/step2")
async def signup_step2_submit(request: Request):
    client_id = _get_client_from_session(request)
    if not client_id:
        return RedirectResponse("/signup", status_code=302)

    form = await request.form()
    voice_id = str(form.get("voice_id", "")).strip()
    persona_name = str(form.get("persona_name", "")).strip() or "Priya"
    voice_gender = str(form.get("voice_gender", "female")).strip()

    # Find voice name from catalog
    from app.voice.voice_catalog import get_voice_by_id
    voice = get_voice_by_id(voice_id)
    voice_name = voice["name"] if voice else persona_name

    db = get_supabase()
    db.table("clients").update({
        "voice_id": voice_id,
        "voice_gender": voice_gender,
        "assistant_persona_name": persona_name,
        "onboarding_step": 2,
    }).eq("id", client_id).execute()

    return RedirectResponse("/signup/step3", status_code=302)


# ─── Step 3: Property Listings ───────────────────────────────────

@router.get("/step3", response_class=HTMLResponse)
async def signup_step3(request: Request):
    client_id = _get_client_from_session(request)
    if not client_id:
        return RedirectResponse("/signup", status_code=302)
    return HTMLResponse(STEP3_HTML)


@router.post("/step3")
async def signup_step3_submit(request: Request):
    client_id = _get_client_from_session(request)
    if not client_id:
        return RedirectResponse("/signup", status_code=302)

    form = await request.form()
    knowledge_base = str(form.get("knowledge_base", "")).strip()

    if not knowledge_base:
        return HTMLResponse(STEP3_HTML.replace("<!-- ERROR -->", '<p class="error">Please add at least some property details.</p>'))

    db = get_supabase()
    db.table("clients").update({
        "knowledge_base": knowledge_base,
    }).eq("id", client_id).execute()

    # Provision voice agent (async)
    try:
        from app.services.onboarding_service import provision_voice_agent
        await provision_voice_agent(client_id)
        logger.info("Voice agent provisioned for %s", client_id)
    except Exception as e:
        logger.error("Failed to provision voice agent for %s: %s", client_id, e)
        # Still redirect to dashboard — they can use chat, agent can be retried
        db.table("clients").update({"onboarding_step": 3}).eq("id", client_id).execute()

    return RedirectResponse("/dashboard", status_code=302)


# ─── Voice catalog API ───────────────────────────────────────────

@router.get("/api/voices")
async def list_voices():
    """Public endpoint — returns the voice catalog."""
    return {"voices": get_catalog()}


# ─── Shared CSS ──────────────────────────────────────────────────

_SHARED_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: #FAFAF8; color: #111827; min-height: 100vh; -webkit-font-smoothing: antialiased; }
.topbar { background: rgba(250,250,248,0.9); backdrop-filter: blur(12px); border-bottom: 1px solid #E5E7EB; padding: 12px 32px; display: flex; justify-content: space-between; align-items: center; }
.topbar-logo { font-size: 18px; font-weight: 800; color: #111827; text-decoration: none; letter-spacing: -0.5px; }
.topbar-logo span { color: #FF5722; }
.topbar-back { font-size: 13px; color: #6B7280; text-decoration: none; }
.topbar-back:hover { color: #111827; }
.wizard { max-width: 580px; margin: 0 auto; padding: 32px 16px 48px; }
.steps { display: flex; gap: 8px; margin-bottom: 28px; }
.step { flex: 1; text-align: center; padding: 10px 6px; font-size: 12px; font-weight: 600; color: #9CA3AF; background: #fff; border-radius: 10px; border: 1px solid #E5E7EB; letter-spacing: 0.2px; }
.step.active { color: #FF5722; border-color: #FF5722; background: rgba(255,87,34,0.06); }
.step.done { color: #10B981; border-color: #10B981; background: #ECFDF5; }
.card { background: #fff; padding: 36px; border-radius: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04); border: 1px solid #E5E7EB; }
.card h2 { font-size: 22px; font-weight: 800; letter-spacing: -0.5px; margin-bottom: 6px; }
.card .subtitle { color: #6B7280; font-size: 14px; margin-bottom: 24px; line-height: 1.55; }
label { display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 16px; }
label span { font-weight: 400; color: #9CA3AF; margin-left: 4px; }
input[type="text"], input[type="email"], input[type="tel"] { display: block; width: 100%; padding: 12px 14px; margin-top: 5px; border: 1.5px solid #E5E7EB; border-radius: 10px; font-size: 15px; font-family: inherit; color: #111827; background: #FAFAF8; transition: all .15s; }
input:focus { outline: none; border-color: #FF5722; box-shadow: 0 0 0 3px rgba(255,87,34,0.1); background: #fff; }
.btn-primary { display: block; width: 100%; padding: 14px; margin-top: 24px; background: #FF5722; color: #fff; border: none; border-radius: 12px; font-size: 16px; font-weight: 700; cursor: pointer; font-family: inherit; transition: all .2s; box-shadow: 0 4px 14px rgba(255,87,34,0.3); }
.btn-primary:hover { background: #E64A19; transform: translateY(-1px); box-shadow: 0 6px 18px rgba(255,87,34,0.35); }
.error { color: #DC2626; font-size: 13px; margin-bottom: 14px; padding: 10px 14px; background: #FEF2F2; border-radius: 8px; border: 1px solid #FECACA; }
@media (max-width: 640px) { .card { padding: 22px; } .topbar { padding: 12px 16px; } }
"""

_STEP2_CSS = """
.voice-grid { display: flex; flex-direction: column; gap: 10px; margin-bottom: 16px; }
.voice-card { display: block; cursor: pointer; border: 1.5px solid #E5E7EB; border-radius: 12px; padding: 14px 16px; transition: all .15s; background: #FAFAF8; }
.voice-card:hover { border-color: rgba(255,87,34,0.4); background: #fff; }
.voice-card input[type="radio"] { display: none; }
.voice-card:has(input:checked) { border-color: #FF5722; background: rgba(255,87,34,0.04); box-shadow: 0 0 0 3px rgba(255,87,34,0.1); }
.voice-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; flex-wrap: wrap; }
.voice-meta { font-size: 12px; color: #6B7280; margin-bottom: 4px; }
.voice-desc { font-size: 13px; color: #374151; line-height: 1.5; }
.gender-tag { font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 600; }
.tag-f { background: #FCE7F3; color: #BE185D; }
.tag-m { background: #DBEAFE; color: #1D4ED8; }
.rec-badge { font-size: 11px; padding: 2px 8px; background: #D1FAE5; color: #065F46; border-radius: 10px; font-weight: 600; }
.filter-bar { display: flex; gap: 8px; margin-bottom: 16px; }
.filter-btn { padding: 6px 16px; border: 1.5px solid #E5E7EB; border-radius: 20px; background: #fff; font-size: 13px; font-weight: 500; cursor: pointer; color: #6B7280; font-family: inherit; transition: all .15s; }
.filter-btn.active { background: #FF5722; color: #fff; border-color: #FF5722; }
.filter-btn:hover:not(.active) { border-color: #FF5722; color: #FF5722; }
.persona-field { margin-top: 14px; }
"""


# ─── HTML Templates ──────────────────────────────────────────────

def _build_step1_html(plan: str = "pro") -> str:
    """Build Step 1 HTML showing the selected plan and a hidden plan input."""
    if plan == "starter":
        plan_label = "Starter — ₹2,499/month"
        plan_color = "#059669"
        plan_bg = "#ecfdf5"
        plan_border = "#6ee7b7"
    else:
        plan_label = "Pro — ₹4,999/month"
        plan_color = "#2563eb"
        plan_bg = "#eff6ff"
        plan_border = "#93c5fd"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sign Up — PropBot</title>
<style>
{_SHARED_CSS}
.plan-pill {{
    display: inline-flex; align-items: center; gap: 6px;
    background: {plan_bg}; border: 1px solid {plan_border};
    color: {plan_color}; padding: 5px 14px; border-radius: 20px;
    font-size: 13px; font-weight: 600; margin-bottom: 20px;
}}
.plan-pill a {{ color: {plan_color}; font-size: 12px; margin-left: 4px; opacity: 0.7; text-decoration: underline; }}
.trial-note {{ font-size: 13px; color: #059669; font-weight: 500; margin-bottom: 16px; }}
</style>
</head>
<body>
<div class="topbar">
    <a class="topbar-logo" href="/"><span>Prop</span>Bot</a>
    <a class="topbar-back" href="/">← Back to home</a>
</div>
<div class="wizard">
    <div class="steps">
        <div class="step active">1 · Business Details</div>
        <div class="step">2 · Choose Voice</div>
        <div class="step">3 · Add Listings</div>
    </div>
    <div class="card">
        <h2>Tell us about your business</h2>
        <div class="plan-pill">
            ✓ {plan_label}
            <a href="/pricing">change</a>
        </div>
        <p class="trial-note">✅ 14-day free trial — no credit card needed</p>
        <!-- ERROR -->
        <form method="POST" action="/signup">
            <input type="hidden" name="plan" value="{plan}" />
            <label>Business Name <span>*</span>
                <input type="text" name="business_name" placeholder="e.g. Sharma Properties" required />
            </label>
            <label>Your Name <span>*</span>
                <input type="text" name="agent_name" placeholder="e.g. Rahul Sharma" required />
            </label>
            <label>Email <span>*</span>
                <input type="email" name="agent_email" placeholder="you@example.com" required />
            </label>
            <label>Phone <span>*</span>
                <input type="tel" name="agent_phone" placeholder="+91 98765 43210" required />
            </label>
            <label>City <span>optional</span>
                <input type="text" name="city" placeholder="e.g. Delhi, Mumbai, Bangalore" />
            </label>
            <button type="submit" class="btn-primary">Continue →</button>
        </form>
    </div>
</div>
</body>
</html>
"""


def _build_step2_html():
    """Build Step 2 HTML with voice cards from catalog."""
    voices = get_catalog()
    cards_html = ""
    for v in voices:
        rec = ' <span class="rec-badge">Recommended</span>' if v.get("recommended") else ""
        cards_html += f"""
        <label class="voice-card" data-gender="{v['gender']}">
            <input type="radio" name="voice_id" value="{v['id']}" {'checked' if v.get('recommended') and v['gender'] == 'female' else ''} />
            <div class="voice-card-inner">
                <div class="voice-header">
                    <strong>{v['name']}</strong>{rec}
                    <span class="gender-tag {'tag-f' if v['gender'] == 'female' else 'tag-m'}">{v['gender'].title()}</span>
                </div>
                <div class="voice-meta">{v['accent']} &middot; {v['language']}</div>
                <div class="voice-desc">{v['description']}</div>
            </div>
        </label>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Choose Voice — PropBot</title>
<style>
{_SHARED_CSS}
{_STEP2_CSS}
</style>
</head>
<body>
<div class="topbar">
    <a class="topbar-logo" href="/"><span>Prop</span>Bot</a>
    <a class="topbar-back" href="/">← Back to home</a>
</div>
<div class="wizard">
    <div class="steps">
        <div class="step done">1 · Business Details</div>
        <div class="step active">2 · Choose Voice</div>
        <div class="step">3 · Add Listings</div>
    </div>
    <div class="card">
        <h2>Choose your AI assistant's voice</h2>
        <p class="subtitle">Pick a voice that matches your brand. You can change this later from your dashboard.</p>
        <form method="POST" action="/signup/step2">
            <div class="filter-bar">
                <button type="button" class="filter-btn active" data-filter="all">All voices</button>
                <button type="button" class="filter-btn" data-filter="female">Female</button>
                <button type="button" class="filter-btn" data-filter="male">Male</button>
            </div>
            <div class="voice-grid">
                {cards_html}
            </div>
            <label class="persona-field">Assistant Name <span>(callers will hear this)</span>
                <input type="text" name="persona_name" placeholder="e.g. Priya, Ananya, Arjun" value="Priya" />
            </label>
            <input type="hidden" name="voice_gender" id="voice_gender" value="female" />
            <button type="submit" class="btn-primary">Continue →</button>
        </form>
    </div>
</div>
<script>
document.querySelectorAll('.filter-btn').forEach(function(btn) {{
    btn.addEventListener('click', function() {{
        document.querySelectorAll('.filter-btn').forEach(function(b) {{ b.classList.remove('active'); }});
        this.classList.add('active');
        var f = this.dataset.filter;
        document.querySelectorAll('.voice-card').forEach(function(c) {{
            c.style.display = (f === 'all' || c.dataset.gender === f) ? '' : 'none';
        }});
    }});
}});
document.querySelectorAll('input[name="voice_id"]').forEach(function(r) {{
    r.addEventListener('change', function() {{
        var card = this.closest('.voice-card');
        document.getElementById('voice_gender').value = card.dataset.gender;
    }});
}});
</script>
</body>
</html>
"""


STEP3_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Add Listings — PropBot</title>
<style>
""" + _SHARED_CSS + """
textarea { width: 100%; min-height: 280px; padding: 14px; border: 1.5px solid #E5E7EB; border-radius: 10px; font-size: 13px; font-family: 'SF Mono', 'Fira Code', monospace; line-height: 1.65; resize: vertical; background: #FAFAF8; color: #111827; transition: all .15s; }
textarea:focus { outline: none; border-color: #FF5722; box-shadow: 0 0 0 3px rgba(255,87,34,0.1); background: #fff; }
.hint-box { background: rgba(255,87,34,0.05); border: 1px solid rgba(255,87,34,0.2); padding: 14px 16px; border-radius: 10px; font-size: 13px; color: #374151; margin-bottom: 16px; line-height: 1.6; }
.hint-box strong { color: #FF5722; }
.hint-box code { background: rgba(255,87,34,0.1); color: #E64A19; padding: 1px 5px; border-radius: 4px; font-size: 12px; }
.skip-link { display: block; text-align: center; margin-top: 12px; font-size: 13px; color: #9CA3AF; }
.skip-link a { color: #6B7280; text-decoration: underline; }
</style>
</head>
<body>
<div class="topbar">
    <a class="topbar-logo" href="/"><span>Prop</span>Bot</a>
    <a class="topbar-back" href="/">← Back to home</a>
</div>
<div class="wizard">
    <div class="steps">
        <div class="step done">1 · Business Details</div>
        <div class="step done">2 · Choose Voice</div>
        <div class="step active">3 · Add Listings</div>
    </div>
    <div class="card">
        <h2>Add your property listings</h2>
        <p class="subtitle">Your AI assistant will use this to answer buyer questions. You can edit this anytime from your dashboard.</p>
        <!-- ERROR -->
        <div class="hint-box">
            <strong>Tip:</strong> Use <code>##</code> for each property name, then add details on separate lines. The more detail you add, the better your AI answers buyer questions.
        </div>
        <form method="POST" action="/signup/step3">
            <textarea name="knowledge_base" placeholder="## Green Valley Apartments, Sector 150 Noida
- Type: 2BHK, 3BHK
- Price: 55 lakh - 85 lakh
- Possession: June 2026
- Features: Swimming pool, gym, 24/7 security, metro nearby
- Area: 950 sq ft - 1400 sq ft

## Royal Heights, Sector 56 Gurgaon
- Type: 3BHK, 4BHK
- Price: 1.2 crore - 1.8 crore
- Possession: Ready to move
- Features: Golf course road, imported marble, modular kitchen
- Area: 1800 sq ft - 2400 sq ft

## FAQ
Q: Do you help with home loans?
A: Yes, we help with home loan processing through partner banks."></textarea>
            <button type="submit" class="btn-primary">Launch My AI Receptionist 🚀</button>
        </form>
        <p class="skip-link">Not ready? <a href="/dashboard">Skip and add listings later from dashboard</a></p>
    </div>
</div>
</body>
</html>
"""
