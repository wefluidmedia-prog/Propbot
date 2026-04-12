"""
Pricing page — /pricing

Redirects to the pricing section of the landing page.
"""

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()

_PRICING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pricing — PropBot AI Receptionist</title>
<!-- __GA__ -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:#FAFAF8;color:#111827;-webkit-font-smoothing:antialiased;}

/* NAV */
.nav{position:sticky;top:0;z-index:100;background:rgba(250,250,248,0.88);backdrop-filter:blur(16px);border-bottom:1px solid #E5E7EB;}
.nav-inner{display:flex;justify-content:space-between;align-items:center;padding:14px 40px;max-width:1100px;margin:0 auto;}
.nav-logo{font-size:20px;font-weight:800;color:#111827;text-decoration:none;letter-spacing:-0.5px;}
.nav-logo span{color:#FF5722;}
.nav-links{display:flex;gap:6px;align-items:center;}
.nav-links a{text-decoration:none;font-size:14px;font-weight:500;color:#6B7280;padding:7px 12px;border-radius:10px;transition:all .15s;}
.nav-links a:hover{color:#111827;background:rgba(0,0,0,0.04);}
.btn-nav{background:#FF5722!important;color:#fff!important;padding:9px 20px!important;border-radius:10px!important;font-weight:700!important;}
.btn-nav:hover{background:#E64A19!important;}

/* HEADER */
.header{text-align:center;padding:64px 24px 48px;}
.sec-label{display:inline-block;font-size:11px;font-weight:700;color:#FF5722;letter-spacing:1.8px;text-transform:uppercase;margin-bottom:12px;}
.header h1{font-size:42px;font-weight:900;letter-spacing:-1.5px;margin-bottom:12px;line-height:1.1;}
.header p{font-size:17px;color:#6B7280;max-width:460px;margin:0 auto 20px;line-height:1.65;}
.trial-badge{display:inline-flex;align-items:center;gap:6px;background:#ECFDF5;color:#065F46;padding:7px 18px;border-radius:20px;font-size:14px;font-weight:600;border:1px solid #A7F3D0;}

/* PLANS */
.plans{display:flex;gap:24px;max-width:820px;margin:0 auto;padding:0 24px 56px;justify-content:center;flex-wrap:wrap;}
.plan{background:#fff;border:2px solid #E5E7EB;border-radius:24px;padding:36px 32px;flex:1;min-width:300px;max-width:380px;position:relative;transition:all .2s;}
.plan:hover{box-shadow:0 20px 48px rgba(0,0,0,0.08);}
.plan.pop{border-color:#FF5722;box-shadow:0 8px 32px rgba(255,87,34,0.12);}
.pop-badge{position:absolute;top:-14px;left:50%;transform:translateX(-50%);background:#FF5722;color:#fff;padding:4px 20px;border-radius:20px;font-size:11px;font-weight:700;white-space:nowrap;letter-spacing:.5px;}
.pname{font-size:20px;font-weight:800;margin-bottom:4px;letter-spacing:-0.3px;}
.pdesc{color:#6B7280;font-size:14px;margin-bottom:22px;line-height:1.5;}
.pamt{font-size:52px;font-weight:900;color:#111827;line-height:1;letter-spacing:-2px;}
.pamt .cur{font-size:22px;font-weight:700;vertical-align:top;margin-top:10px;display:inline-block;letter-spacing:0;}
.pamt .per{font-size:15px;color:#6B7280;font-weight:500;letter-spacing:0;}
.ptrial{display:inline-block;margin:12px 0 24px;padding:4px 14px;background:#ECFDF5;color:#065F46;border-radius:20px;font-size:12px;font-weight:600;border:1px solid #A7F3D0;}
.feats{list-style:none;margin-bottom:28px;display:flex;flex-direction:column;gap:11px;}
.feats li{display:flex;align-items:flex-start;gap:10px;font-size:14px;color:#374151;}
.feats li .ck{color:#10B981;font-size:16px;flex-shrink:0;}
.feats li.dm{color:#9CA3AF;}
.feats li.dm .dash{color:#E5E7EB;flex-shrink:0;}
.btn{display:block;width:100%;padding:15px;border-radius:12px;font-size:16px;font-weight:700;text-align:center;text-decoration:none;cursor:pointer;border:none;transition:all .2s;font-family:inherit;}
.btn-fill{background:#FF5722;color:#fff;box-shadow:0 4px 14px rgba(255,87,34,0.3);}
.btn-fill:hover{background:#E64A19;transform:translateY(-1px);box-shadow:0 6px 18px rgba(255,87,34,0.35);}
.btn-ol{background:#fff;color:#FF5722;border:2px solid #FF5722;}
.btn-ol:hover{background:#FFF5F0;}

/* COMPARE NOTE */
.compare-note{text-align:center;padding-bottom:48px;}
.compare-note p{color:#6B7280;font-size:14px;}
.compare-note a{color:#FF5722;text-decoration:underline;}

/* COMING SOON BADGE */
.cs-tag{display:inline-block;font-size:10px;font-weight:700;color:#7C3AED;background:#EDE9FE;border:1px solid #C4B5FD;border-radius:20px;padding:1px 8px;margin-left:6px;letter-spacing:.3px;vertical-align:middle;}
.feats li.soon{color:#6B7280;}
.feats li.soon .cs-tag{opacity:.85;}

/* OUTBOUND TEASER BANNER */
.ob-banner{max-width:820px;margin:0 auto 56px;padding:0 24px;}
.ob-inner{background:linear-gradient(135deg,#1E1B4B 0%,#312E81 100%);border-radius:20px;padding:36px 40px;display:flex;align-items:center;gap:32px;flex-wrap:wrap;}
.ob-icon{font-size:48px;flex-shrink:0;}
.ob-body{flex:1;min-width:220px;}
.ob-label{font-size:11px;font-weight:700;color:#A5B4FC;letter-spacing:1.8px;text-transform:uppercase;margin-bottom:8px;}
.ob-body h3{font-size:22px;font-weight:800;color:#fff;letter-spacing:-.4px;margin-bottom:8px;line-height:1.2;}
.ob-body p{font-size:14px;color:#C7D2FE;line-height:1.65;}
.ob-cta{flex-shrink:0;}
.ob-btn{display:inline-block;padding:12px 24px;background:rgba(255,255,255,.12);border:1.5px solid rgba(255,255,255,.25);color:#fff;border-radius:12px;font-size:14px;font-weight:600;text-decoration:none;cursor:pointer;transition:all .2s;font-family:inherit;}
.ob-btn:hover{background:rgba(255,255,255,.2);}
.ob-btn input{display:none;}
@media(max-width:600px){.ob-inner{padding:28px 24px;gap:20px;}.ob-icon{font-size:36px;}}

/* FAQ */
.faq{max-width:680px;margin:0 auto;padding:0 24px 72px;}
.faq h2{font-size:28px;font-weight:800;letter-spacing:-0.5px;text-align:center;margin-bottom:32px;}
.faq-list details{border-bottom:1px solid #E5E7EB;}
.faq-list summary{padding:18px 0;font-size:15px;font-weight:600;color:#111827;cursor:pointer;list-style:none;display:flex;justify-content:space-between;align-items:center;transition:color .15s;}
.faq-list summary:hover{color:#FF5722;}
.faq-list summary::after{content:"+";font-size:22px;color:#9CA3AF;font-weight:400;flex-shrink:0;}
.faq-list details[open] summary::after{content:"\2212";color:#FF5722;}
.faq-list summary::-webkit-details-marker{display:none;}
.faq-list .fb{padding:0 0 18px;font-size:14px;color:#6B7280;line-height:1.7;}

/* FOOTER ROW */
.footer-row{background:#0D1117;padding:20px 40px;text-align:center;}
.footer-row p{font-size:12px;color:#6E7681;}
.footer-row a{color:#8B949E;text-decoration:none;}
.footer-row a:hover{color:#E6EDF3;}

@media(max-width:700px){
  .nav-inner{padding:14px 16px;}
  .nav-links a:not(.btn-nav){display:none;}
  .header{padding:48px 16px 36px;}
  .header h1{font-size:32px;}
  .plans{flex-direction:column;align-items:center;padding:0 16px 48px;}
  .plan{max-width:100%;}
  .faq{padding:0 16px 48px;}
  .footer-row{padding:20px 16px;}
}
</style>
</head>
<body>

<!-- NAV -->
<nav class="nav">
<div class="nav-inner">
  <a class="nav-logo" href="/"><span>Prop</span>Bot</a>
  <div class="nav-links">
    <a href="/#features">Features</a>
    <a href="/#demo">Demo</a>
    <a href="/#faq">FAQ</a>
    <a href="/dashboard">Login</a>
    <a href="/signup" class="btn-nav">Start Free Trial &rarr;</a>
  </div>
</div>
</nav>

<!-- HEADER -->
<div class="header">
  <div class="sec-label">Pricing</div>
  <h1>One flat price. Unlimited leads answered.</h1>
  <p>No hidden fees. No per-call charges. One flat monthly price to never miss a lead again.</p>
  <span class="trial-badge">&#10003; 14-day free trial &mdash; no credit card needed</span>
</div>

<!-- PLANS -->
<div class="plans">

  <!-- STARTER -->
  <div class="plan">
    <div class="pname">Starter</div>
    <div class="pdesc">For solo brokers starting with AI</div>
    <div class="pamt"><span class="cur">&#8377;</span>2,499<span class="per">/mo</span></div>
    <div class="ptrial">14-day free trial</div>
    <ul class="feats">
      <li><span class="ck">&#10003;</span> AI receptionist answers all calls</li>
      <li><span class="ck">&#10003;</span> Hindi + Hinglish conversations</li>
      <li><span class="ck">&#10003;</span> Lead alerts to your email</li>
      <li><span class="ck">&#10003;</span> Lead &amp; call dashboard</li>
      <li><span class="ck">&#10003;</span> Up to 50 calls / month</li>
      <li class="dm"><span class="dash">&mdash;</span> Call recordings &amp; transcripts</li>
      <li class="dm"><span class="dash">&mdash;</span> Chat widget for website</li>
      <li class="dm"><span class="dash">&mdash;</span> Priority support</li>
      <li class="soon"><span class="dash" style="color:#C4B5FD">&#9670;</span> Outbound follow-up calls <span class="cs-tag">Coming Soon</span></li>
    </ul>
    <a href="/signup?plan=starter" class="btn btn-ol">Start Free Trial</a>
  </div>

  <!-- PRO -->
  <div class="plan pop">
    <div class="pop-badge">MOST POPULAR</div>
    <div class="pname">Pro</div>
    <div class="pdesc">For serious brokers who can&rsquo;t miss a single lead</div>
    <div class="pamt"><span class="cur">&#8377;</span>4,999<span class="per">/mo</span></div>
    <div class="ptrial">14-day free trial</div>
    <ul class="feats">
      <li><span class="ck">&#10003;</span> AI receptionist answers all calls</li>
      <li><span class="ck">&#10003;</span> Hindi + Hinglish conversations</li>
      <li><span class="ck">&#10003;</span> Lead alerts to your email</li>
      <li><span class="ck">&#10003;</span> Full lead &amp; call dashboard</li>
      <li><span class="ck">&#10003;</span> <strong>Unlimited calls</strong></li>
      <li><span class="ck">&#10003;</span> Chat widget for your website</li>
      <li><span class="ck">&#10003;</span> Priority onboarding support</li>
      <li><span class="ck">&#10003;</span> Call recordings &amp; transcripts</li>
      <li class="soon"><span class="dash" style="color:#C4B5FD">&#9670;</span> Outbound follow-up calls <span class="cs-tag">Coming Soon</span></li>
    </ul>
    <a href="/signup?plan=pro" class="btn btn-fill">Start Free Trial &rarr;</a>
  </div>

</div>

<div class="compare-note">
  <p>Not sure? <a href="/signup?plan=pro">Start with Pro free for 14 days</a> &mdash; downgrade anytime, no questions asked.</p>
</div>

<!-- OUTBOUND COMING SOON BANNER -->
<div class="ob-banner">
  <div class="ob-inner">
    <div class="ob-icon">&#128222;</div>
    <div class="ob-body">
      <div class="ob-label">Coming Soon</div>
      <h3>Outbound Follow-Up Calls &mdash; PropBot Calls Your Leads For You</h3>
      <p>Drop in a lead&rsquo;s number and PropBot calls them back automatically &mdash; within 60 seconds of the inquiry, or on a schedule you set. First to follow up wins the deal. <strong style="color:#A5B4FC;">Join the waitlist to get early access.</strong></p>
    </div>
    <div class="ob-cta">
      <button class="ob-btn" onclick="document.getElementById('ob-email-wrap').style.display='block';this.style.display='none';">Get Early Access &rarr;</button>
      <div id="ob-email-wrap" style="display:none;">
        <input id="ob-email" type="email" placeholder="your@email.com" style="width:100%;padding:10px 14px;border-radius:8px;border:none;font-size:14px;margin-bottom:8px;outline:none;font-family:inherit;">
        <button onclick="
          var em=document.getElementById('ob-email').value;
          if(!em||!em.includes('@')){return;}
          fetch('/contact',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:'Outbound Waitlist',phone:'waitlist',email:em,message:'Outbound waitlist signup from pricing page'})});
          document.getElementById('ob-email-wrap').innerHTML='<p style=\'color:#A5B4FC;font-size:14px;font-weight:600;\'>&#10003; You&rsquo;re on the list! We&rsquo;ll email you first.</p>';
        " style="width:100%;padding:10px;background:#7C3AED;color:#fff;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;font-family:inherit;">Notify Me</button>
      </div>
    </div>
  </div>
</div>

<!-- FAQ -->
<div class="faq">
  <h2>Common questions</h2>
  <div class="faq-list">
    <details><summary>Do I need a credit card to start?</summary><div class="fb">No. Sign up, set up your AI receptionist, and use it free for 14 days. We only ask for payment details when your trial ends.</div></details>
    <details><summary>What happens when I reach 50 calls on Starter?</summary><div class="fb">Once you hit 50 calls/month, PropBot will inform callers the line is busy. You&rsquo;ll get a notification to upgrade to Pro for unlimited calls. You won&rsquo;t be charged extra automatically.</div></details>
    <details><summary>Can I switch plans later?</summary><div class="fb">Yes. Upgrade from Starter to Pro at any time from your dashboard. Changes take effect immediately.</div></details>
    <details><summary>What language does the AI speak?</summary><div class="fb">Hindi, Hinglish (mixed Hindi-English), and English. You can also choose a male AI voice if you prefer from male and female AI voices to match your brand.</div></details>
    <details><summary>What is the chat widget?</summary><div class="fb">A small chat button you can embed on your website or property listings. Visitors chat with your AI, and leads are captured just like calls.</div></details>
    <details><summary>Can I cancel anytime?</summary><div class="fb">Yes &mdash; cancel from your dashboard with one click. No lock-in, no cancellation fee, no questions asked.</div></details>
  </div>
</div>

<div class="footer-row">
  <p>&copy; 2026 PropBot &mdash; <a href="/">Home</a> &middot; <a href="/dashboard">Dashboard</a> &middot; <a href="mailto:daanzack8@gmail.com">Contact</a></p>
</div>

</body>
</html>
"""


@router.get("")
@router.get("/")
async def pricing_page():
    return RedirectResponse("/#pricing", status_code=301)
