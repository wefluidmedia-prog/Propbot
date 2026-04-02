"""
Self-serve client signup.

GET  /signup  → polished signup HTML page
POST /signup  → create account in Supabase, send welcome email
"""

import asyncio
import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.config import settings
from app.db.supabase_client import get_supabase

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def signup_page():
    return HTMLResponse(SIGNUP_HTML)


@router.post("")
@router.post("/")
async def create_account(request: Request):
    body = await request.json()

    # Validate required fields
    required = {
        "business_name": "Business name",
        "agent_name": "Your name",
        "agent_email": "Email address",
        "agent_phone": "Phone number",
        "city": "City",
    }
    for field, label in required.items():
        if not str(body.get(field, "")).strip():
            return JSONResponse({"error": f"{label} is required."}, status_code=400)

    email = body["agent_email"].strip().lower()
    phone = body["agent_phone"].strip()

    # Basic phone normalisation — add +91 if bare 10-digit number
    if phone.isdigit() and len(phone) == 10:
        phone = f"+91{phone}"

    db = get_supabase()

    # Duplicate email check
    existing = db.table("clients").select("id").eq("agent_email", email).limit(1).execute()
    if existing.data:
        return JSONResponse(
            {"error": "This email is already registered. Please log in to your dashboard."},
            status_code=409,
        )

    # Build default first message
    persona_name = "Priya"
    first_message = (
        f"Namaste! {body['business_name'].strip()} mein aapka swagat hai. "
        f"Main {persona_name} hoon, aapki kya madad kar sakti hoon?"
    )

    client_data = {
        "business_name": body["business_name"].strip(),
        "agent_name": body["agent_name"].strip(),
        "agent_email": email,
        "agent_phone": phone,
        "city": body.get("city", "").strip(),
        "specialty": body.get("specialty", "").strip(),
        "subscription_status": "trial",
        "assistant_persona_name": persona_name,
        "voice_gender": "female",
        "voice_id": "",
        "first_message": first_message,
    }

    result = db.table("clients").insert(client_data).execute()
    client_id = result.data[0]["id"]
    logger.info(f"New signup: {client_id} — {email}")

    # Send welcome email (best-effort, non-blocking)
    if settings.SMTP_EMAIL:
        asyncio.create_task(
            _send_welcome_email(
                email=email,
                agent_name=body["agent_name"].strip(),
                business_name=body["business_name"].strip(),
            )
        )

    return JSONResponse({"success": True})


async def _send_welcome_email(email: str, agent_name: str, business_name: str) -> None:
    from app.services.alert_service import _send_email

    dashboard_url = f"{settings.BASE_URL}/dashboard"
    try:
        await asyncio.to_thread(
            _send_email,
            to=email,
            subject=f"Welcome to PropBot — {business_name}",
            body=f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
            max-width:560px;margin:0 auto;background:#fff;border-radius:16px;
            overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);">
  <div style="background:linear-gradient(135deg,#2563eb,#1d4ed8);padding:32px;">
    <h1 style="color:#fff;margin:0;font-size:26px;font-weight:700;">Welcome to PropBot!</h1>
    <p style="color:#bfdbfe;margin:8px 0 0;font-size:15px;">Your AI receptionist is being set up</p>
  </div>
  <div style="padding:32px;">
    <p style="font-size:16px;color:#1e293b;margin:0 0 16px;">Hi {agent_name},</p>
    <p style="color:#475569;line-height:1.7;margin:0 0 24px;">
      Thank you for signing up! Your PropBot account for
      <strong>{business_name}</strong> has been created successfully.
    </p>
    <div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;padding:20px;margin:0 0 28px;">
      <p style="margin:0 0 10px;font-weight:600;color:#0369a1;">What happens next:</p>
      <ol style="margin:0;padding-left:18px;color:#0c4a6e;line-height:2;">
        <li>Our team assigns your dedicated Indian phone number (within 24h)</li>
        <li>Your AI assistant <strong>Priya</strong> goes live on that number</li>
        <li>Leads captured from every call appear in your dashboard instantly</li>
      </ol>
    </div>
    <div style="text-align:center;margin:0 0 28px;">
      <a href="{dashboard_url}"
         style="display:inline-block;padding:14px 40px;background:#2563eb;color:#fff;
                text-decoration:none;border-radius:10px;font-weight:700;font-size:16px;">
        Open My Dashboard
      </a>
    </div>
    <p style="color:#94a3b8;font-size:13px;border-top:1px solid #e2e8f0;padding-top:16px;margin:0;">
      Dashboard: {dashboard_url}<br>
      Questions? Just reply to this email.
    </p>
  </div>
</div>
""",
        )
        logger.info(f"Welcome email sent to {email}")
    except Exception as exc:
        logger.error(f"Welcome email failed: {exc}")


# ─── Signup HTML ─────────────────────────────────────────────────────────────

SIGNUP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PropBot — Sign Up Free</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f0f6ff;
  min-height: 100vh;
  display: flex;
  align-items: stretch;
}

/* ── Layout ── */
.page { display: flex; min-height: 100vh; width: 100%; }

.left {
  flex: 1;
  background: linear-gradient(145deg, #1d4ed8, #2563eb, #3b82f6);
  padding: 60px 48px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  color: #fff;
}
.left-logo { font-size: 28px; font-weight: 800; letter-spacing: -0.5px; margin-bottom: 48px; }
.left-logo span { opacity: 0.7; font-weight: 400; }
.left h1 { font-size: 38px; font-weight: 800; line-height: 1.2; margin-bottom: 16px; }
.left p { font-size: 17px; color: #bfdbfe; line-height: 1.7; margin-bottom: 40px; }

.benefit { display: flex; align-items: flex-start; gap: 14px; margin-bottom: 20px; }
.benefit-icon {
  width: 36px; height: 36px; background: rgba(255,255,255,0.15);
  border-radius: 8px; display: flex; align-items: center; justify-content: center;
  font-size: 18px; flex-shrink: 0; margin-top: 2px;
}
.benefit-text strong { display: block; font-size: 15px; font-weight: 600; }
.benefit-text span { font-size: 14px; color: #bfdbfe; }

.price-pill {
  display: inline-flex; align-items: center; gap: 10px;
  background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.2);
  border-radius: 50px; padding: 10px 20px; margin-top: 40px;
  font-size: 14px; color: #e0f2fe;
}
.price-pill strong { color: #fff; font-size: 18px; }

/* ── Right / Form ── */
.right {
  width: 480px;
  background: #fff;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 60px 48px;
  box-shadow: -8px 0 40px rgba(0,0,0,0.08);
}
.form-header { margin-bottom: 32px; }
.form-header h2 { font-size: 26px; font-weight: 700; color: #1e293b; margin-bottom: 6px; }
.form-header p { color: #64748b; font-size: 15px; }

.field { margin-bottom: 18px; }
.field label { display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 6px; }
.field input, .field select {
  width: 100%; padding: 11px 14px;
  border: 1.5px solid #d1d5db; border-radius: 8px;
  font-size: 15px; color: #1e293b;
  transition: border-color 0.15s, box-shadow 0.15s;
  background: #fff;
  appearance: none;
}
.field input:focus, .field select:focus {
  outline: none; border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.12);
}
.field input.error { border-color: #ef4444; }
.field-row { display: flex; gap: 12px; }
.field-row .field { flex: 1; }

.specialty-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 8px; margin-top: 4px;
}
.specialty-opt {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; border: 1.5px solid #e2e8f0;
  border-radius: 8px; cursor: pointer; font-size: 14px;
  color: #374151; transition: all 0.15s; user-select: none;
}
.specialty-opt:hover { border-color: #93c5fd; background: #eff6ff; }
.specialty-opt input { display: none; }
.specialty-opt.checked { border-color: #2563eb; background: #eff6ff; color: #1d4ed8; font-weight: 500; }

.btn-submit {
  width: 100%; padding: 14px;
  background: #2563eb; color: #fff;
  border: none; border-radius: 10px;
  font-size: 16px; font-weight: 700;
  cursor: pointer; margin-top: 8px;
  transition: background 0.15s, transform 0.1s;
}
.btn-submit:hover { background: #1d4ed8; }
.btn-submit:active { transform: scale(0.99); }
.btn-submit:disabled { opacity: 0.6; cursor: not-allowed; }

.login-link {
  text-align: center; margin-top: 20px;
  font-size: 14px; color: #64748b;
}
.login-link a { color: #2563eb; text-decoration: none; font-weight: 500; }
.login-link a:hover { text-decoration: underline; }

/* ── States ── */
.error-msg {
  background: #fef2f2; border: 1px solid #fecaca;
  color: #b91c1c; padding: 12px 16px; border-radius: 8px;
  font-size: 14px; margin-bottom: 16px; display: none;
}
.success-state { display: none; text-align: center; }
.success-icon {
  width: 72px; height: 72px; background: #d1fae5;
  border-radius: 50%; display: flex; align-items: center;
  justify-content: center; font-size: 32px; margin: 0 auto 20px;
}
.success-state h3 { font-size: 22px; color: #1e293b; margin-bottom: 10px; }
.success-state p { color: #475569; font-size: 15px; line-height: 1.6; }
.btn-dashboard {
  display: inline-block; margin-top: 24px; padding: 12px 32px;
  background: #2563eb; color: #fff; text-decoration: none;
  border-radius: 8px; font-weight: 600; font-size: 15px;
}

/* ── Responsive ── */
@media (max-width: 900px) {
  .page { flex-direction: column; }
  .left { padding: 40px 24px; }
  .left h1 { font-size: 28px; }
  .right { width: 100%; padding: 40px 24px; box-shadow: none; }
  .field-row { flex-direction: column; gap: 0; }
}
</style>
</head>
<body>
<div class="page">

  <!-- Left: branding + benefits -->
  <div class="left">
    <div class="left-logo">Prop<span>Bot</span></div>
    <h1>Your AI receptionist,<br>working 24/7</h1>
    <p>Never miss a lead again. PropBot answers every call, qualifies buyers, and sends you instant alerts — even at midnight.</p>

    <div class="benefit">
      <div class="benefit-icon">📞</div>
      <div class="benefit-text">
        <strong>Answers every call instantly</strong>
        <span>In Hindi, English, or Hinglish — sounds human</span>
      </div>
    </div>
    <div class="benefit">
      <div class="benefit-icon">🎯</div>
      <div class="benefit-text">
        <strong>Qualifies leads automatically</strong>
        <span>Budget, area, urgency — captured before you pick up</span>
      </div>
    </div>
    <div class="benefit">
      <div class="benefit-icon">⚡</div>
      <div class="benefit-text">
        <strong>Instant alerts to your phone</strong>
        <span>SMS + email the moment a hot lead calls</span>
      </div>
    </div>
    <div class="benefit">
      <div class="benefit-icon">📊</div>
      <div class="benefit-text">
        <strong>Full dashboard to track leads</strong>
        <span>Call history, transcripts, lead status — all in one place</span>
      </div>
    </div>

    <div class="price-pill">
      Flat <strong>₹5,000/month</strong> &nbsp;·&nbsp; No per-minute charges
    </div>
  </div>

  <!-- Right: signup form -->
  <div class="right">
    <div class="form-header">
      <h2>Get started free</h2>
      <p>Set up your AI receptionist in 2 minutes</p>
    </div>

    <div class="error-msg" id="error-msg"></div>

    <div id="form-area">
      <div class="field-row">
        <div class="field">
          <label>Your Name</label>
          <input type="text" id="agent_name" placeholder="Rahul Sharma" autocomplete="name" />
        </div>
        <div class="field">
          <label>Business Name</label>
          <input type="text" id="business_name" placeholder="Sharma Properties" />
        </div>
      </div>

      <div class="field">
        <label>Email Address</label>
        <input type="email" id="agent_email" placeholder="rahul@sharmaproperties.com" autocomplete="email" />
      </div>

      <div class="field-row">
        <div class="field">
          <label>Mobile Number</label>
          <input type="tel" id="agent_phone" placeholder="9876543210" autocomplete="tel" />
        </div>
        <div class="field">
          <label>City</label>
          <input type="text" id="city" placeholder="Delhi NCR" />
        </div>
      </div>

      <div class="field">
        <label>Property Speciality (optional)</label>
        <div class="specialty-grid" id="specialty-grid">
          <div class="specialty-opt" data-val="Residential">
            <input type="checkbox"> 🏠 Residential
          </div>
          <div class="specialty-opt" data-val="Commercial">
            <input type="checkbox"> 🏢 Commercial
          </div>
          <div class="specialty-opt" data-val="Plots">
            <input type="checkbox"> 🌍 Plots & Land
          </div>
          <div class="specialty-opt" data-val="Luxury">
            <input type="checkbox"> ✨ Luxury
          </div>
        </div>
      </div>

      <button class="btn-submit" id="submit-btn">Create My Account →</button>
      <div class="login-link">Already registered? <a href="/dashboard">Login to dashboard</a></div>
    </div>

    <div class="success-state" id="success-state">
      <div class="success-icon">✅</div>
      <h3>Account created!</h3>
      <p>
        We've sent a welcome email to <strong id="success-email"></strong> with everything you need.<br><br>
        Your dedicated phone number will be assigned within 24 hours. In the meantime, explore your dashboard and customise your AI assistant.
      </p>
      <a href="/dashboard" class="btn-dashboard">Open Dashboard</a>
    </div>
  </div>
</div>

<script>
(function () {
  // Specialty checkboxes
  document.querySelectorAll('.specialty-opt').forEach(function (el) {
    el.addEventListener('click', function () {
      this.classList.toggle('checked');
    });
  });

  document.getElementById('submit-btn').addEventListener('click', function () {
    submit();
  });

  // Allow Enter key on last field
  document.getElementById('city').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') submit();
  });

  function getSpecialty() {
    var vals = [];
    document.querySelectorAll('.specialty-opt.checked').forEach(function (el) {
      vals.push(el.dataset.val);
    });
    return vals.join(', ');
  }

  function showError(msg) {
    var el = document.getElementById('error-msg');
    el.textContent = msg;
    el.style.display = 'block';
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function hideError() {
    document.getElementById('error-msg').style.display = 'none';
  }

  function submit() {
    hideError();
    var btn = document.getElementById('submit-btn');
    var payload = {
      agent_name:    document.getElementById('agent_name').value.trim(),
      business_name: document.getElementById('business_name').value.trim(),
      agent_email:   document.getElementById('agent_email').value.trim(),
      agent_phone:   document.getElementById('agent_phone').value.trim(),
      city:          document.getElementById('city').value.trim(),
      specialty:     getSpecialty(),
    };

    var required = { agent_name: 'Your name', business_name: 'Business name', agent_email: 'Email', agent_phone: 'Phone', city: 'City' };
    for (var k in required) {
      if (!payload[k]) { showError(required[k] + ' is required.'); return; }
    }

    btn.disabled = true;
    btn.textContent = 'Creating account…';

    fetch('/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
    .then(function (res) {
      if (!res.ok) {
        showError(res.data.error || 'Something went wrong. Please try again.');
        btn.disabled = false;
        btn.textContent = 'Create My Account →';
        return;
      }
      // Success
      document.getElementById('success-email').textContent = payload.agent_email;
      document.getElementById('form-area').style.display = 'none';
      document.getElementById('success-state').style.display = 'block';
    })
    .catch(function () {
      showError('Network error. Please check your connection and try again.');
      btn.disabled = false;
      btn.textContent = 'Create My Account →';
    });
  }
})();
</script>
</body>
</html>
"""
