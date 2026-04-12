"""
Self-serve signup wizard — 2-step onboarding flow.

Step 1: Verify phone (OTP via MSG91)
Step 2: Business details + property listings → provisions Bolna agent → dashboard
"""

import hashlib
import hmac
import logging
import time

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.config import settings
from app.db.supabase_client import get_supabase

router = APIRouter()
logger = logging.getLogger(__name__)

# Default voice: Priya (ElevenLabs voice ID)
_DEFAULT_VOICE_ID = "QTKSa2Iyv0yoxvXY2V8a"
_DEFAULT_PERSONA = "Priya"
_DEFAULT_VOICE_GENDER = "female"


# ─── Session helpers ──────────────────────────────────────────────

def _set_session_cookie(response, client_id: str):
    secret = (settings.WEBHOOK_SECRET or "propbot-default-secret").encode()
    ts = int(time.time())
    sig = hmac.new(secret, f"{client_id}:{ts}".encode(), hashlib.sha256).hexdigest()[:32]
    token = f"{client_id}:{ts}:{sig}"
    response.set_cookie("propbot_session", token, max_age=7 * 24 * 3600, httponly=True, samesite="lax")


def _get_client_from_session(request: Request) -> str | None:
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


def _set_phone_cookie(response, phone: str):
    """Store verified phone in a signed cookie for Step 2."""
    secret = (settings.WEBHOOK_SECRET or "propbot-default-secret").encode()
    ts = int(time.time())
    sig = hmac.new(secret, f"phone:{phone}:{ts}".encode(), hashlib.sha256).hexdigest()[:32]
    token = f"{phone}:{ts}:{sig}"
    response.set_cookie("propbot_phone", token, max_age=1800, httponly=True, samesite="lax")


def _get_verified_phone(request: Request) -> str | None:
    """Return verified phone number from cookie, or None if invalid/expired."""
    token = request.cookies.get("propbot_phone")
    if not token:
        return None
    try:
        phone, ts_str, sig = token.split(":")
        ts = int(ts_str)
        if time.time() - ts > 1800:
            return None
        secret = (settings.WEBHOOK_SECRET or "propbot-default-secret").encode()
        expected = hmac.new(secret, f"phone:{phone}:{ts}".encode(), hashlib.sha256).hexdigest()[:32]
        if hmac.compare_digest(sig, expected):
            return phone
    except (ValueError, AttributeError):
        pass
    return None


def _ga_snippet() -> str:
    gid = settings.GA_MEASUREMENT_ID
    if not gid:
        return ""
    return (
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={gid}"></script>\n'
        f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}"
        f"gtag('js',new Date());gtag('config','{gid}');</script>"
    )


def _founder_info() -> dict:
    """Return founder pricing state: slots total, slots used, is_active."""
    try:
        slots_total = int(settings.FOUNDERS_SLOTS or 0)
    except ValueError:
        slots_total = 0
    if slots_total <= 0:
        return {"active": False, "total": 0, "used": 0, "remaining": 0}
    try:
        db = get_supabase()
        result = db.table("clients").select("id", count="exact").eq("is_founder", True).execute()
        used = result.count or 0
    except Exception:
        used = 0
    remaining = max(0, slots_total - used)
    return {"active": remaining > 0, "total": slots_total, "used": used, "remaining": remaining}


# ─── Step 1: Phone OTP ───────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def signup_step1(request: Request, plan: str = "pro"):
    plan = plan if plan in ("starter", "pro") else "pro"
    # If already logged in, redirect to dashboard
    if _get_client_from_session(request):
        return RedirectResponse("/dashboard", status_code=302)
    fi = _founder_info()
    return HTMLResponse(_build_step1_html(plan, fi).replace("<!-- __GA__ -->", _ga_snippet()))


@router.post("/api/send-otp")
async def send_otp_api(request: Request):
    body = await request.json()
    phone = str(body.get("phone", "")).strip()
    from app.services.otp_service import send_otp
    result = await send_otp(phone)
    return JSONResponse(result)


@router.post("/api/verify-otp")
async def verify_otp_api(request: Request):
    body = await request.json()
    phone = str(body.get("phone", "")).strip()
    otp = str(body.get("otp", "")).strip()
    from app.services.otp_service import verify_otp, normalize_phone
    result = await verify_otp(phone, otp)
    if result["success"]:
        # Set verified phone cookie — frontend will redirect to step2
        resp = JSONResponse(result)
        _set_phone_cookie(resp, normalize_phone(phone))
        return resp
    return JSONResponse(result)


# ─── Step 2: Business Details + Listings ─────────────────────────

@router.get("/step2", response_class=HTMLResponse)
async def signup_step2(request: Request, plan: str = "pro"):
    # Allow entry via existing session (returning user) or verified phone
    if not _get_client_from_session(request) and not _get_verified_phone(request):
        return RedirectResponse("/signup", status_code=302)
    plan = plan if plan in ("starter", "pro") else "pro"
    fi = _founder_info()
    return HTMLResponse(_build_step2_html(plan, fi).replace("<!-- __GA__ -->", _ga_snippet()))


@router.post("/step2")
async def signup_step2_submit(request: Request):
    verified_phone = _get_verified_phone(request)
    existing_client = _get_client_from_session(request)
    if not verified_phone and not existing_client:
        return RedirectResponse("/signup", status_code=302)

    form = await request.form()
    business_name = str(form.get("business_name", "")).strip()
    agent_name = str(form.get("agent_name", "")).strip()
    agent_email = str(form.get("agent_email", "")).strip()
    city = str(form.get("city", "")).strip()
    knowledge_base = str(form.get("knowledge_base", "")).strip()
    plan = str(form.get("plan", "pro")).strip()
    plan = plan if plan in ("starter", "pro") else "pro"

    if not all([business_name, agent_name, agent_email]):
        fi = _founder_info()
        err = '<p class="error">Please fill all required fields.</p>'
        return HTMLResponse(_build_step2_html(plan, fi).replace("<!-- ERROR -->", err).replace("<!-- __GA__ -->", _ga_snippet()))

    db = get_supabase()
    phone = verified_phone or ""

    # Check if email already registered — resume their session
    try:
        existing = db.table("clients").select("id").eq("agent_email", agent_email).limit(1).execute()
    except Exception as e:
        logger.error("DB error checking email: %s", e)
        fi = _founder_info()
        err = '<p class="error">Database error. Please try again.</p>'
        return HTMLResponse(_build_step2_html(plan, fi).replace("<!-- ERROR -->", err).replace("<!-- __GA__ -->", _ga_snippet()))

    if existing.data and not existing_client:
        client_id = existing.data[0]["id"]
        response = RedirectResponse("/dashboard", status_code=302)
        _set_session_cookie(response, client_id)
        return response

    # Determine founder status
    fi = _founder_info()
    is_founder = fi["active"]

    from datetime import datetime, timezone, timedelta
    trial_end = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()

    try:
        result = db.table("clients").insert({
            "business_name": business_name,
            "agent_name": agent_name,
            "agent_email": agent_email,
            "agent_phone": phone,
            "city": city,
            "knowledge_base": knowledge_base,
            "onboarding_step": 3,
            "subscription_status": "trial",
            "setup_status": "provisioning",
            "trial_ends_at": trial_end,
            "plan_type": plan,
            "is_founder": is_founder,
            "voice_id": _DEFAULT_VOICE_ID,
            "assistant_persona_name": _DEFAULT_PERSONA,
            "voice_gender": _DEFAULT_VOICE_GENDER,
        }).execute()
    except Exception as e:
        logger.warning("Insert with new columns failed, trying minimal: %s", e)
        result = db.table("clients").insert({
            "business_name": business_name,
            "agent_name": agent_name,
            "agent_email": agent_email,
            "agent_phone": phone,
            "subscription_status": "trial",
            "setup_status": "provisioning",
            "trial_ends_at": trial_end,
            "voice_id": _DEFAULT_VOICE_ID,
            "assistant_persona_name": _DEFAULT_PERSONA,
            "voice_gender": _DEFAULT_VOICE_GENDER,
        }).execute()

    client_id = result.data[0]["id"]
    logger.info("New signup: %s (%s) founder=%s", business_name, client_id, is_founder)

    # Provision voice agent async
    try:
        from app.services.onboarding_service import provision_voice_agent
        await provision_voice_agent(client_id)
        logger.info("Voice agent provisioned for %s", client_id)
    except Exception as e:
        logger.error("Failed to provision voice agent for %s: %s", client_id, e)

    response = RedirectResponse("/dashboard", status_code=302)
    _set_session_cookie(response, client_id)
    response.delete_cookie("propbot_phone")
    return response


# ─── Legacy step routes (redirect to new flow) ───────────────────

@router.get("/step3", response_class=HTMLResponse)
async def signup_step3_redirect():
    return RedirectResponse("/signup/step2", status_code=302)

@router.post("/step3")
async def signup_step3_post_redirect():
    return RedirectResponse("/signup/step2", status_code=302)


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
input[type="text"], input[type="email"], input[type="tel"], input[type="number"] { display: block; width: 100%; padding: 12px 14px; margin-top: 5px; border: 1.5px solid #E5E7EB; border-radius: 10px; font-size: 15px; font-family: inherit; color: #111827; background: #FAFAF8; transition: all .15s; }
input:focus { outline: none; border-color: #FF5722; box-shadow: 0 0 0 3px rgba(255,87,34,0.1); background: #fff; }
.btn-primary { display: block; width: 100%; padding: 14px; margin-top: 24px; background: #FF5722; color: #fff; border: none; border-radius: 12px; font-size: 16px; font-weight: 700; cursor: pointer; font-family: inherit; transition: all .2s; box-shadow: 0 4px 14px rgba(255,87,34,0.3); }
.btn-primary:hover { background: #E64A19; transform: translateY(-1px); box-shadow: 0 6px 18px rgba(255,87,34,0.35); }
.btn-primary:disabled { background: #9CA3AF; box-shadow: none; transform: none; cursor: not-allowed; }
.error { color: #DC2626; font-size: 13px; margin-bottom: 14px; padding: 10px 14px; background: #FEF2F2; border-radius: 8px; border: 1px solid #FECACA; }
.success-msg { color: #059669; font-size: 13px; margin-bottom: 14px; padding: 10px 14px; background: #ECFDF5; border-radius: 8px; border: 1px solid #A7F3D0; }
@media (max-width: 640px) { .card { padding: 22px; } .topbar { padding: 12px 16px; } }
"""


# ─── HTML Builders ────────────────────────────────────────────────

def _build_step1_html(plan: str, fi: dict) -> str:
    founder_banner = ""
    if fi["active"]:
        founder_banner = f'''
        <div style="background:linear-gradient(135deg,#fff7ed,#fff3e0);border:1px solid #fed7aa;border-radius:12px;padding:12px 16px;margin-bottom:18px;font-size:13px;color:#92400e;font-weight:600;">
          🔥 Founder pricing active — only <strong>{fi['remaining']} of {fi['total']}</strong> spots left at 30% off, forever.
        </div>'''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sign Up — PropBot</title>
<!-- __GA__ -->
<style>
{_SHARED_CSS}
.phone-row {{ display: flex; gap: 8px; }}
.phone-row .prefix {{ display: flex; align-items: center; justify-content: center; padding: 12px 14px; background: #F3F4F6; border: 1.5px solid #E5E7EB; border-radius: 10px; font-size: 15px; color: #374151; font-weight: 600; white-space: nowrap; margin-top: 5px; }}
.phone-row input {{ flex: 1; }}
.otp-section {{ display: none; margin-top: 16px; animation: fadeIn .3s; }}
.otp-section.visible {{ display: block; }}
@keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(-6px); }} to {{ opacity: 1; transform: translateY(0); }} }}
.otp-input {{ letter-spacing: 8px; font-size: 22px; font-weight: 700; text-align: center; }}
.resend-link {{ font-size: 12px; color: #6B7280; text-align: center; margin-top: 10px; }}
.resend-link a {{ color: #FF5722; cursor: pointer; text-decoration: none; }}
.plan-note {{ font-size: 13px; color: #6B7280; margin-bottom: 20px; }}
</style>
</head>
<body>
<div class="topbar">
  <a class="topbar-logo" href="/"><span>Prop</span>Bot</a>
  <a class="topbar-back" href="/">← Back to home</a>
</div>
<div class="wizard">
  <div class="steps">
    <div class="step active">1 · Verify Phone</div>
    <div class="step">2 · Business Details</div>
  </div>
  <div class="card">
    <h2>Verify your phone</h2>
    <p class="subtitle">We'll send a 6-digit OTP to confirm your number. Your AI receptionist will be ready in minutes.</p>
    {founder_banner}
    <div id="msg"></div>
    <div id="phone-section">
      <label>Mobile Number <span>*</span>
        <div class="phone-row">
          <div class="prefix">+91</div>
          <input type="tel" id="phone-input" placeholder="9876543210" maxlength="10" inputmode="numeric" />
        </div>
      </label>
      <button type="button" class="btn-primary" id="send-btn">Send OTP</button>
    </div>
    <div class="otp-section" id="otp-section">
      <label>Enter OTP <span>(sent to your mobile)</span>
        <input type="number" id="otp-input" class="otp-input" placeholder="······" maxlength="6" inputmode="numeric" />
      </label>
      <button type="button" class="btn-primary" id="verify-btn">Verify &amp; Continue →</button>
      <p class="resend-link">Didn't get it? <a id="resend-link">Resend OTP</a></p>
    </div>
  </div>
</div>
<script>
var plan = '{plan}';
function showMsg(text, isError) {{
  var el = document.getElementById('msg');
  el.innerHTML = '<p class="'+(isError?'error':'success-msg')+'">'+text+'</p>';
}}
document.getElementById('send-btn').onclick = function() {{
  var phone = document.getElementById('phone-input').value.trim();
  if(!phone || phone.length < 10) {{ showMsg('Enter a valid 10-digit mobile number.', true); return; }}
  var btn = this; btn.disabled = true; btn.textContent = 'Sending…';
  fetch('/signup/api/send-otp', {{
    method: 'POST', headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{phone: phone}})
  }}).then(function(r) {{ return r.json(); }}).then(function(d) {{
    if(d.success) {{
      showMsg('OTP sent to +91 ' + phone, false);
      document.getElementById('otp-section').classList.add('visible');
      document.getElementById('otp-input').focus();
      btn.textContent = 'Resend OTP';
      btn.disabled = false;
    }} else {{
      showMsg(d.message, true);
      btn.textContent = 'Send OTP';
      btn.disabled = false;
    }}
  }}).catch(function() {{
    showMsg('Network error. Please try again.', true);
    btn.textContent = 'Send OTP'; btn.disabled = false;
  }});
}};
document.getElementById('verify-btn').onclick = function() {{
  var phone = document.getElementById('phone-input').value.trim();
  var otp = document.getElementById('otp-input').value.trim();
  if(!otp || otp.length < 6) {{ showMsg('Enter the 6-digit OTP.', true); return; }}
  var btn = this; btn.disabled = true; btn.textContent = 'Verifying…';
  fetch('/signup/api/verify-otp', {{
    method: 'POST', headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{phone: phone, otp: otp}})
  }}).then(function(r) {{ return r.json(); }}).then(function(d) {{
    if(d.success) {{
      showMsg('Phone verified! Redirecting…', false);
      window.location.href = '/signup/step2?plan=' + plan;
    }} else {{
      showMsg(d.message, true);
      btn.textContent = 'Verify & Continue →';
      btn.disabled = false;
    }}
  }}).catch(function() {{
    showMsg('Network error. Please try again.', true);
    btn.textContent = 'Verify & Continue →'; btn.disabled = false;
  }});
}};
document.getElementById('resend-link').onclick = function() {{
  document.getElementById('send-btn').click();
}};
document.getElementById('otp-input').addEventListener('keydown', function(e) {{
  if(e.key === 'Enter') document.getElementById('verify-btn').click();
}});
document.getElementById('phone-input').addEventListener('keydown', function(e) {{
  if(e.key === 'Enter') document.getElementById('send-btn').click();
}});
</script>
</body>
</html>
"""


def _build_step2_html(plan: str, fi: dict) -> str:
    if plan == "starter":
        if fi["active"]:
            plan_label = "Starter — ₹1,749/month (30% founder discount)"
            plan_color = "#059669"
        else:
            plan_label = "Starter — ₹2,499/month"
            plan_color = "#059669"
        plan_bg = "#ecfdf5"; plan_border = "#6ee7b7"
    else:
        if fi["active"]:
            plan_label = "Pro — ₹3,499/month (30% founder discount)"
            plan_color = "#2563eb"
        else:
            plan_label = "Pro — ₹4,999/month"
            plan_color = "#2563eb"
        plan_bg = "#eff6ff"; plan_border = "#93c5fd"

    founder_banner = ""
    if fi["active"]:
        founder_banner = f'''
        <div style="background:linear-gradient(135deg,#fff7ed,#fff3e0);border:1px solid #fed7aa;border-radius:10px;padding:10px 14px;margin-bottom:16px;font-size:13px;color:#92400e;font-weight:600;">
          🎉 You're getting 30% off as a founding member — locked in forever!
        </div>'''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Business Details — PropBot</title>
<!-- __GA__ -->
<style>
{_SHARED_CSS}
.plan-pill {{ display: inline-flex; align-items: center; gap: 6px; background: {plan_bg}; border: 1px solid {plan_border}; color: {plan_color}; padding: 5px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; margin-bottom: 20px; }}
.plan-pill a {{ color: {plan_color}; font-size: 12px; margin-left: 4px; opacity: 0.7; text-decoration: underline; }}
.trial-note {{ font-size: 13px; color: #059669; font-weight: 500; margin-bottom: 16px; }}
textarea {{ width: 100%; min-height: 200px; padding: 14px; border: 1.5px solid #E5E7EB; border-radius: 10px; font-size: 13px; font-family: 'SF Mono', 'Fira Code', monospace; line-height: 1.65; resize: vertical; background: #FAFAF8; color: #111827; transition: all .15s; margin-top: 5px; }}
textarea:focus {{ outline: none; border-color: #FF5722; box-shadow: 0 0 0 3px rgba(255,87,34,0.1); background: #fff; }}
.hint-box {{ background: rgba(255,87,34,0.05); border: 1px solid rgba(255,87,34,0.2); padding: 12px 14px; border-radius: 10px; font-size: 13px; color: #374151; margin-bottom: 12px; line-height: 1.6; }}
.hint-box strong {{ color: #FF5722; }}
.section-divider {{ border: none; border-top: 1px solid #E5E7EB; margin: 24px 0; }}
</style>
</head>
<body>
<div class="topbar">
  <a class="topbar-logo" href="/"><span>Prop</span>Bot</a>
  <a class="topbar-back" href="/">← Back to home</a>
</div>
<div class="wizard">
  <div class="steps">
    <div class="step done">1 · Verify Phone</div>
    <div class="step active">2 · Business Details</div>
  </div>
  <div class="card">
    <h2>Set up your account</h2>
    <div class="plan-pill">✓ {plan_label}<a href="/pricing">change</a></div>
    <p class="trial-note">✅ 14-day free trial — no credit card needed</p>
    {founder_banner}
    <!-- ERROR -->
    <form method="POST" action="/signup/step2" onsubmit="if(typeof gtag==='function')gtag('event','sign_up',{{method:'phone'}})">
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
      <label>City <span>optional</span>
        <input type="text" name="city" placeholder="e.g. Delhi, Mumbai, Bangalore" />
      </label>
      <hr class="section-divider" />
      <label>Property Listings <span>optional — add later from dashboard</span></label>
      <div class="hint-box"><strong>Tip:</strong> Use <code>##</code> for each property name. The more detail you add, the better your AI answers buyer questions.</div>
      <textarea name="knowledge_base" placeholder="## Green Valley Apartments, Sector 150 Noida&#10;- Type: 2BHK, 3BHK&#10;- Price: 55 lakh - 85 lakh&#10;- Possession: June 2026&#10;- Features: Swimming pool, gym, 24/7 security&#10;&#10;## Royal Heights, Sector 56 Gurgaon&#10;- Type: 3BHK, 4BHK&#10;- Price: 1.2 crore - 1.8 crore"></textarea>
      <button type="submit" class="btn-primary">Launch My AI Receptionist 🚀</button>
    </form>
  </div>
</div>
</body>
</html>
"""
