"""
Pricing page — /pricing

Standalone page showing Starter and Pro plans.
CTAs redirect to /signup?plan=starter or /signup?plan=pro.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_PRICING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pricing — PropBot AI Receptionist</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8fafc; color: #1e293b; min-height: 100vh; }

.header { text-align: center; padding: 56px 16px 40px; }
.header h1 { font-size: 36px; font-weight: 800; margin-bottom: 12px; }
.header p { font-size: 18px; color: #64748b; max-width: 480px; margin: 0 auto 20px; line-height: 1.5; }
.trial-badge { display: inline-block; background: #d1fae5; color: #065f46; padding: 6px 16px; border-radius: 20px; font-size: 14px; font-weight: 600; }

.plans { display: flex; gap: 24px; max-width: 840px; margin: 0 auto; padding: 0 16px 64px; justify-content: center; flex-wrap: wrap; }

.plan { background: #fff; border: 2px solid #e2e8f0; border-radius: 20px; padding: 36px 32px; flex: 1; min-width: 300px; max-width: 380px; position: relative; }
.plan.popular { border-color: #2563eb; box-shadow: 0 8px 32px rgba(37,99,235,0.12); }

.popular-badge { position: absolute; top: -14px; left: 50%; transform: translateX(-50%); background: #2563eb; color: #fff; padding: 4px 20px; border-radius: 20px; font-size: 12px; font-weight: 700; white-space: nowrap; letter-spacing: 0.5px; }

.plan-name { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
.plan-desc { color: #64748b; font-size: 14px; margin-bottom: 24px; }

.plan-price { margin-bottom: 8px; }
.plan-price .amount { font-size: 48px; font-weight: 800; color: #1e293b; }
.plan-price .currency { font-size: 22px; font-weight: 600; vertical-align: top; margin-top: 12px; display: inline-block; }
.plan-price .period { font-size: 16px; color: #64748b; }
.plan-trial { font-size: 13px; color: #059669; font-weight: 600; margin-bottom: 28px; }

.features { list-style: none; margin-bottom: 32px; }
.features li { display: flex; align-items: flex-start; gap: 10px; font-size: 15px; color: #334155; margin-bottom: 12px; }
.features li .icon { flex-shrink: 0; font-size: 16px; margin-top: 1px; }
.features li.muted { color: #94a3b8; }

.btn { display: block; width: 100%; padding: 15px; border-radius: 10px; font-size: 16px; font-weight: 700; text-align: center; text-decoration: none; cursor: pointer; border: none; transition: background 0.15s; }
.btn-primary { background: #2563eb; color: #fff; }
.btn-primary:hover { background: #1d4ed8; }
.btn-outline { background: #fff; color: #2563eb; border: 2px solid #2563eb; }
.btn-outline:hover { background: #eff6ff; }

.compare { text-align: center; padding-bottom: 48px; }
.compare p { color: #64748b; font-size: 14px; }
.compare a { color: #2563eb; text-decoration: underline; }

.faq { max-width: 640px; margin: 0 auto; padding: 0 16px 64px; }
.faq h2 { font-size: 24px; font-weight: 700; text-align: center; margin-bottom: 28px; }
.faq-item { background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px 24px; margin-bottom: 12px; }
.faq-item h3 { font-size: 15px; font-weight: 600; margin-bottom: 8px; }
.faq-item p { font-size: 14px; color: #64748b; line-height: 1.6; }

@media (max-width: 640px) {
  .header h1 { font-size: 28px; }
  .plan { padding: 28px 22px; }
  .plan-price .amount { font-size: 40px; }
}
</style>
</head>
<body>

<div class="header">
  <h1>Simple, honest pricing</h1>
  <p>Har missed call ek lost deal hai. PropBot ensures that never happens.</p>
  <span class="trial-badge">✅ 14-day free trial — no credit card needed</span>
</div>

<div class="plans">

  <!-- STARTER -->
  <div class="plan">
    <div class="plan-name">Starter</div>
    <div class="plan-desc">For solo brokers who want to try AI calling</div>
    <div class="plan-price">
      <span class="currency">₹</span><span class="amount">2,499</span>
      <span class="period"> / month</span>
    </div>
    <div class="plan-trial">14-day free trial included</div>
    <ul class="features">
      <li><span class="icon">✅</span> AI receptionist (Priya) answers all calls</li>
      <li><span class="icon">✅</span> Hindi + Hinglish conversations</li>
      <li><span class="icon">✅</span> Lead details sent to your WhatsApp</li>
      <li><span class="icon">✅</span> Lead dashboard</li>
      <li><span class="icon">✅</span> Up to 50 calls / month</li>
      <li class="muted"><span class="icon">—</span> Chat widget for website</li>
      <li class="muted"><span class="icon">—</span> Priority onboarding support</li>
    </ul>
    <a href="/signup?plan=starter" class="btn btn-outline">Start Free Trial</a>
  </div>

  <!-- PRO -->
  <div class="plan popular">
    <div class="popular-badge">MOST POPULAR</div>
    <div class="plan-name">Pro</div>
    <div class="plan-desc">For serious brokers who can't miss a single lead</div>
    <div class="plan-price">
      <span class="currency">₹</span><span class="amount">4,999</span>
      <span class="period"> / month</span>
    </div>
    <div class="plan-trial">14-day free trial included</div>
    <ul class="features">
      <li><span class="icon">✅</span> AI receptionist (Priya) answers all calls</li>
      <li><span class="icon">✅</span> Hindi + Hinglish conversations</li>
      <li><span class="icon">✅</span> Lead details sent to your WhatsApp</li>
      <li><span class="icon">✅</span> Lead dashboard</li>
      <li><span class="icon">✅</span> <strong>Unlimited calls</strong></li>
      <li><span class="icon">✅</span> Chat widget for your website</li>
      <li><span class="icon">✅</span> Priority onboarding support</li>
    </ul>
    <a href="/signup?plan=pro" class="btn btn-primary">Start Free Trial</a>
  </div>

</div>

<div class="compare">
  <p>Not sure? <a href="/signup?plan=pro">Start with Pro free for 14 days</a> — downgrade anytime.</p>
</div>

<div class="faq">
  <h2>Common questions</h2>

  <div class="faq-item">
    <h3>Do I need a credit card to start?</h3>
    <p>No. Sign up, set up your AI receptionist, and use it free for 14 days. We only ask for payment details when your trial ends.</p>
  </div>

  <div class="faq-item">
    <h3>What happens when I reach 50 calls on Starter?</h3>
    <p>Priya will politely tell callers to try again later, and you'll get a notification to upgrade. You won't be charged extra — just upgrade to Pro for unlimited calls.</p>
  </div>

  <div class="faq-item">
    <h3>Can I switch plans later?</h3>
    <p>Yes. You can upgrade from Starter to Pro at any time from your dashboard. Changes take effect immediately.</p>
  </div>

  <div class="faq-item">
    <h3>What language does Priya speak?</h3>
    <p>Hindi, Hinglish (mixed Hindi-English), and English. You can also choose a male AI voice if you prefer.</p>
  </div>

  <div class="faq-item">
    <h3>What is the "chat widget"?</h3>
    <p>A small chat button you can embed on your website or 99acres/MagicBricks listing page. Visitors can chat with Priya, and leads are captured the same way as calls.</p>
  </div>

  <div class="faq-item">
    <h3>Can I cancel anytime?</h3>
    <p>Yes, cancel from your dashboard with one click. No lock-in, no cancellation fee.</p>
  </div>
</div>

</body>
</html>
"""


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def pricing_page():
    return HTMLResponse(_PRICING_HTML)
