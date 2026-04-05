from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def root():
    """Landing page — marketing site."""
    return LANDING_HTML


@router.get("/health")
async def health():
    """Health check endpoint. Also used as self-ping target to keep Render alive."""
    return {"status": "ok", "service": "propbot"}


LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PropBot — AI Receptionist for Indian Real Estate Agents</title>
<meta name="description" content="PropBot - AI Receptionist for Indian Real Estate. Answers calls in Hindi & English 24/7, captures leads, books site visits. From ₹2,499/month. 14-day free trial, no credit card.">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #1e293b; }

/* Nav */
.nav { position: sticky; top: 0; z-index: 1000; background: rgba(255,255,255,0.95); backdrop-filter: blur(10px); transition: box-shadow 0.3s; }
.nav.scrolled { box-shadow: 0 1px 12px rgba(0,0,0,0.08); }
.nav-inner { display: flex; justify-content: space-between; align-items: center; padding: 14px 32px; max-width: 1100px; margin: 0 auto; }
.nav-logo { font-size: 22px; font-weight: 800; color: #1e293b; text-decoration: none; }
.nav-logo span { color: #2563eb; }
.nav-links { display: flex; gap: 20px; align-items: center; }
.nav-links a { text-decoration: none; font-size: 14px; font-weight: 500; color: #475569; transition: color 0.2s; }
.nav-links a:hover { color: #2563eb; }
.btn-nav { padding: 9px 22px; background: #2563eb; color: #fff !important; border-radius: 8px; font-weight: 600; }
.btn-nav:hover { background: #1d4ed8; }
.nav-toggle { display: none; background: none; border: none; font-size: 24px; cursor: pointer; color: #1e293b; }

/* Hero */
.hero { text-align: center; padding: 80px 24px 64px; background: linear-gradient(180deg, #f8fafc 0%, #eff6ff 100%); }
.hero-badge { display: inline-block; padding: 6px 18px; background: #dbeafe; color: #1d4ed8; border-radius: 20px; font-size: 13px; font-weight: 600; margin-bottom: 22px; }
.hero h1 { font-size: 46px; line-height: 1.12; max-width: 750px; margin: 0 auto 18px; font-weight: 800; }
.hero h1 em { color: #2563eb; font-style: normal; }
.hero p { font-size: 18px; color: #64748b; max-width: 580px; margin: 0 auto 36px; line-height: 1.65; }
.btn-hero { display: inline-block; padding: 17px 44px; background: #2563eb; color: #fff; text-decoration: none; border-radius: 12px; font-size: 17px; font-weight: 700; box-shadow: 0 4px 20px rgba(37,99,235,0.35); transition: all 0.2s; }
.btn-hero:hover { background: #1d4ed8; transform: translateY(-2px); box-shadow: 0 6px 24px rgba(37,99,235,0.4); }
.hero-sub { margin-top: 14px; font-size: 13px; color: #94a3b8; }
.trust-row { display: flex; justify-content: center; gap: 28px; margin-top: 36px; flex-wrap: wrap; }
.trust-item { display: flex; align-items: center; gap: 6px; font-size: 13px; color: #64748b; font-weight: 500; }
.trust-icon { font-size: 18px; }

/* Pain Point Stats */
.pain { padding: 56px 24px; background: #1e293b; color: #fff; text-align: center; }
.pain h2 { font-size: 28px; margin-bottom: 36px; font-weight: 700; }
.pain-grid { display: flex; justify-content: center; gap: 48px; max-width: 800px; margin: 0 auto; flex-wrap: wrap; }
.pain-stat { text-align: center; }
.pain-num { font-size: 40px; font-weight: 800; color: #f87171; }
.pain-num.zero { color: #fbbf24; }
.pain-label { font-size: 14px; color: #94a3b8; margin-top: 4px; max-width: 200px; }

/* Comparison */
.compare { padding: 80px 24px; max-width: 900px; margin: 0 auto; }
.compare h2 { text-align: center; font-size: 32px; margin-bottom: 8px; }
.compare .sub { text-align: center; color: #64748b; margin-bottom: 40px; font-size: 15px; }
.compare-table { width: 100%; border-collapse: separate; border-spacing: 0; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 8px rgba(0,0,0,0.06); }
.compare-table th, .compare-table td { padding: 14px 18px; font-size: 14px; text-align: left; border-bottom: 1px solid #e2e8f0; }
.compare-table th { background: #f8fafc; font-weight: 600; font-size: 13px; text-transform: uppercase; color: #64748b; letter-spacing: 0.5px; }
.compare-table th:nth-child(2) { background: #fef2f2; color: #991b1b; }
.compare-table th:nth-child(3) { background: #ecfdf5; color: #065f46; }
.compare-table td:first-child { font-weight: 600; color: #334155; background: #f8fafc; }
.compare-table td:nth-child(2) { background: #fffbfb; color: #7f1d1d; }
.compare-table td:nth-child(3) { background: #f0fdf8; color: #14532d; }
.compare-table tr:last-child td { border-bottom: none; }
.compare-callout { margin-top: 28px; background: #ecfdf5; border-left: 4px solid #059669; border-radius: 8px; padding: 18px 24px; text-align: center; }
.compare-callout strong { font-size: 20px; color: #059669; }
.compare-callout p { font-size: 14px; color: #334155; margin-top: 4px; }

/* Features */
.features { padding: 80px 24px; background: #f8fafc; }
.features h2 { text-align: center; font-size: 32px; margin-bottom: 48px; max-width: 800px; margin-left: auto; margin-right: auto; }
.features-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; max-width: 1000px; margin: 0 auto; }
.feature-card { background: #fff; padding: 28px; border-radius: 14px; border: 1px solid #e2e8f0; transition: transform 0.2s, box-shadow 0.2s; }
.feature-card:hover { transform: translateY(-3px); box-shadow: 0 8px 24px rgba(0,0,0,0.06); }
.feature-icon { width: 44px; height: 44px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 22px; margin-bottom: 14px; }
.fi-blue { background: #dbeafe; } .fi-green { background: #d1fae5; } .fi-orange { background: #fef3c7; }
.fi-purple { background: #ede9fe; } .fi-pink { background: #fce7f3; } .fi-teal { background: #ccfbf1; }
.feature-card h3 { font-size: 17px; margin-bottom: 6px; }
.feature-card p { font-size: 14px; color: #64748b; line-height: 1.55; }

/* How */
.how { padding: 80px 24px; }
.how h2 { text-align: center; font-size: 32px; margin-bottom: 8px; }
.how .sub { text-align: center; color: #64748b; margin-bottom: 48px; font-size: 15px; }
.how-steps { display: flex; gap: 40px; max-width: 900px; margin: 0 auto; justify-content: center; flex-wrap: wrap; }
.how-step { flex: 1; min-width: 220px; text-align: center; }
.how-num { width: 52px; height: 52px; border-radius: 50%; background: #2563eb; color: #fff; font-size: 22px; font-weight: 700; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px; }
.how-step h3 { font-size: 17px; margin-bottom: 6px; }
.how-step p { font-size: 14px; color: #64748b; line-height: 1.5; }
.how-cta { text-align: center; margin-top: 44px; }

/* Demo */
.demo { padding: 80px 24px; background: #f8fafc; text-align: center; }
.demo h2 { font-size: 32px; margin-bottom: 8px; }
.demo .sub { color: #64748b; margin-bottom: 36px; font-size: 15px; }
.video-wrap { max-width: 720px; margin: 0 auto; position: relative; border-radius: 14px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.12); }
.video-placeholder { background: #1e293b; padding-bottom: 56.25%; position: relative; }
.video-placeholder .play { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; }
.video-placeholder .play-btn { width: 72px; height: 72px; background: rgba(255,255,255,0.15); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 28px; color: #fff; margin: 0 auto 12px; border: 2px solid rgba(255,255,255,0.3); }
.video-placeholder .play p { color: #94a3b8; font-size: 14px; }

/* Pricing */
.pricing { padding: 80px 24px; text-align: center; }
.pricing h2 { font-size: 32px; margin-bottom: 8px; }
.pricing .sub { color: #64748b; margin-bottom: 40px; font-size: 15px; }
.plans-row { display: flex; gap: 24px; max-width: 820px; margin: 0 auto 36px; justify-content: center; flex-wrap: wrap; }
.price-card { background: #fff; border: 2px solid #e2e8f0; border-radius: 16px; padding: 36px 28px; flex: 1; min-width: 280px; max-width: 370px; text-align: left; position: relative; }
.price-card.popular { border-color: #2563eb; box-shadow: 0 8px 32px rgba(37,99,235,0.12); }
.popular-badge { position: absolute; top: -13px; left: 50%; transform: translateX(-50%); background: #2563eb; color: #fff; padding: 3px 18px; border-radius: 20px; font-size: 11px; font-weight: 700; white-space: nowrap; letter-spacing: 0.5px; }
.plan-name { font-size: 18px; font-weight: 700; margin-bottom: 2px; }
.plan-desc { font-size: 13px; color: #64748b; margin-bottom: 18px; }
.price-amount { font-size: 44px; font-weight: 800; color: #1e293b; line-height: 1; }
.price-amount .currency { font-size: 20px; font-weight: 600; vertical-align: top; margin-top: 8px; display: inline-block; }
.price-amount span { font-size: 16px; color: #64748b; font-weight: 400; }
.price-trial { display: inline-block; margin: 10px 0 20px; padding: 4px 14px; background: #d1fae5; color: #065f46; border-radius: 20px; font-size: 13px; font-weight: 600; }
.price-features { margin-bottom: 24px; }
.price-features li { padding: 6px 0; font-size: 14px; color: #475569; list-style: none; display: flex; align-items: flex-start; gap: 8px; }
.price-features li .check { color: #059669; font-weight: bold; flex-shrink: 0; }
.price-features li.muted { color: #94a3b8; }
.btn-price { display: block; width: 100%; padding: 14px; background: #2563eb; color: #fff; text-decoration: none; border-radius: 10px; font-size: 15px; font-weight: 600; border: none; cursor: pointer; transition: background 0.2s; text-align: center; }
.btn-price:hover { background: #1d4ed8; }
.btn-price-outline { background: #fff; color: #2563eb; border: 2px solid #2563eb; }
.btn-price-outline:hover { background: #eff6ff; }
.pricing-note { font-size: 13px; color: #64748b; margin-bottom: 36px; }
.pricing-note a { color: #2563eb; }
.roi-box { max-width: 540px; margin: 0 auto; background: #ecfdf5; border-left: 4px solid #059669; border-radius: 8px; padding: 24px 28px; text-align: left; }
.roi-box h3 { font-size: 16px; color: #065f46; margin-bottom: 12px; }
.roi-table { width: 100%; font-size: 14px; border-collapse: collapse; margin-bottom: 12px; }
.roi-table td { padding: 6px 0; color: #334155; }
.roi-table td:nth-child(2), .roi-table td:nth-child(3) { text-align: right; }
.roi-table .save td { font-weight: 700; color: #059669; font-size: 16px; border-top: 2px solid #a7f3d0; padding-top: 10px; }
.roi-note { font-size: 13px; color: #475569; line-height: 1.5; font-style: italic; }

/* FAQ */
.faq { padding: 80px 24px; background: #f8fafc; }
.faq h2 { text-align: center; font-size: 32px; margin-bottom: 40px; }
.faq-list { max-width: 700px; margin: 0 auto; }
.faq-list details { border-bottom: 1px solid #e2e8f0; }
.faq-list summary { padding: 18px 0; font-size: 15px; font-weight: 600; color: #1e293b; cursor: pointer; list-style: none; display: flex; justify-content: space-between; align-items: center; }
.faq-list summary::after { content: "+"; font-size: 20px; color: #94a3b8; font-weight: 400; transition: transform 0.2s; }
.faq-list details[open] summary::after { content: "\\2212"; }
.faq-list summary::-webkit-details-marker { display: none; }
.faq-list .faq-body { padding: 0 0 18px; font-size: 14px; color: #64748b; line-height: 1.65; }

/* Final CTA */
.final-cta { padding: 80px 24px; background: linear-gradient(135deg, #2563eb, #1d4ed8); text-align: center; }
.final-cta h2 { color: #fff; font-size: 32px; max-width: 600px; margin: 0 auto 14px; line-height: 1.2; }
.final-cta p { color: #bfdbfe; font-size: 16px; max-width: 520px; margin: 0 auto 32px; line-height: 1.6; }
.btn-final { display: inline-block; padding: 16px 44px; background: #fff; color: #2563eb; text-decoration: none; border-radius: 12px; font-size: 17px; font-weight: 700; transition: all 0.2s; }
.btn-final:hover { background: #f0f0f0; transform: translateY(-1px); }
.final-sub { margin-top: 14px; }
.final-sub a { color: #bfdbfe; font-size: 14px; text-decoration: underline; }

/* Footer */
.footer { background: #1e293b; padding: 48px 24px 32px; color: #94a3b8; }
.footer-inner { max-width: 1000px; margin: 0 auto; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 32px; }
.footer-col h4 { color: #fff; font-size: 14px; margin-bottom: 12px; }
.footer-col a { display: block; color: #94a3b8; text-decoration: none; font-size: 13px; padding: 3px 0; }
.footer-col a:hover { color: #fff; }
.footer-bottom { max-width: 1000px; margin: 28px auto 0; padding-top: 20px; border-top: 1px solid #334155; text-align: center; font-size: 12px; color: #64748b; }

/* Responsive */
@media (max-width: 768px) {
    .nav-links { display: none; position: absolute; top: 100%; left: 0; right: 0; background: #fff; flex-direction: column; padding: 16px 24px; gap: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
    .nav-links.open { display: flex; }
    .nav-toggle { display: block; }
    .hero h1 { font-size: 30px; }
    .hero p { font-size: 16px; }
    .hero { padding: 56px 20px 48px; }
    .pain-grid { gap: 28px; }
    .pain-num { font-size: 32px; }
    .compare-table { font-size: 12px; }
    .compare-table th, .compare-table td { padding: 10px 10px; }
    .features-grid { grid-template-columns: 1fr 1fr; }
    .how-steps { flex-direction: column; align-items: center; }
    .footer-inner { flex-direction: column; gap: 24px; }
}
@media (max-width: 480px) {
    .features-grid { grid-template-columns: 1fr; }
    .trust-row { flex-direction: column; gap: 10px; }
    .compare-table th:first-child, .compare-table td:first-child { min-width: 90px; }
}
</style>
</head>
<body>

<!-- Nav -->
<nav class="nav" id="nav">
<div class="nav-inner">
    <a class="nav-logo" href="/"><span>Prop</span>Bot</a>
    <button class="nav-toggle" onclick="document.querySelector('.nav-links').classList.toggle('open')">&#9776;</button>
    <div class="nav-links">
        <a href="#features">Features</a>
        <a href="#pricing">Pricing</a>
        <a href="#demo">Demo</a>
        <a href="#how">How It Works</a>
        <a href="/dashboard">Login</a>
        <a href="/signup" class="btn-nav">Start Free Trial</a>
    </div>
</div>
</nav>

<!-- Hero -->
<section class="hero">
    <div class="hero-badge">AI Receptionist for Indian Real Estate</div>
    <h1>Stop Losing Leads to Missed Calls. <em>Your AI Receptionist Is Ready.</em></h1>
    <p>PropBot answers every call in Hindi, English, and Hinglish &mdash; 24/7. It qualifies buyers, books site visits, and sends you instant alerts. No more missed deals. No more &#8377;20,000/month receptionist salary.</p>
    <a href="/signup" class="btn-hero">Start 14-Day Free Trial</a>
    <div class="hero-sub">No credit card required. Live in under 5 minutes.</div>
    <div class="trust-row">
        <div class="trust-item"><span class="trust-icon">&#128338;</span> 24/7 Availability</div>
        <div class="trust-item"><span class="trust-icon">&#127470;&#127475;</span> Hindi + English</div>
        <div class="trust-item"><span class="trust-icon">&#9889;</span> Setup in 5 Minutes</div>
    </div>
</section>

<!-- Pain Point Stats -->
<section class="pain">
    <h2>Aapka Receptionist Kitna Cost Kar Raha Hai?</h2>
    <div class="pain-grid">
        <div class="pain-stat">
            <div class="pain-num">&#8377;15-25K</div>
            <div class="pain-label">Monthly salary for a human receptionist</div>
        </div>
        <div class="pain-stat">
            <div class="pain-num">40%</div>
            <div class="pain-label">Calls missed after hours and on holidays</div>
        </div>
        <div class="pain-stat">
            <div class="pain-num zero">0</div>
            <div class="pain-label">Leads captured at 2 AM by a human</div>
        </div>
    </div>
</section>

<!-- AI vs Human Comparison -->
<section class="compare" id="compare">
    <h2>Why Smart Agents Are Switching to AI</h2>
    <p class="sub">See the real difference. No sugarcoating.</p>
    <table class="compare-table">
        <thead><tr><th></th><th>Human Receptionist</th><th>PropBot AI</th></tr></thead>
        <tbody>
            <tr><td>Monthly Cost</td><td>&#8377;15,000 &ndash; &#8377;25,000</td><td>&#8377;2,499 &ndash; &#8377;4,999</td></tr>
            <tr><td>Availability</td><td>9 AM &ndash; 6 PM, Mon-Sat</td><td>24/7/365. Never sick.</td></tr>
            <tr><td>Languages</td><td>1-2 languages</td><td>Hindi, English, Hinglish</td></tr>
            <tr><td>Response Time</td><td>Depends on mood</td><td>Instant. Every time.</td></tr>
            <tr><td>Lead Capture</td><td>Pen &amp; paper / WhatsApp</td><td>Auto-captured + email alert</td></tr>
            <tr><td>Call Recording</td><td>Not possible</td><td>Every call recorded + transcribed</td></tr>
            <tr><td>Site Visit Booking</td><td>Manual back-and-forth</td><td>Books into Google Calendar</td></tr>
            <tr><td>Scalability</td><td>1 call at a time</td><td>Unlimited simultaneous calls</td></tr>
            <tr><td>Training</td><td>2-4 weeks</td><td>5 minutes. Done.</td></tr>
            <tr><td>Leaves &amp; Holidays</td><td>15-20 days/year absent</td><td>Zero downtime. Ever.</td></tr>
        </tbody>
    </table>
    <div class="compare-callout">
        <strong>Save &#8377;1,20,000 &ndash; &#8377;2,40,000 per year</strong>
        <p>Aur koi chutti bhi nahi mangega.</p>
    </div>
</section>

<!-- Features -->
<section class="features" id="features">
    <h2>Everything Your Business Needs to Never Miss a Lead</h2>
    <div class="features-grid">
        <div class="feature-card">
            <div class="feature-icon fi-blue">&#128222;</div>
            <h3>AI Voice Calls</h3>
            <p>Answers every call in natural Hindi and English. Your callers won't know it's AI &mdash; sounds like a real team member.</p>
        </div>
        <div class="feature-card">
            <div class="feature-icon fi-green">&#128172;</div>
            <h3>Website Chat Widget</h3>
            <p>Embed on your property website. Visitors get instant answers about your listings 24/7. Captures phone numbers automatically.</p>
        </div>
        <div class="feature-card">
            <div class="feature-icon fi-orange">&#128203;</div>
            <h3>Auto Lead Capture</h3>
            <p>Name, phone, budget, area preference &mdash; everything captured instantly. Get email alerts the moment a new lead comes in.</p>
        </div>
        <div class="feature-card">
            <div class="feature-icon fi-purple">&#128197;</div>
            <h3>Google Calendar Booking</h3>
            <p>Your AI books site visits directly into your Google Calendar. Confirms with the caller on the spot. No back-and-forth.</p>
        </div>
        <div class="feature-card">
            <div class="feature-icon fi-pink">&#128200;</div>
            <h3>Dashboard &amp; Analytics</h3>
            <p>All leads, call recordings, transcripts in one place. Know exactly what every caller asked and what they want.</p>
        </div>
        <div class="feature-card">
            <div class="feature-icon fi-teal">&#9889;</div>
            <h3>Instant Alerts</h3>
            <p>Get notified on email the moment a qualified lead comes in. Never let a hot buyer wait.</p>
        </div>
    </div>
</section>

<!-- How It Works -->
<section class="how" id="how">
    <h2>Live in 5 Minutes. Seriously.</h2>
    <p class="sub">No technical skills needed. No waiting for "onboarding calls."</p>
    <div class="how-steps">
        <div class="how-step">
            <div class="how-num">1</div>
            <h3>Sign Up &amp; Add Details</h3>
            <p>Enter your business name, phone, email. Choose your AI assistant's voice &mdash; 6 natural Indian voices.</p>
        </div>
        <div class="how-step">
            <div class="how-num">2</div>
            <h3>Add Your Listings</h3>
            <p>Paste your property details. Your AI learns everything about your inventory instantly.</p>
        </div>
        <div class="how-step">
            <div class="how-num">3</div>
            <h3>Go Live</h3>
            <p>Get your dedicated phone number and chat widget code. Start receiving AI-handled calls immediately.</p>
        </div>
    </div>
    <div class="how-cta">
        <a href="/signup" class="btn-hero">Start Your Free Trial Now</a>
    </div>
</section>

<!-- Demo Video -->
<section class="demo" id="demo">
    <h2>See PropBot in Action</h2>
    <p class="sub">Watch a real conversation between a buyer and PropBot. Hindi mein. Bilkul natural.</p>
    <div class="video-wrap">
        <div class="video-placeholder">
            <div class="play">
                <div class="play-btn">&#9654;</div>
                <p>Demo video coming soon</p>
            </div>
        </div>
    </div>
</section>

<!-- Pricing -->
<section class="pricing" id="pricing">
    <h2>Simple, Honest Pricing</h2>
    <p class="sub">14-day free trial on both plans &mdash; no credit card needed.</p>
    <div class="plans-row">
        <!-- Starter -->
        <div class="price-card">
            <div class="plan-name">Starter</div>
            <div class="plan-desc">For solo brokers starting with AI</div>
            <div class="price-amount"><span class="currency">&#8377;</span>2,499<span> /month</span></div>
            <div class="price-trial">14-day free trial</div>
            <ul class="price-features">
                <li><span class="check">&#10003;</span> AI voice receptionist (Priya)</li>
                <li><span class="check">&#10003;</span> Hindi + Hinglish conversations</li>
                <li><span class="check">&#10003;</span> Lead alerts to your WhatsApp</li>
                <li><span class="check">&#10003;</span> Lead dashboard</li>
                <li><span class="check">&#10003;</span> Up to 50 calls / month</li>
                <li class="muted"><span>&#8212;</span> Chat widget for website</li>
                <li class="muted"><span>&#8212;</span> Priority support</li>
            </ul>
            <a href="/signup?plan=starter" class="btn-price btn-price-outline">Start Free Trial</a>
        </div>
        <!-- Pro -->
        <div class="price-card popular">
            <div class="popular-badge">MOST POPULAR</div>
            <div class="plan-name">Pro</div>
            <div class="plan-desc">For serious brokers who can&rsquo;t miss a lead</div>
            <div class="price-amount"><span class="currency">&#8377;</span>4,999<span> /month</span></div>
            <div class="price-trial">14-day free trial</div>
            <ul class="price-features">
                <li><span class="check">&#10003;</span> AI voice receptionist (Priya)</li>
                <li><span class="check">&#10003;</span> Hindi + Hinglish conversations</li>
                <li><span class="check">&#10003;</span> Lead alerts to your WhatsApp</li>
                <li><span class="check">&#10003;</span> Lead dashboard</li>
                <li><span class="check">&#10003;</span> <strong>Unlimited calls</strong></li>
                <li><span class="check">&#10003;</span> Chat widget for website</li>
                <li><span class="check">&#10003;</span> Priority onboarding support</li>
            </ul>
            <a href="/signup?plan=pro" class="btn-price">Start Free Trial</a>
        </div>
    </div>
    <p class="pricing-note">Not sure which plan? <a href="/pricing">See full comparison</a> &mdash; or start with Pro free for 14 days and decide later.</p>
    <div class="roi-box">
        <h3>Your ROI Math (Pro plan)</h3>
        <table class="roi-table">
            <tr><td></td><td><strong>Human Receptionist</strong></td><td><strong>PropBot Pro</strong></td></tr>
            <tr><td>Monthly cost</td><td>&#8377;20,000</td><td>&#8377;4,999</td></tr>
            <tr><td>Annual cost</td><td>&#8377;2,40,000</td><td>&#8377;59,988</td></tr>
            <tr class="save"><td>You save</td><td></td><td>&#8377;1,80,000/year</td></tr>
        </table>
        <p class="roi-note">Plus: no leaves, no late arrivals, no training. One deal from a 2 AM missed call pays for PropBot Pro for 3 months.</p>
    </div>
</section>

<!-- FAQ -->
<section class="faq" id="faq">
    <h2>Common Questions</h2>
    <div class="faq-list">
        <details><summary>Will my callers know they're talking to AI?</summary><div class="faq-body">PropBot uses natural Indian voices that sound remarkably human. Most callers don't realize it's AI. You can choose from 6 different voices &mdash; male and female &mdash; with natural Hindi/English accents.</div></details>
        <details><summary>Does it work in Hindi?</summary><div class="faq-body">Yes! PropBot speaks fluent Hindi, English, and Hinglish. It understands mixed-language queries naturally &mdash; just like how real conversations happen in India.</div></details>
        <details><summary>What if the caller wants to talk to me directly?</summary><div class="faq-body">PropBot captures their details and sends you an instant email alert. You can also set up callback requests through the chat widget. You're always in control.</div></details>
        <details><summary>How long does setup take?</summary><div class="faq-body">Under 5 minutes. Sign up, add your property details, choose a voice &mdash; and your AI receptionist is live. No technical skills needed.</div></details>
        <details><summary>What happens after the 14-day trial?</summary><div class="faq-body">Your subscription continues at &#8377;2,499/month (Starter) or &#8377;4,999/month (Pro) via Razorpay. Cancel anytime from the dashboard &mdash; no lock-in, no cancellation fees.</div></details>
        <details><summary>Can I use it with my existing phone number?</summary><div class="faq-body">PropBot provides you a dedicated phone number. You can forward calls to it from your existing number, or share the PropBot number directly with clients.</div></details>
        <details><summary>Is my data safe?</summary><div class="faq-body">All data is stored securely. Call recordings, transcripts, and lead information are only accessible through your password-protected dashboard.</div></details>
        <details><summary>What if I need to change my property listings?</summary><div class="faq-body">Update anytime from your dashboard. Your AI assistant learns the changes instantly &mdash; no waiting, no retraining.</div></details>
    </div>
</section>

<!-- Final CTA -->
<section class="final-cta">
    <h2>Your Competitors Are Already Going AI. Don't Get Left Behind.</h2>
    <p>Every missed call is a missed deal. Every missed deal is lakhs lost. Start your free trial today and let PropBot handle your calls while you close deals.</p>
    <a href="/signup?plan=pro" class="btn-final">Start My Free Trial</a>
    <div class="final-sub"><a href="/dashboard">or Login to Dashboard</a></div>
</section>

<!-- Footer -->
<footer class="footer">
<div class="footer-inner">
    <div class="footer-col">
        <h4>PropBot</h4>
        <a href="#features">Features</a>
        <a href="#pricing">Pricing</a>
        <a href="#demo">Demo</a>
        <a href="#how">How It Works</a>
    </div>
    <div class="footer-col">
        <h4>Get Started</h4>
        <a href="/signup">Start Free Trial</a>
        <a href="/dashboard">Login to Dashboard</a>
        <a href="#faq">FAQ</a>
    </div>
    <div class="footer-col">
        <h4>Made with &#10084;&#65039; in India</h4>
        <a href="mailto:daanzack8@gmail.com">Contact Us</a>
    </div>
</div>
<div class="footer-bottom">&copy; 2026 PropBot. AI Receptionist for Indian Real Estate Agents.</div>
</footer>

<script>
window.addEventListener('scroll',function(){document.getElementById('nav').classList.toggle('scrolled',window.scrollY>10)});
</script>
</body>
</html>
"""
