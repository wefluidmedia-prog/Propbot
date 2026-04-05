from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.config import settings

router = APIRouter()


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


def _og_tags() -> str:
    """Return Open Graph + canonical meta tags."""
    url = settings.BASE_URL
    return (
        f'<link rel="canonical" href="{url}/">\n'
        f'<meta property="og:title" content="PropBot - AI Receptionist for Indian Real Estate Agents">\n'
        f'<meta property="og:description" content="Answer every call 24/7 in Hindi & English. From ₹2,499/month.">\n'
        f'<meta property="og:type" content="website">\n'
        f'<meta property="og:url" content="{url}/">\n'
        f'<meta name="twitter:card" content="summary">\n'
        f'<meta name="twitter:title" content="PropBot - AI Receptionist for Indian Real Estate">\n'
        f'<meta name="twitter:description" content="Answer every call 24/7 in Hindi & English. From ₹2,499/month.">\n'
    )


@router.get("/", response_class=HTMLResponse)
async def root():
    """Landing page — marketing site."""
    html = LANDING_HTML.replace("<!-- __GA__ -->", _ga_snippet())
    html = html.replace("<!-- __OG__ -->", _og_tags())

    # WhatsApp floating button + footer link (only if configured)
    wa = settings.WHATSAPP_NUMBER
    if wa:
        wa_url = f"https://wa.me/91{wa}?text=Hi%20I%27m%20interested%20in%20PropBot"
        wa_float = (
            f'<a class="wa-float" href="{wa_url}" target="_blank" rel="noopener">'
            '<svg viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12 0C5.373 0 0 5.373 0 12c0 2.625.846 5.059 2.284 7.034L.789 23.492a.5.5 0 00.611.611l4.458-1.495A11.952 11.952 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 22c-2.317 0-4.46-.768-6.183-2.064l-.432-.334-3.156 1.058 1.058-3.156-.334-.432A9.955 9.955 0 012 12C2 6.486 6.486 2 12 2s10 4.486 10 10-4.486 10-10 10z"/></svg>'
            '</a>'
        )
        wa_footer = f'<a href="{wa_url}" target="_blank" rel="noopener">WhatsApp us</a>'
    else:
        wa_float = ""
        wa_footer = ""

    html = html.replace("<!-- __WHATSAPP_FLOAT__ -->", wa_float)
    html = html.replace("<!-- __WHATSAPP_FOOTER__ -->", wa_footer)
    return html


@router.get("/health")
async def health():
    """Health check endpoint. Also used as self-ping target to keep Render alive."""
    return {"status": "ok", "service": "propbot"}


@router.post("/contact")
async def contact_form(request):
    """Receive contact form submission and email it to the founder."""
    import asyncio
    body = await request.json()
    name = body.get("name", "").strip()
    phone = body.get("phone", "").strip()
    email = body.get("email", "").strip()
    message = body.get("message", "").strip()

    if not name or not phone or not message:
        return {"status": "error", "message": "Please fill all required fields."}

    if settings.SMTP_EMAIL:
        from app.services.alert_service import _send_email
        try:
            await asyncio.to_thread(
                _send_email,
                to=settings.SMTP_EMAIL,
                subject=f"PropBot Inquiry from {name}",
                body=(
                    f"<h3>New inquiry from PropBot website</h3>"
                    f"<p><strong>Name:</strong> {name}</p>"
                    f"<p><strong>Phone:</strong> {phone}</p>"
                    f"<p><strong>Email:</strong> {email or 'not provided'}</p>"
                    f"<p><strong>Message:</strong><br>{message}</p>"
                ),
            )
        except Exception:
            pass  # Best-effort — don't fail the response

    return {"status": "ok"}


LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PropBot — AI Receptionist for Indian Real Estate Agents</title>
<meta name="description" content="PropBot answers every call in Hindi & English 24/7, captures leads, books site visits. From ₹2,499/month. 14-day free trial, no credit card.">
<!-- __GA__ -->
<!-- __OG__ -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
:root {
  --orange: #FF5722;
  --orange-dark: #E64A19;
  --orange-glow: rgba(255,87,34,0.12);
  --dark: #0D1117;
  --dark-card: #161B22;
  --text: #111827;
  --muted: #6B7280;
  --light: #9CA3AF;
  --bg: #FAFAF8;
  --bg2: #F3F4F6;
  --white: #FFFFFF;
  --border: #E5E7EB;
  --green: #10B981;
  --green-bg: #ECFDF5;
  --green-text: #065F46;
  --r: 16px;
  --r-lg: 24px;
  --sh: 0 4px 16px rgba(0,0,0,0.08),0 2px 4px rgba(0,0,0,0.04);
  --sh-lg: 0 20px 48px rgba(0,0,0,0.10),0 4px 8px rgba(0,0,0,0.04);
}
*{margin:0;padding:0;box-sizing:border-box;}
html{scroll-behavior:smooth;}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;color:var(--text);background:var(--bg);-webkit-font-smoothing:antialiased;}

/* NAV */
.nav{position:sticky;top:0;z-index:1000;background:rgba(250,250,248,0.88);backdrop-filter:blur(16px);border-bottom:1px solid transparent;transition:border-color .3s;}
.nav.scrolled{border-color:var(--border);}
.nav-inner{display:flex;justify-content:space-between;align-items:center;padding:14px 40px;max-width:1160px;margin:0 auto;}
.nav-logo{font-size:21px;font-weight:800;color:var(--text);text-decoration:none;letter-spacing:-0.5px;}
.nav-logo span{color:var(--orange);}
.nav-links{display:flex;gap:4px;align-items:center;}
.nav-links a{text-decoration:none;font-size:14px;font-weight:500;color:var(--muted);padding:7px 12px;border-radius:10px;transition:all .15s;}
.nav-links a:hover{color:var(--text);background:rgba(0,0,0,0.04);}
.btn-nav{background:var(--orange)!important;color:#fff!important;padding:9px 20px!important;border-radius:10px!important;font-weight:700!important;}
.btn-nav:hover{background:var(--orange-dark)!important;box-shadow:0 4px 12px rgba(255,87,34,.3)!important;}
.nav-toggle{display:none;background:none;border:none;cursor:pointer;padding:4px;flex-direction:column;gap:5px;}
.nav-toggle span{display:block;width:22px;height:2px;background:var(--text);border-radius:2px;transition:all .25s;}

/* HERO */
.hero{padding:72px 40px 80px;background:linear-gradient(150deg,#FFFAF7 0%,#FFF5EF 45%,#F0F4FF 100%);overflow:hidden;}
.hero-inner{max-width:1160px;margin:0 auto;display:grid;grid-template-columns:1fr 1fr;gap:64px;align-items:center;}
.hero-badge{display:inline-flex;align-items:center;gap:7px;padding:6px 14px;background:var(--orange-glow);border:1px solid rgba(255,87,34,.22);color:var(--orange);border-radius:20px;font-size:12px;font-weight:700;margin-bottom:22px;letter-spacing:.3px;}
.hero-badge .pulse{width:7px;height:7px;background:var(--orange);border-radius:50%;animation:blink 2s infinite;}
@keyframes blink{0%,100%{opacity:1;}50%{opacity:.3;}}
.hero h1{font-size:52px;line-height:1.07;font-weight:900;letter-spacing:-2.5px;margin-bottom:20px;}
.hero h1 .hl{color:var(--orange);}
.hero p{font-size:17px;color:var(--muted);line-height:1.72;margin-bottom:36px;max-width:460px;}
.btn-hero{display:inline-flex;align-items:center;gap:8px;padding:16px 36px;background:var(--orange);color:#fff;text-decoration:none;border-radius:var(--r);font-size:16px;font-weight:700;box-shadow:0 8px 24px rgba(255,87,34,.3);transition:all .2s;width:fit-content;}
.btn-hero:hover{background:var(--orange-dark);transform:translateY(-2px);box-shadow:0 12px 32px rgba(255,87,34,.4);}
.hero-fine{margin-top:14px;font-size:13px;color:var(--light);display:flex;flex-wrap:wrap;gap:16px;}
.hero-fine span{display:flex;align-items:center;gap:5px;}

/* HERO VISUAL */
.hero-visual{position:relative;}
.mock-card{background:#fff;border-radius:var(--r-lg);box-shadow:var(--sh-lg);border:1px solid var(--border);overflow:hidden;}
.mock-header{background:var(--dark);padding:13px 18px;display:flex;align-items:center;gap:10px;}
.dots span{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;}
.d-r{background:#FF5F57;}.d-y{background:#FEBC2E;}.d-g{background:#28C840;}
.mock-title{color:#8B949E;font-size:12px;font-weight:500;margin-left:4px;}
.mock-live{margin-left:auto;font-size:11px;color:var(--green);font-weight:600;display:flex;align-items:center;gap:4px;}
.mock-live::before{content:"●";font-size:8px;animation:blink 1.5s infinite;}
.mock-body{padding:16px;}
.notif-strip{display:flex;gap:10px;align-items:flex-start;background:linear-gradient(135deg,#ECFDF5,#F0FFF4);border:1px solid #A7F3D0;border-radius:10px;padding:12px 14px;margin-bottom:14px;}
.notif-strip .ni{font-size:18px;}
.notif-strip .nt{font-size:12px;font-weight:700;color:var(--green-text);}
.notif-strip .nd{font-size:11px;color:#374151;margin-top:2px;line-height:1.5;}
.chat-win{border:1px solid var(--border);border-radius:10px;overflow:hidden;background:#F9FAFB;}
.chat-top{background:#fff;padding:10px 14px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:8px;}
.chat-av{width:28px;height:28px;background:var(--orange-glow);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;}
.chat-inf .cn{font-size:12px;font-weight:600;color:var(--text);}
.chat-inf .cp{font-size:10px;color:var(--light);}
.chat-status-badge{margin-left:auto;font-size:10px;color:var(--green);font-weight:600;background:var(--green-bg);padding:2px 8px;border-radius:10px;}
.msgs{padding:12px;display:flex;flex-direction:column;gap:8px;}
.mb{max-width:86%;}.mb-bot{align-self:flex-start;}.mb-usr{align-self:flex-end;}
.mn{font-size:10px;color:var(--light);font-weight:600;margin-bottom:3px;}
.mb-usr .mn{text-align:right;}
.bub{padding:8px 12px;border-radius:12px;font-size:12px;line-height:1.5;}
.bub-bot{background:#fff;border:1px solid var(--border);color:var(--text);border-bottom-left-radius:3px;}
.bub-usr{background:var(--orange);color:#fff;border-bottom-right-radius:3px;}
.chat-foot{background:#fff;padding:9px 14px;border-top:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;}
.cf-ok{font-size:10px;color:var(--green);font-weight:600;}
.cf-time{font-size:10px;color:var(--light);}
.float-b{position:absolute;background:#fff;border-radius:10px;box-shadow:var(--sh);padding:8px 12px;display:flex;align-items:center;gap:7px;font-size:12px;font-weight:600;color:var(--text);border:1px solid var(--border);white-space:nowrap;}
.fb1{top:-16px;right:-12px;animation:fl 3s ease-in-out infinite;}
.fb2{bottom:-14px;left:-14px;animation:fl 3s ease-in-out infinite 1.5s;}
@keyframes fl{0%,100%{transform:translateY(0);}50%{transform:translateY(-5px);}}

/* TRUST BAR */
.trust-bar{background:var(--dark);padding:16px 40px;}
.trust-bar-inner{max-width:1160px;margin:0 auto;display:flex;justify-content:center;align-items:center;gap:40px;flex-wrap:wrap;}
.ti{display:flex;align-items:center;gap:7px;color:#8B949E;font-size:13px;font-weight:500;}
.ti strong{color:#E6EDF3;}
.tdiv{width:1px;height:18px;background:#30363D;}

/* SECTION COMMON */
.sec-label{display:inline-block;font-size:11px;font-weight:700;color:var(--orange);letter-spacing:1.8px;text-transform:uppercase;margin-bottom:10px;}
.sec-h2{font-size:36px;font-weight:900;letter-spacing:-1.2px;line-height:1.12;margin-bottom:12px;}
.sec-sub{font-size:16px;color:var(--muted);line-height:1.68;max-width:540px;}

/* DEMO */
.demo{padding:80px 40px;background:#fff;}
.demo-inner{max-width:1160px;margin:0 auto;display:grid;grid-template-columns:1fr 1fr;gap:64px;align-items:start;}
.demo-stats{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:28px;}
.ds-card{background:var(--bg);border-radius:var(--r);padding:20px;border:1px solid var(--border);}
.ds-num{font-size:32px;font-weight:900;letter-spacing:-1px;color:var(--text);}
.ds-num .u{font-size:16px;font-weight:600;color:var(--muted);}
.ds-lbl{font-size:13px;color:var(--muted);margin-top:4px;line-height:1.4;}
.convo-card{background:var(--bg);border-radius:var(--r-lg);overflow:hidden;border:1px solid var(--border);box-shadow:var(--sh);}
.convo-hdr{background:var(--dark);padding:13px 18px;display:flex;align-items:center;justify-content:space-between;}
.convo-title{color:#8B949E;font-size:12px;margin-left:8px;}
.convo-live{font-size:11px;color:var(--green);font-weight:600;display:flex;align-items:center;gap:4px;}
.convo-live::before{content:"●";font-size:8px;animation:blink 1.5s infinite;}
.convo-body{padding:20px;display:flex;flex-direction:column;gap:14px;}
.cm{display:flex;gap:10px;}.cm-r{flex-direction:row-reverse;}
.ca{width:32px;height:32px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:15px;}
.ca-bot{background:linear-gradient(135deg,var(--orange-glow),#FFF5F0);border:1px solid rgba(255,87,34,.2);}
.ca-usr{background:#EFF6FF;border:1px solid #DBEAFE;}
.cb{max-width:78%;}
.cname{font-size:10px;color:var(--light);font-weight:600;margin-bottom:3px;letter-spacing:.3px;}
.cm-r .cname{text-align:right;}
.ct{padding:10px 14px;border-radius:14px;font-size:13px;line-height:1.55;}
.ct-bot{background:#fff;border:1px solid var(--border);border-top-left-radius:3px;}
.ct-usr{background:#1E3A5F;color:#fff;border-top-right-radius:3px;}
.convo-result{margin:0 20px 20px;padding:12px 16px;background:linear-gradient(135deg,var(--green-bg),#F0FFF4);border:1px solid #A7F3D0;border-radius:10px;display:flex;align-items:center;gap:10px;}
.cr-icon{font-size:20px;}
.cr-title{font-size:13px;font-weight:700;color:var(--green-text);}
.cr-detail{font-size:11px;color:#374151;margin-top:2px;}

/* PAIN */
.pain{padding:72px 40px;background:var(--dark);}
.pain-inner{max-width:1060px;margin:0 auto;text-align:center;}
.pain h2{font-size:36px;font-weight:900;color:#E6EDF3;letter-spacing:-1px;margin-bottom:10px;}
.pain-sub{font-size:16px;color:#8B949E;margin-bottom:52px;}
.pain-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;}
.pc{background:var(--dark-card);border-radius:var(--r);padding:32px 24px;border:1px solid #30363D;transition:border-color .2s;}
.pc:hover{border-color:var(--orange);}
.pn{font-size:46px;font-weight:900;letter-spacing:-2px;line-height:1;margin-bottom:10px;}
.pn.red{color:#FF5F57;}.pn.yellow{color:#FEBC2E;}.pn.blue{color:#58A6FF;}
.pl{font-size:14px;color:#8B949E;line-height:1.6;}

/* COMPARE */
.compare{padding:80px 40px;background:#fff;}
.compare-inner{max-width:920px;margin:0 auto;}
.compare-hdr{text-align:center;margin-bottom:48px;}
.ct-table{width:100%;border-collapse:separate;border-spacing:0;border-radius:var(--r);overflow:hidden;box-shadow:var(--sh);border:1px solid var(--border);}
.ct-table th,.ct-table td{padding:14px 20px;font-size:14px;text-align:left;}
.ct-table tr:not(:last-child) td,.ct-table tr:not(:last-child) th{border-bottom:1px solid var(--border);}
.ct-table th{padding:16px 20px;font-weight:700;font-size:12px;text-transform:uppercase;letter-spacing:.5px;}
.ct-table th:first-child{background:var(--bg2);color:var(--muted);}
.ct-table th:nth-child(2){background:#FFF1F0;color:#9B1C1C;}
.ct-table th:nth-child(3){background:#F0FDF4;color:#14532D;}
.ct-table td:first-child{font-weight:600;color:var(--text);background:var(--bg);font-size:13px;}
.ct-table td:nth-child(2){background:#fff;color:var(--muted);font-size:13px;}
.ct-table td:nth-child(3){background:#fff;color:#374151;font-weight:500;font-size:13px;}
.ct-table tr:hover td{background:#FAFAF8!important;}
.td-bad{color:#EF4444!important;}.td-good{color:var(--green)!important;font-weight:600!important;}
.compare-callout{margin-top:24px;background:linear-gradient(135deg,var(--green-bg),#F0FFF4);border:1px solid #A7F3D0;border-radius:var(--r);padding:20px 28px;text-align:center;}
.compare-callout strong{font-size:22px;color:var(--green-text);font-weight:800;}
.compare-callout p{font-size:14px;color:#374151;margin-top:4px;}

/* FEATURES */
.features{padding:80px 40px;background:var(--bg);}
.features-inner{max-width:1160px;margin:0 auto;}
.feat-hdr{text-align:center;margin-bottom:52px;}
.feat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;}
.fc{background:#fff;padding:28px;border-radius:var(--r);border:1px solid var(--border);transition:all .2s;}
.fc:hover{transform:translateY(-4px);box-shadow:var(--sh-lg);border-color:rgba(255,87,34,.2);}
.fic{width:48px;height:48px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:22px;margin-bottom:16px;}
.fi-o{background:linear-gradient(135deg,#FFF5F0,#FFE8DF);}
.fi-g{background:linear-gradient(135deg,#ECFDF5,#D1FAE5);}
.fi-b{background:linear-gradient(135deg,#EFF6FF,#DBEAFE);}
.fi-p{background:linear-gradient(135deg,#F5F3FF,#EDE9FE);}
.fi-pk{background:linear-gradient(135deg,#FDF2F8,#FCE7F3);}
.fi-t{background:linear-gradient(135deg,#F0FDFA,#CCFBF1);}
.fc h3{font-size:16px;font-weight:700;margin-bottom:8px;}
.fc p{font-size:13px;color:var(--muted);line-height:1.6;}

/* HOW */
.how{padding:80px 40px;background:#fff;}
.how-inner{max-width:960px;margin:0 auto;}
.how-hdr{text-align:center;margin-bottom:56px;}
.how-steps{display:grid;grid-template-columns:repeat(3,1fr);gap:40px;position:relative;}
.how-steps::before{content:"";position:absolute;top:26px;left:calc(16.66% + 26px);right:calc(16.66% + 26px);height:2px;background:linear-gradient(90deg,var(--orange),rgba(255,87,34,.2));z-index:0;}
.hs{text-align:center;position:relative;z-index:1;}
.hn{width:52px;height:52px;border-radius:50%;font-size:20px;font-weight:800;display:flex;align-items:center;justify-content:center;margin:0 auto 20px;background:linear-gradient(135deg,var(--orange),#FF7043);color:#fff;box-shadow:0 8px 20px rgba(255,87,34,.3);}
.hs h3{font-size:17px;font-weight:700;margin-bottom:8px;}
.hs p{font-size:14px;color:var(--muted);line-height:1.6;}
.how-cta{text-align:center;margin-top:48px;}

/* PRICING */
.pricing{padding:80px 40px;background:var(--bg);}
.pricing-inner{max-width:960px;margin:0 auto;}
.price-hdr{text-align:center;margin-bottom:48px;}
.plans-row{display:grid;grid-template-columns:1fr 1fr;gap:24px;max-width:760px;margin:0 auto 28px;}
.price-card{background:#fff;border:2px solid var(--border);border-radius:var(--r-lg);padding:36px 32px;position:relative;transition:all .2s;}
.price-card:hover{box-shadow:var(--sh-lg);}
.price-card.pop{border-color:var(--orange);box-shadow:0 8px 32px rgba(255,87,34,.12);}
.pop-badge{position:absolute;top:-13px;left:50%;transform:translateX(-50%);background:var(--orange);color:#fff;padding:4px 18px;border-radius:20px;font-size:11px;font-weight:700;white-space:nowrap;letter-spacing:.5px;}
.pname{font-size:18px;font-weight:800;margin-bottom:2px;}
.pdesc{font-size:13px;color:var(--muted);margin-bottom:20px;}
.pamt{font-size:48px;font-weight:900;color:var(--text);line-height:1;letter-spacing:-2px;}
.pamt .cur{font-size:22px;font-weight:700;vertical-align:top;margin-top:9px;display:inline-block;letter-spacing:0;}
.pamt .per{font-size:15px;color:var(--muted);font-weight:500;letter-spacing:0;}
.ptrial{display:inline-block;margin:12px 0 24px;padding:4px 14px;background:var(--green-bg);color:var(--green-text);border-radius:20px;font-size:12px;font-weight:600;}
.pfeats{list-style:none;display:flex;flex-direction:column;gap:10px;margin-bottom:28px;}
.pfeats li{font-size:14px;color:#374151;display:flex;align-items:flex-start;gap:10px;}
.pfeats li .ck{color:var(--green);font-size:16px;flex-shrink:0;}
.pfeats li.dm{color:var(--light);}
.pfeats li.dm .dash{color:var(--border);flex-shrink:0;}
.btn-price{display:block;width:100%;padding:14px;text-align:center;background:var(--orange);color:#fff;text-decoration:none;border-radius:10px;font-size:15px;font-weight:700;border:none;cursor:pointer;transition:all .2s;}
.btn-price:hover{background:var(--orange-dark);transform:translateY(-1px);box-shadow:0 6px 16px rgba(255,87,34,.3);}
.btn-outline{background:#fff;color:var(--orange);border:2px solid var(--orange);}
.btn-outline:hover{background:#FFF5F0;box-shadow:0 4px 12px rgba(255,87,34,.15);}
.roi-box{max-width:560px;margin:4px auto 0;background:linear-gradient(135deg,var(--green-bg),#F0FFF4);border:1px solid #A7F3D0;border-radius:var(--r);padding:24px 28px;}
.roi-box h3{font-size:15px;font-weight:700;color:var(--green-text);margin-bottom:14px;}
.roi-t{width:100%;font-size:13px;border-collapse:collapse;margin-bottom:12px;}
.roi-t td{padding:7px 0;color:#374151;}
.roi-t td:nth-child(2),.roi-t td:nth-child(3){text-align:right;}
.roi-t .save td{font-weight:800;color:var(--green-text);font-size:15px;border-top:2px solid #A7F3D0;padding-top:12px;}
.roi-note{font-size:13px;color:var(--muted);line-height:1.55;font-style:italic;}

/* FAQ */
.faq{padding:80px 40px;background:#fff;}
.faq-inner{max-width:720px;margin:0 auto;}
.faq-hdr{text-align:center;margin-bottom:48px;}
.faq-list details{border-bottom:1px solid var(--border);}
.faq-list summary{padding:18px 0;font-size:15px;font-weight:600;color:var(--text);cursor:pointer;list-style:none;display:flex;justify-content:space-between;align-items:center;transition:color .15s;}
.faq-list summary:hover{color:var(--orange);}
.faq-list summary::after{content:"+";font-size:22px;color:var(--light);font-weight:400;flex-shrink:0;transition:all .2s;}
.faq-list details[open] summary::after{content:"\2212";color:var(--orange);}
.faq-list summary::-webkit-details-marker{display:none;}
.faq-list .fb{padding:0 0 18px;font-size:14px;color:var(--muted);line-height:1.7;}

/* FINAL CTA */
.final-cta{padding:80px 40px;background:linear-gradient(135deg,var(--orange) 0%,#FF8A65 100%);text-align:center;position:relative;overflow:hidden;}
.final-cta::before{content:"";position:absolute;top:-80px;left:-80px;width:300px;height:300px;background:rgba(255,255,255,.06);border-radius:50%;}
.final-cta::after{content:"";position:absolute;bottom:-60px;right:-60px;width:240px;height:240px;background:rgba(255,255,255,.06);border-radius:50%;}
.final-cta-inner{max-width:640px;margin:0 auto;position:relative;z-index:1;}
.final-cta h2{color:#fff;font-size:36px;font-weight:900;letter-spacing:-1px;margin-bottom:14px;line-height:1.15;}
.final-cta p{color:rgba(255,255,255,.85);font-size:16px;margin-bottom:32px;line-height:1.65;}
.btn-final{display:inline-flex;align-items:center;gap:8px;padding:17px 44px;background:#fff;color:var(--orange);text-decoration:none;border-radius:var(--r);font-size:17px;font-weight:800;transition:all .2s;box-shadow:0 8px 24px rgba(0,0,0,.15);}
.btn-final:hover{background:#FFF5F0;transform:translateY(-2px);box-shadow:0 12px 32px rgba(0,0,0,.2);}
.final-sub{margin-top:14px;color:rgba(255,255,255,.7);font-size:14px;}
.final-sub a{color:rgba(255,255,255,.9);text-decoration:underline;}

/* FOOTER */
.footer{background:var(--dark);padding:52px 40px 32px;}
.footer-inner{max-width:1160px;margin:0 auto;display:flex;justify-content:space-between;flex-wrap:wrap;gap:40px;margin-bottom:40px;}
.footer-logo{font-size:20px;font-weight:800;color:#fff;text-decoration:none;letter-spacing:-.5px;}
.footer-logo span{color:var(--orange);}
.footer-tag{font-size:13px;color:#8B949E;margin-top:6px;}
.fcol h4{color:#E6EDF3;font-size:13px;font-weight:700;margin-bottom:14px;letter-spacing:.3px;}
.fcol a{display:block;color:#8B949E;text-decoration:none;font-size:13px;padding:4px 0;transition:color .15s;}
.fcol a:hover{color:#E6EDF3;}
.footer-bot{max-width:1160px;margin:0 auto;padding-top:24px;border-top:1px solid #21262D;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;}
.footer-bot p{font-size:12px;color:#6E7681;}

/* RESPONSIVE */
@media(max-width:900px){
  .nav-inner{padding:14px 24px;}
  .nav-links{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(250,250,248,.97);backdrop-filter:blur(20px);flex-direction:column;justify-content:center;align-items:center;gap:8px;z-index:999;}
  .nav-links.open{display:flex;}
  .nav-links a{font-size:18px;padding:12px 24px;}
  .nav-toggle{display:flex;z-index:1001;position:relative;}
  .hero{padding:48px 24px 56px;}
  .hero-inner{grid-template-columns:1fr;gap:40px;}
  .hero h1{font-size:38px;letter-spacing:-1.5px;}
  .hero p{font-size:16px;}
  .float-b{display:none;}
  .trust-bar{padding:14px 24px;}
  .trust-bar-inner{gap:20px;}
  .tdiv{display:none;}
  .demo{padding:56px 24px;}
  .demo-inner{grid-template-columns:1fr;gap:40px;}
  .pain{padding:56px 24px;}
  .pain-grid{grid-template-columns:1fr;gap:16px;max-width:380px;margin:0 auto;}
  .compare{padding:56px 24px;}
  .ct-table{font-size:12px;}
  .ct-table th,.ct-table td{padding:10px 11px;}
  .features{padding:56px 24px;}
  .feat-grid{grid-template-columns:repeat(2,1fr);}
  .how{padding:56px 24px;}
  .how-steps{grid-template-columns:1fr;gap:32px;max-width:340px;margin:0 auto;}
  .how-steps::before{display:none;}
  .pricing{padding:56px 24px;}
  .plans-row{grid-template-columns:1fr;max-width:400px;margin-left:auto;margin-right:auto;}
  .faq{padding:56px 24px;}
  .final-cta{padding:56px 24px;}
  .final-cta h2{font-size:28px;}
  .footer{padding:40px 24px 24px;}
  .footer-bot{flex-direction:column;text-align:center;}
  .demo-stats{grid-template-columns:1fr 1fr;}
  .sec-h2{font-size:30px;}
}
@media(max-width:480px){
  .hero h1{font-size:32px;}
  .feat-grid{grid-template-columns:1fr;}
  .demo-stats{grid-template-columns:1fr 1fr;}
  .trust-bar-inner{gap:14px;}
}

/* Social proof */
.social-proof{padding:64px 40px;background:#fff;border-top:1px solid var(--border);border-bottom:1px solid var(--border);}
.sp-inner{max-width:1000px;margin:0 auto;text-align:center;}
.sp-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin-top:32px;}
.sp-card{padding:28px;background:var(--bg);border-radius:var(--r);border:1px solid var(--border);}
.sp-card .sp-icon{font-size:32px;margin-bottom:12px;}
.sp-card h3{font-size:16px;font-weight:700;color:var(--text);margin-bottom:6px;}
.sp-card p{font-size:14px;color:var(--muted);line-height:1.6;}
@media(max-width:700px){.sp-cards{grid-template-columns:1fr;}}

/* Contact form */
.contact-section{padding:64px 40px;background:var(--bg2);}
.contact-inner{max-width:560px;margin:0 auto;}
.contact-inner h2{font-size:28px;font-weight:800;letter-spacing:-0.5px;text-align:center;margin-bottom:8px;}
.contact-sub{text-align:center;color:var(--muted);font-size:15px;margin-bottom:28px;}
.contact-form{display:flex;flex-direction:column;gap:14px;}
.contact-form input,.contact-form textarea{padding:12px 14px;border:1.5px solid var(--border);border-radius:10px;font-size:15px;font-family:inherit;background:#fff;}
.contact-form input:focus,.contact-form textarea:focus{outline:none;border-color:var(--orange);box-shadow:0 0 0 3px rgba(255,87,34,.1);}
.contact-form textarea{min-height:100px;resize:vertical;}
.contact-form .row{display:flex;gap:14px;}
.contact-form .row input{flex:1;}
.btn-contact{padding:14px;background:var(--orange);color:#fff;border:none;border-radius:10px;font-size:16px;font-weight:700;cursor:pointer;transition:all .2s;font-family:inherit;}
.btn-contact:hover{background:var(--orange-dark);}
.btn-contact:disabled{opacity:.6;cursor:not-allowed;}
.contact-msg{text-align:center;margin-top:12px;font-size:14px;color:#059669;display:none;}
@media(max-width:600px){.contact-form .row{flex-direction:column;}}

/* WhatsApp floating button */
.wa-float{position:fixed;bottom:24px;right:24px;z-index:999;width:56px;height:56px;background:#25D366;border-radius:50%;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 16px rgba(37,211,102,.4);transition:transform .2s;text-decoration:none;}
.wa-float:hover{transform:scale(1.1);}
.wa-float svg{width:28px;height:28px;fill:#fff;}
</style>
</head>
<body>

<!-- NAV -->
<nav class="nav" id="nav">
<div class="nav-inner">
  <a class="nav-logo" href="/"><span>Prop</span>Bot</a>
  <button class="nav-toggle" id="ntog" aria-label="Menu">
    <span></span><span></span><span></span>
  </button>
  <div class="nav-links" id="nlinks">
    <a href="#demo">Live Demo</a>
    <a href="#features">Features</a>
    <a href="#pricing">Pricing</a>
    <a href="#faq">FAQ</a>
    <a href="/dashboard">Login</a>
    <a href="/signup" class="btn-nav">Start Free Trial &rarr;</a>
  </div>
</div>
</nav>

<!-- HERO -->
<section class="hero">
<div class="hero-inner">
  <div>
    <div class="hero-badge"><span class="pulse"></span> AI Receptionist for Indian Real Estate</div>
    <h1>Never Miss a Lead.<br><span class="hl">Even at 2 AM.</span></h1>
    <p>PropBot answers every call in Hindi, English, and Hinglish &mdash; 24/7. Qualifies buyers, books site visits, captures leads. All while you sleep.</p>
    <a href="/signup" class="btn-hero">Start Free 14-Day Trial &rarr;</a>
    <div class="hero-fine">
      <span>&#10003; No credit card</span>
      <span>&#10003; Live in 5 minutes</span>
      <span>&#10003; Cancel anytime</span>
    </div>
  </div>
  <div class="hero-visual">
    <div class="float-b fb1">&#128276; New lead: Suresh M. &middot; 3BHK &middot; &#8377;65L</div>
    <div class="mock-card">
      <div class="mock-header">
        <div class="dots"><span class="d-r"></span><span class="d-y"></span><span class="d-g"></span></div>
        <span class="mock-title">PropBot &mdash; Live Call &middot; 2:17 AM</span>
        <div class="mock-live">LIVE</div>
      </div>
      <div class="mock-body">
        <div class="notif-strip">
          <div class="ni">&#9989;</div>
          <div>
            <div class="nt">Lead Captured</div>
            <div class="nd">Rajesh Kumar &middot; +91 98765 43210<br>2BHK &middot; Noida Sec 62 &middot; Budget &#8377;45&ndash;55L</div>
          </div>
        </div>
        <div class="chat-win">
          <div class="chat-top">
            <div class="chat-av">&#129302;</div>
            <div class="chat-inf">
              <div class="cn">PropBot &mdash; Priya</div>
              <div class="cp">+91 99887 76655 calling</div>
            </div>
            <div class="chat-status-badge">&#9679; LIVE</div>
          </div>
          <div class="msgs">
            <div class="mb mb-bot">
              <div class="mn">Priya &middot; PropBot AI</div>
              <div class="bub bub-bot">Namaste! Main Priya hoon. Aap kaunsi property dhundh rahe hain? &#128591;</div>
            </div>
            <div class="mb mb-usr">
              <div class="mn">Caller</div>
              <div class="bub bub-usr">2BHK chahiye, Noida Sector 62, budget 45&ndash;50 lakh</div>
            </div>
            <div class="mb mb-bot">
              <div class="mn">Priya &middot; PropBot AI</div>
              <div class="bub bub-bot">Perfect! Sector 62 mein ek 2BHK hai &mdash; 1200 sqft, &#8377;48L. Kya aaj site visit schedule karein? &#128197;</div>
            </div>
          </div>
          <div class="chat-foot">
            <div class="cf-ok">&#10003; Site visit booked for tomorrow</div>
            <div class="cf-time">2:17 AM</div>
          </div>
        </div>
      </div>
    </div>
    <div class="float-b fb2">&#9889; Response time: &lt;1 second</div>
  </div>
</div>
</section>

<!-- TRUST BAR -->
<div class="trust-bar">
<div class="trust-bar-inner">
  <div class="ti">&#128222; <strong>24/7</strong> Availability</div>
  <div class="tdiv"></div>
  <div class="ti">&#127470;&#127475; Hindi <strong>+</strong> English <strong>+</strong> Hinglish</div>
  <div class="tdiv"></div>
  <div class="ti">&#9889; Setup in <strong>5 minutes</strong></div>
  <div class="tdiv"></div>
  <div class="ti">&#128176; Save <strong>&#8377;1.5L+/year</strong> vs receptionist</div>
  <div class="tdiv"></div>
  <div class="ti">&#128274; Your data, <strong>100% secure</strong></div>
</div>
</div>

<!-- DEMO -->
<section class="demo" id="demo">
<div class="demo-inner">
  <div>
    <div class="sec-label">Live Demo</div>
    <h2 class="sec-h2">Hear Exactly What Your Buyers Experience</h2>
    <p class="sec-sub">This is a real conversation PropBot handles at 2 AM &mdash; while you sleep. Natural Hindi. Instant responses. Lead captured and site visit booked before you wake up.</p>
    <div class="demo-stats">
      <div class="ds-card">
        <div class="ds-num">&lt;1<span class="u">s</span></div>
        <div class="ds-lbl">Response time on every single call</div>
      </div>
      <div class="ds-card">
        <div class="ds-num">24<span class="u">/7</span></div>
        <div class="ds-lbl">Zero downtime, zero sick days</div>
      </div>
      <div class="ds-card">
        <div class="ds-num">6</div>
        <div class="ds-lbl">Natural Indian voices to choose from</div>
      </div>
      <div class="ds-card">
        <div class="ds-num">5<span class="u">min</span></div>
        <div class="ds-lbl">From signup to live AI receptionist</div>
      </div>
    </div>
  </div>
  <div>
    <div class="convo-card">
      <div class="convo-hdr">
        <div style="display:flex;align-items:center;">
          <div class="dots"><span class="d-r"></span><span class="d-y"></span><span class="d-g"></span></div>
          <span class="convo-title">Incoming call &mdash; Tuesday, 2:17 AM</span>
        </div>
        <div class="convo-live">LIVE CALL</div>
      </div>
      <div class="convo-body">
        <div class="cm">
          <div class="ca ca-bot">&#129302;</div>
          <div class="cb">
            <div class="cname">Priya &middot; PropBot AI</div>
            <div class="ct ct-bot">Namaste! Main Priya hoon. Aap kaunsi property dhundh rahe hain? &#128591;</div>
          </div>
        </div>
        <div class="cm cm-r">
          <div class="ca ca-usr">&#128100;</div>
          <div class="cb">
            <div class="cname">Suresh M.</div>
            <div class="ct ct-usr">Bhai 3BHK chahiye, Noida Sector 62, budget mera 60&ndash;70 lakh hai</div>
          </div>
        </div>
        <div class="cm">
          <div class="ca ca-bot">&#129302;</div>
          <div class="cb">
            <div class="cname">Priya &middot; PropBot AI</div>
            <div class="ct ct-bot">Bilkul! Sector 62 mein ek 3BHK hai &mdash; 1450 sqft, 3rd floor, &#8377;68L. Bahut accha option hai. Aapka naam aur number le sakti hoon?</div>
          </div>
        </div>
        <div class="cm cm-r">
          <div class="ca ca-usr">&#128100;</div>
          <div class="cb">
            <div class="cname">Suresh M.</div>
            <div class="ct ct-usr">Suresh Mehta, 9876543210</div>
          </div>
        </div>
        <div class="cm">
          <div class="ca ca-bot">&#129302;</div>
          <div class="cb">
            <div class="cname">Priya &middot; PropBot AI</div>
            <div class="ct ct-bot">Perfect Suresh ji! Kal subah 11 baje site visit book kar diya hai. Confirm ho gaya &#9989;</div>
          </div>
        </div>
      </div>
      <div class="convo-result">
        <div class="cr-icon">&#127919;</div>
        <div>
          <div class="cr-title">Lead Captured + Site Visit Booked</div>
          <div class="cr-detail">Suresh Mehta &middot; 3BHK &#8377;68L &middot; Visit: Tomorrow 11 AM &rarr; your Google Calendar &middot; Alert sent instantly</div>
        </div>
      </div>
    </div>
  </div>
</div>
</section>

<!-- PAIN STATS -->
<section class="pain">
<div class="pain-inner">
  <h2>Jo Aap Miss Kar Rahe Hain</h2>
  <p class="pain-sub">Ek missed call matlab ek missed deal. Numbers bolte hain.</p>
  <div class="pain-grid">
    <div class="pc">
      <div class="pn red">&#8377;15&ndash;25K</div>
      <div class="pl">Monthly salary you pay a human receptionist &mdash; who takes sick days, leaves, and misses calls after 6 PM anyway</div>
    </div>
    <div class="pc">
      <div class="pn yellow">40%</div>
      <div class="pl">Calls missed after 6 PM and on weekends &mdash; the exact time serious buyers are searching online</div>
    </div>
    <div class="pc">
      <div class="pn blue">0</div>
      <div class="pl">Leads captured at 2 AM by a human receptionist. PropBot catches every single one.</div>
    </div>
  </div>
</div>
</section>

<!-- COMPARE -->
<section class="compare" id="compare">
<div class="compare-inner">
  <div class="compare-hdr">
    <div class="sec-label">The Real Comparison</div>
    <h2 class="sec-h2">Why Smart Agents Are Switching to AI</h2>
  </div>
  <table class="ct-table">
    <thead>
      <tr>
        <th></th>
        <th>Human Receptionist</th>
        <th>PropBot AI &#10003;</th>
      </tr>
    </thead>
    <tbody>
      <tr><td>Monthly Cost</td><td class="td-bad">&#8377;15,000 &ndash; &#8377;25,000</td><td class="td-good">&#8377;2,499 &ndash; &#8377;4,999</td></tr>
      <tr><td>Availability</td><td class="td-bad">9 AM &ndash; 6 PM, Mon&ndash;Sat</td><td class="td-good">24/7/365. Never sick.</td></tr>
      <tr><td>Languages</td><td>1&ndash;2 languages only</td><td class="td-good">Hindi, English, Hinglish</td></tr>
      <tr><td>Response Time</td><td class="td-bad">Depends on mood</td><td class="td-good">Under 1 second. Every time.</td></tr>
      <tr><td>Lead Capture</td><td class="td-bad">Pen &amp; paper / forgets</td><td class="td-good">Auto-captured + instant email</td></tr>
      <tr><td>Call Recording</td><td class="td-bad">Not possible</td><td class="td-good">Every call recorded + transcribed</td></tr>
      <tr><td>Site Visit Booking</td><td class="td-bad">Manual back-and-forth</td><td class="td-good">Books into Google Calendar live</td></tr>
      <tr><td>Simultaneous Calls</td><td class="td-bad">1 call at a time</td><td class="td-good">Unlimited, simultaneously</td></tr>
      <tr><td>Setup Time</td><td class="td-bad">2&ndash;4 weeks training</td><td class="td-good">5 minutes. You&rsquo;re live.</td></tr>
      <tr><td>Sick Days / Leaves</td><td class="td-bad">15&ndash;20 days/year absent</td><td class="td-good">Zero. Ever.</td></tr>
    </tbody>
  </table>
  <div class="compare-callout">
    <strong>Save &#8377;1,20,000 &ndash; &#8377;2,40,000 per year</strong>
    <p>Aur koi chutti bhi nahi mangega. Kabhi nahi.</p>
  </div>
</div>
</section>

<!-- FEATURES -->
<section class="features" id="features">
<div class="features-inner">
  <div class="feat-hdr">
    <div class="sec-label">Everything Included</div>
    <h2 class="sec-h2">Your Complete AI Receptionist Stack</h2>
  </div>
  <div class="feat-grid">
    <div class="fc"><div class="fic fi-o">&#128222;</div><h3>AI Voice Calls</h3><p>Natural Hindi and English conversations. 6 Indian voices. Callers won&rsquo;t know it&rsquo;s AI &mdash; sounds like a real, warm team member.</p></div>
    <div class="fc"><div class="fic fi-g">&#128172;</div><h3>Website Chat Widget</h3><p>Embed on your property website in 2 minutes. Answers listing questions, captures phone numbers, qualifies visitors automatically.</p></div>
    <div class="fc"><div class="fic fi-b">&#127919;</div><h3>Auto Lead Capture</h3><p>Name, phone, budget, area preference &mdash; all captured the moment they call. Instant email alert. Nothing falls through the cracks.</p></div>
    <div class="fc"><div class="fic fi-p">&#128197;</div><h3>Google Calendar Booking</h3><p>PropBot books site visits live on the call, straight into your Google Calendar. Confirms with the caller on the spot. Zero back-and-forth.</p></div>
    <div class="fc"><div class="fic fi-pk">&#128200;</div><h3>Dashboard &amp; Analytics</h3><p>All leads, call recordings, and transcripts in one clean dashboard. Know exactly what every buyer asked, their budget, and timeline.</p></div>
    <div class="fc"><div class="fic fi-t">&#9889;</div><h3>Instant Alerts</h3><p>Get notified the moment a qualified lead comes in &mdash; by email and SMS. Hot buyers never wait. You never miss a deal again.</p></div>
  </div>
</div>
</section>

<!-- SOCIAL PROOF -->
<section class="social-proof">
<div class="sp-inner">
  <div class="sec-label">Built for India</div>
  <h2 class="sec-h2">Why Indian Real Estate Agents Choose PropBot</h2>
  <div class="sp-cards">
    <div class="sp-card"><div class="sp-icon">&#127470;&#127475;</div><h3>Hindi + English + Hinglish</h3><p>Your AI speaks the way your clients do. Fluent in Hindi, English, and natural Hinglish &mdash; so every caller feels at home.</p></div>
    <div class="sp-card"><div class="sp-icon">&#127968;</div><h3>Made for Indian Real Estate</h3><p>Understands BHK, carpet area, RERA, possession dates, and how Indian buyers actually talk about property. Not a generic chatbot.</p></div>
    <div class="sp-card"><div class="sp-icon">&#128176;</div><h3>Save &#8377;1.5L+ Per Year</h3><p>Replace a full-time receptionist for a fraction of the cost. Works 24/7 including Sundays and holidays. Never takes leave.</p></div>
  </div>
</div>
</section>

<!-- HOW IT WORKS -->
<section class="how" id="how">
<div class="how-inner">
  <div class="how-hdr">
    <div class="sec-label">Setup</div>
    <h2 class="sec-h2">Live in 5 Minutes. Seriously.</h2>
    <p style="color:var(--muted);font-size:16px;margin-top:8px;text-align:center;">No technical skills. No onboarding calls. No waiting.</p>
  </div>
  <div class="how-steps">
    <div class="hs"><div class="hn">1</div><h3>Sign Up &amp; Add Details</h3><p>Your business name, phone, email. Done in 60 seconds. Choose your AI voice from 6 natural Indian options.</p></div>
    <div class="hs"><div class="hn">2</div><h3>Add Your Listings</h3><p>Paste your property details. Your AI instantly learns your entire inventory &mdash; prices, areas, amenities, everything.</p></div>
    <div class="hs"><div class="hn">3</div><h3>Go Live &amp; Close More</h3><p>Get your dedicated number and chat widget. Start receiving AI-handled calls. Check your dashboard. Close deals.</p></div>
  </div>
  <div class="how-cta">
    <a href="/signup" class="btn-hero">Get Started Free &mdash; No Card Needed &rarr;</a>
  </div>
</div>
</section>

<!-- PRICING -->
<section class="pricing" id="pricing">
<div class="pricing-inner">
  <div class="price-hdr">
    <div class="sec-label">Pricing</div>
    <h2 class="sec-h2">Simple, Honest Pricing</h2>
    <p style="color:var(--muted);font-size:16px;margin-top:8px;">14-day free trial on both plans. No credit card required.</p>
  </div>
  <div class="plans-row">
    <div class="price-card">
      <div class="pname">Starter</div>
      <div class="pdesc">For solo brokers starting with AI</div>
      <div class="pamt"><span class="cur">&#8377;</span>2,499<span class="per">/mo</span></div>
      <div class="ptrial">14-day free trial</div>
      <ul class="pfeats">
        <li><span class="ck">&#10003;</span> AI voice receptionist (Priya)</li>
        <li><span class="ck">&#10003;</span> Hindi + Hinglish conversations</li>
        <li><span class="ck">&#10003;</span> Lead alerts to your email</li>
        <li><span class="ck">&#10003;</span> Lead &amp; call dashboard</li>
        <li><span class="ck">&#10003;</span> Up to 50 calls / month</li>
        <li class="dm"><span class="dash">&mdash;</span> Chat widget for website</li>
        <li class="dm"><span class="dash">&mdash;</span> Priority support</li>
      </ul>
      <a href="/signup?plan=starter" class="btn-price btn-outline">Start Free Trial</a>
    </div>
    <div class="price-card pop">
      <div class="pop-badge">MOST POPULAR</div>
      <div class="pname">Pro</div>
      <div class="pdesc">For serious brokers who can&rsquo;t miss a lead</div>
      <div class="pamt"><span class="cur">&#8377;</span>4,999<span class="per">/mo</span></div>
      <div class="ptrial">14-day free trial</div>
      <ul class="pfeats">
        <li><span class="ck">&#10003;</span> AI voice receptionist (your choice)</li>
        <li><span class="ck">&#10003;</span> Hindi + Hinglish conversations</li>
        <li><span class="ck">&#10003;</span> Lead alerts &mdash; email + SMS</li>
        <li><span class="ck">&#10003;</span> Full lead &amp; call dashboard</li>
        <li><span class="ck">&#10003;</span> <strong>Unlimited calls</strong></li>
        <li><span class="ck">&#10003;</span> Chat widget for your website</li>
        <li><span class="ck">&#10003;</span> Priority onboarding support</li>
      </ul>
      <a href="/signup?plan=pro" class="btn-price">Start Free Trial &rarr;</a>
    </div>
  </div>
  <div class="roi-box">
    <h3>Your ROI on the Pro Plan</h3>
    <table class="roi-t">
      <tr><td></td><td><strong>Human Receptionist</strong></td><td><strong>PropBot Pro</strong></td></tr>
      <tr><td>Monthly cost</td><td>&#8377;20,000</td><td>&#8377;4,999</td></tr>
      <tr><td>Annual cost</td><td>&#8377;2,40,000</td><td>&#8377;59,988</td></tr>
      <tr class="save"><td>You save</td><td></td><td>&#8377;1,80,012/year</td></tr>
    </table>
    <p class="roi-note">One deal from a 2 AM missed call pays for PropBot Pro for 3 months. Every missed call is money left on the table.</p>
  </div>
</div>
</section>

<!-- FAQ -->
<section class="faq" id="faq">
<div class="faq-inner">
  <div class="faq-hdr">
    <div class="sec-label">FAQ</div>
    <h2 class="sec-h2">Questions? We Have Answers.</h2>
  </div>
  <div class="faq-list">
    <details><summary>Will my callers know they&rsquo;re talking to AI?</summary><div class="fb">PropBot uses natural Indian voices that sound remarkably human. Most callers don&rsquo;t realise it&rsquo;s AI. Choose from 6 voices &mdash; male and female &mdash; with natural Hindi/English accents.</div></details>
    <details><summary>Does it work in Hindi?</summary><div class="fb">Yes &mdash; fluent Hindi, English, and Hinglish. Understands mixed-language queries naturally, just like how real conversations happen in India. No robotic translation.</div></details>
    <details><summary>What if the caller wants to talk to me directly?</summary><div class="fb">PropBot captures their details and sends you an instant alert. You can also enable callback requests. You&rsquo;re always in control of follow-ups.</div></details>
    <details><summary>How long does setup take?</summary><div class="fb">Under 5 minutes. Sign up, add your property details, pick a voice &mdash; and your AI receptionist is live. No technical skills. No waiting for an onboarding call.</div></details>
    <details><summary>What happens after the 14-day free trial?</summary><div class="fb">Your subscription continues at &#8377;2,499/month (Starter) or &#8377;4,999/month (Pro) via Razorpay. Cancel anytime from the dashboard &mdash; no lock-in, no cancellation fees.</div></details>
    <details><summary>Can I use it with my existing phone number?</summary><div class="fb">PropBot gives you a dedicated phone number. Forward calls from your existing number to it, or share the PropBot number directly with clients &mdash; your choice.</div></details>
    <details><summary>What about the 50 call limit on Starter?</summary><div class="fb">Once you hit 50 calls/month on Starter, PropBot informs callers the line is busy. Upgrade to Pro for unlimited calls anytime from your dashboard.</div></details>
    <details><summary>Is my data safe?</summary><div class="fb">All data is encrypted and stored securely. Call recordings, transcripts, and lead info are only accessible through your dashboard. We never share your data.</div></details>
  </div>
</div>
</section>

<!-- FINAL CTA -->
<section class="final-cta">
<div class="final-cta-inner">
  <h2>Your Competitors Are Going AI.<br>Don&rsquo;t Get Left Behind.</h2>
  <p>Every missed call is a missed deal. Every missed deal is lakhs lost. Start your free trial today &mdash; no credit card, no risk, cancel anytime.</p>
  <a href="/signup?plan=pro" class="btn-final">Start My Free Trial &rarr;</a>
  <div class="final-sub">Already have an account? <a href="/dashboard">Login to Dashboard</a></div>
</div>
</section>

<!-- CONTACT FORM -->
<section class="contact-section" id="contact">
<div class="contact-inner">
  <h2>Have Questions?</h2>
  <p class="contact-sub">Drop us a message and we'll get back to you within hours.</p>
  <form class="contact-form" id="contactForm" onsubmit="return submitContact(event)">
    <div class="row">
      <input name="name" placeholder="Your name" required>
      <input name="phone" placeholder="Phone / WhatsApp" required>
    </div>
    <input name="email" type="email" placeholder="Email (optional)">
    <textarea name="message" placeholder="What would you like to know?" required></textarea>
    <button type="submit" class="btn-contact" id="contactBtn">Send Message</button>
  </form>
  <div class="contact-msg" id="contactMsg">Thanks! We'll get back to you shortly.</div>
</div>
</section>

<!-- FOOTER -->
<footer class="footer">
<div class="footer-inner">
  <div>
    <a class="footer-logo" href="/"><span>Prop</span>Bot</a>
    <div class="footer-tag">AI Receptionist for Indian Real Estate</div>
  </div>
  <div class="fcol">
    <h4>Product</h4>
    <a href="#demo">Live Demo</a>
    <a href="#features">Features</a>
    <a href="#pricing">Pricing</a>
    <a href="#how">How It Works</a>
  </div>
  <div class="fcol">
    <h4>Account</h4>
    <a href="/signup">Start Free Trial</a>
    <a href="/dashboard">Login to Dashboard</a>
    <a href="#faq">FAQ</a>
  </div>
  <div class="fcol">
    <h4>Contact</h4>
    <a href="mailto:daanzack8@gmail.com">daanzack8@gmail.com</a>
    <!-- __WHATSAPP_FOOTER__ -->
    <a href="#contact">Send a Message</a>
  </div>
</div>
<div class="footer-bot">
  <p>&copy; 2026 PropBot. All rights reserved.</p>
  <p>Made with &#10084;&#65039; in India</p>
</div>
</footer>

<script>
window.addEventListener('scroll',function(){document.getElementById('nav').classList.toggle('scrolled',window.scrollY>10);});
var tog=document.getElementById('ntog'),lnk=document.getElementById('nlinks');
tog.addEventListener('click',function(){
  var open=lnk.classList.toggle('open');
  var s=tog.querySelectorAll('span');
  s[0].style.transform=open?'translateY(7px) rotate(45deg)':'';
  s[1].style.opacity=open?'0':'1';
  s[2].style.transform=open?'translateY(-7px) rotate(-45deg)':'';
});
document.querySelectorAll('.nav-links a').forEach(function(a){a.addEventListener('click',function(){lnk.classList.remove('open');tog.querySelectorAll('span').forEach(function(s){s.style.transform='';s.style.opacity='1';});});});
</script>
<!-- __WHATSAPP_FLOAT__ -->

<script>
function submitContact(e){
  e.preventDefault();
  var f=document.getElementById('contactForm'),b=document.getElementById('contactBtn');
  b.disabled=true;b.textContent='Sending...';
  var d=new FormData(f);
  fetch('/contact',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name:d.get('name'),phone:d.get('phone'),email:d.get('email')||'',message:d.get('message')})
  }).then(function(r){return r.json()}).then(function(){
    document.getElementById('contactMsg').style.display='block';
    f.reset();b.textContent='Sent!';
    setTimeout(function(){b.disabled=false;b.textContent='Send Message';},3000);
  }).catch(function(){b.disabled=false;b.textContent='Send Message';alert('Error sending message. Please try again.');});
  return false;
}
</script>
</body>
</html>
"""
