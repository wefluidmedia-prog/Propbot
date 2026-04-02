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
<title>PropBot — AI Receptionist for Real Estate</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #1e293b; }

/* Nav */
.nav { display: flex; justify-content: space-between; align-items: center; padding: 16px 32px; max-width: 1100px; margin: 0 auto; }
.nav-logo { font-size: 22px; font-weight: 800; color: #1e293b; text-decoration: none; }
.nav-logo span { color: #2563eb; }
.nav-links { display: flex; gap: 16px; align-items: center; }
.nav-links a { text-decoration: none; font-size: 14px; font-weight: 500; color: #475569; }
.nav-links a:hover { color: #2563eb; }
.btn-nav { padding: 8px 20px; background: #2563eb; color: #fff !important; border-radius: 8px; font-weight: 600; }
.btn-nav:hover { background: #1d4ed8; }

/* Hero */
.hero { text-align: center; padding: 80px 24px 60px; background: linear-gradient(180deg, #f8fafc 0%, #eff6ff 100%); }
.hero-badge { display: inline-block; padding: 6px 16px; background: #dbeafe; color: #1d4ed8; border-radius: 20px; font-size: 13px; font-weight: 600; margin-bottom: 20px; }
.hero h1 { font-size: 44px; line-height: 1.15; max-width: 700px; margin: 0 auto 16px; }
.hero h1 span { color: #2563eb; }
.hero p { font-size: 18px; color: #64748b; max-width: 560px; margin: 0 auto 32px; line-height: 1.6; }
.btn-hero { display: inline-block; padding: 16px 40px; background: #2563eb; color: #fff; text-decoration: none; border-radius: 12px; font-size: 17px; font-weight: 700; box-shadow: 0 4px 14px rgba(37,99,235,0.3); }
.btn-hero:hover { background: #1d4ed8; transform: translateY(-1px); }
.hero-sub { margin-top: 14px; font-size: 13px; color: #94a3b8; }

/* Features */
.features { padding: 80px 24px; max-width: 1000px; margin: 0 auto; }
.features h2 { text-align: center; font-size: 32px; margin-bottom: 48px; }
.features-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px; }
.feature-card { background: #fff; padding: 28px; border-radius: 14px; border: 1px solid #e2e8f0; }
.feature-icon { width: 44px; height: 44px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 22px; margin-bottom: 14px; }
.fi-blue { background: #dbeafe; }
.fi-green { background: #d1fae5; }
.fi-orange { background: #fef3c7; }
.fi-purple { background: #ede9fe; }
.fi-pink { background: #fce7f3; }
.fi-teal { background: #ccfbf1; }
.feature-card h3 { font-size: 17px; margin-bottom: 6px; }
.feature-card p { font-size: 14px; color: #64748b; line-height: 1.5; }

/* How it works */
.how { padding: 80px 24px; background: #f8fafc; }
.how h2 { text-align: center; font-size: 32px; margin-bottom: 48px; }
.how-steps { display: flex; gap: 32px; max-width: 900px; margin: 0 auto; flex-wrap: wrap; justify-content: center; }
.how-step { flex: 1; min-width: 220px; text-align: center; }
.how-num { width: 48px; height: 48px; border-radius: 50%; background: #2563eb; color: #fff; font-size: 20px; font-weight: 700; display: flex; align-items: center; justify-content: center; margin: 0 auto 14px; }
.how-step h3 { font-size: 16px; margin-bottom: 6px; }
.how-step p { font-size: 13px; color: #64748b; }

/* Pricing */
.pricing { padding: 80px 24px; max-width: 500px; margin: 0 auto; text-align: center; }
.pricing h2 { font-size: 32px; margin-bottom: 12px; }
.pricing .sub { color: #64748b; margin-bottom: 32px; font-size: 15px; }
.price-card { background: #fff; border: 2px solid #2563eb; border-radius: 16px; padding: 36px; }
.price-amount { font-size: 48px; font-weight: 800; color: #1e293b; }
.price-amount span { font-size: 18px; color: #64748b; font-weight: 400; }
.price-trial { display: inline-block; margin: 12px 0 20px; padding: 6px 16px; background: #d1fae5; color: #065f46; border-radius: 20px; font-size: 14px; font-weight: 600; }
.price-features { text-align: left; margin-bottom: 24px; }
.price-features li { padding: 6px 0; font-size: 14px; color: #475569; list-style: none; }
.price-features li::before { content: "\\2713"; color: #059669; font-weight: bold; margin-right: 8px; }
.btn-price { display: block; width: 100%; padding: 14px; background: #2563eb; color: #fff; text-decoration: none; border-radius: 10px; font-size: 16px; font-weight: 600; border: none; cursor: pointer; }
.btn-price:hover { background: #1d4ed8; }

/* Footer */
.footer { text-align: center; padding: 32px; color: #94a3b8; font-size: 13px; border-top: 1px solid #e2e8f0; }

@media (max-width: 768px) {
    .hero h1 { font-size: 30px; }
    .hero p { font-size: 16px; }
    .nav { padding: 12px 16px; }
    .how-steps { flex-direction: column; align-items: center; }
}
</style>
</head>
<body>

<nav class="nav">
    <a class="nav-logo" href="/"><span>Prop</span>Bot</a>
    <div class="nav-links">
        <a href="#features">Features</a>
        <a href="#pricing">Pricing</a>
        <a href="/dashboard">Login</a>
        <a href="/signup" class="btn-nav">Start Free Trial</a>
    </div>
</nav>

<section class="hero">
    <div class="hero-badge">AI-Powered Real Estate Receptionist</div>
    <h1>Replace your receptionist with <span>AI that never sleeps</span></h1>
    <p>PropBot answers calls, qualifies leads, and books site visits for your real estate business — 24/7, in Hindi and English. No missed calls, no missed deals.</p>
    <a href="/signup" class="btn-hero">Start 14-Day Free Trial</a>
    <div class="hero-sub">No credit card required. Set up in under 5 minutes.</div>
</section>

<section class="features" id="features">
    <h2>Everything your receptionist does, but better</h2>
    <div class="features-grid">
        <div class="feature-card">
            <div class="feature-icon fi-blue">&#128222;</div>
            <h3>AI Voice Calls</h3>
            <p>Answers every call in natural Hindi/English. Sounds like a real team member, not a robot.</p>
        </div>
        <div class="feature-card">
            <div class="feature-icon fi-green">&#128172;</div>
            <h3>Website Chat Widget</h3>
            <p>Embed on your website. Visitors get instant answers about your properties 24/7.</p>
        </div>
        <div class="feature-card">
            <div class="feature-icon fi-orange">&#128203;</div>
            <h3>Auto Lead Capture</h3>
            <p>Collects name, phone, budget, area preference. Sends you instant email + SMS alerts.</p>
        </div>
        <div class="feature-card">
            <div class="feature-icon fi-purple">&#128200;</div>
            <h3>Dashboard</h3>
            <p>See all your leads, call recordings, transcripts, and analytics in one place.</p>
        </div>
        <div class="feature-card">
            <div class="feature-icon fi-pink">&#127908;</div>
            <h3>Choose Your Voice</h3>
            <p>Male or female, pick from 6 natural Indian voices. Rename your assistant to match your brand.</p>
        </div>
        <div class="feature-card">
            <div class="feature-icon fi-teal">&#9889;</div>
            <h3>5-Minute Setup</h3>
            <p>Sign up, add your listings, choose a voice — done. Your AI receptionist is live.</p>
        </div>
    </div>
</section>

<section class="how" id="how">
    <h2>How it works</h2>
    <div class="how-steps">
        <div class="how-step">
            <div class="how-num">1</div>
            <h3>Sign Up</h3>
            <p>Enter your business details and choose your AI assistant's voice.</p>
        </div>
        <div class="how-step">
            <div class="how-num">2</div>
            <h3>Add Listings</h3>
            <p>Paste your property details. Your AI learns everything instantly.</p>
        </div>
        <div class="how-step">
            <div class="how-num">3</div>
            <h3>Go Live</h3>
            <p>Get your phone number and widget code. Start receiving AI-handled calls.</p>
        </div>
    </div>
</section>

<section class="pricing" id="pricing">
    <h2>Simple pricing</h2>
    <p class="sub">One plan. Everything included. No hidden fees.</p>
    <div class="price-card">
        <div class="price-amount">&#8377;5,000 <span>/month</span></div>
        <div class="price-trial">14-day free trial</div>
        <ul class="price-features">
            <li>Unlimited AI voice calls</li>
            <li>Website chat widget</li>
            <li>Auto lead capture + alerts</li>
            <li>Dashboard with recordings</li>
            <li>Hindi + English support</li>
            <li>Email + SMS notifications</li>
            <li>Choose male or female voice</li>
        </ul>
        <a href="/signup" class="btn-price">Start Free Trial</a>
    </div>
</section>

<footer class="footer">
    &copy; 2026 PropBot. AI Receptionist for Indian Real Estate.
</footer>

</body>
</html>
"""
