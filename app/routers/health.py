     1|from fastapi import APIRouter, Request
     2|from fastapi.responses import HTMLResponse
     3|
     4|from app.config import settings
     5|
     6|router = APIRouter()
     7|
     8|
     9|def _ga_snippet() -> str:
    10|    """Return GA4 script tags if GA_MEASUREMENT_ID is configured, else empty string."""
    11|    gid = settings.GA_MEASUREMENT_ID
    12|    if not gid:
    13|        return ""
    14|    return (
    15|        f'<script async src="https://www.googletagmanager.com/gtag/js?id={gid}"></script>\n'
    16|        f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}"
    17|        f"gtag('js',new Date());gtag('config','{gid}');</script>\n"
    18|    )
    19|
    20|
    21|def _og_tags() -> str:
    22|    """Return Open Graph + canonical meta tags."""
    23|    url = settings.BASE_URL
    24|    return (
    25|        f'<link rel="canonical" href="{url}/">\n'
    26|        f'<meta property="og:title" content="PropBot - AI Receptionist for Indian Real Estate Agents">\n'
    27|        f'<meta property="og:description" content="Answer every call 24/7 in Hindi & English. From ₹2,499/month.">\n'
    28|        f'<meta property="og:type" content="website">\n'
    29|        f'<meta property="og:url" content="{url}/">\n'
    30|        f'<meta name="twitter:card" content="summary">\n'
    31|        f'<meta name="twitter:title" content="PropBot - AI Receptionist for Indian Real Estate">\n'
    32|        f'<meta name="twitter:description" content="Answer every call 24/7 in Hindi & English. From ₹2,499/month.">\n'
    33|    )
    34|
    35|
    36|@router.get("/", response_class=HTMLResponse)
    37|async def root():
    38|    """Landing page — marketing site."""
    39|    from app.db.supabase_client import get_supabase
    40|    html = LANDING_HTML.replace("<!-- __GA__ -->", _ga_snippet())
    41|    html = html.replace("<!-- __OG__ -->", _og_tags())
    42|
    43|    # Founders banner + dynamic pricing
    44|    slots_total = 0
    45|    try:
    46|        slots_total = int(settings.FOUNDERS_SLOTS or 0)
    47|    except ValueError:
    48|        pass
    49|
    50|    founder_active = False
    51|    slots_remaining = 0
    52|    if slots_total > 0:
    53|        try:
    54|            db = get_supabase()
    55|            result = db.table("clients").select("id", count="exact").eq("is_founder", True).execute()
    56|            used = result.count or 0
    57|        except Exception:
    58|            used = 0
    59|        slots_remaining = max(0, slots_total - used)
    60|        founder_active = slots_remaining > 0
    61|
    62|    if founder_active:
    63|        founders_html = (
    64|            '<div class="founders-banner"><div class="fb-inner">'
    65|            '<span class="fb-badge">LAUNCH OFFER</span>'
    66|            '<span class="fb-text">First Founders get <strong class="fb-price">30% off for life</strong> '
    67|            '&mdash; Starter at <strong>&#8377;1,749/mo</strong>, Pro at <strong>&#8377;3,499/mo</strong></span>'
    68|            f'<span class="fb-slots">Only {slots_remaining} spots left</span>'
    69|            '</div></div>'
    70|        )
    71|        starter_price = '<span style="font-size:14px;color:#6B7280;text-decoration:line-through">&#8377;2,499</span> <span class="cur">&#8377;</span>1,749<span class="per">/mo</span>'
    72|        pro_price = '<span style="font-size:14px;color:#6B7280;text-decoration:line-through">&#8377;4,999</span> <span class="cur">&#8377;</span>3,499<span class="per">/mo</span>'
    73|    elif slots_total > 0:
    74|        # All founder slots filled
    75|        founders_html = ""
    76|        starter_price = '<span class="cur">&#8377;</span>2,499<span class="per">/mo</span>'
    77|        pro_price = '<span class="cur">&#8377;</span>4,999<span class="per">/mo</span>'
    78|    else:
    79|        founders_html = ""
    80|        starter_price = '<span class="cur">&#8377;</span>2,499<span class="per">/mo</span>'
    81|        pro_price = '<span class="cur">&#8377;</span>4,999<span class="per">/mo</span>'
    82|
    83|    html = html.replace("<!-- __FOUNDERS_BANNER__ -->", founders_html)
    84|    html = html.replace("<!-- __STARTER_PRICE__ -->", starter_price)
    85|    html = html.replace("<!-- __PRO_PRICE__ -->", pro_price)
    86|
    87|    # WhatsApp floating button + footer link (only if configured)
    88|    wa = settings.WHATSAPP_NUMBER
    89|    if wa:
    90|        wa_url = f"https://wa.me/91{wa}?text=Hi%20I%27m%20interested%20in%20PropBot"
    91|        wa_float = (
    92|            f'<a class="wa-float" href="{wa_url}" target="_blank" rel="noopener">'
    93|            '<svg viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12 0C5.373 0 0 5.373 0 12c0 2.625.846 5.059 2.284 7.034L.789 23.492a.5.5 0 00.611.611l4.458-1.495A11.952 11.952 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 22c-2.317 0-4.46-.768-6.183-2.064l-.432-.334-3.156 1.058 1.058-3.156-.334-.432A9.955 9.955 0 012 12C2 6.486 6.486 2 12 2s10 4.486 10 10-4.486 10-10 10z"/></svg>'
    94|            '</a>'
    95|        )
    96|        wa_footer = f'<a href="{wa_url}" target="_blank" rel="noopener">WhatsApp us</a>'
    97|    else:
    98|        wa_float = ""
    99|        wa_footer = ""
   100|
   101|    html = html.replace("<!-- __WHATSAPP_FLOAT__ -->", wa_float)
   102|    html = html.replace("<!-- __WHATSAPP_FOOTER__ -->", wa_footer)
   103|
   104|    # Demo call floating button (only if configured)
   105|    demo_phone = settings.DEMO_PHONE_NUMBER
   106|    if demo_phone:
   107|        demo_btn = (
   108|            f'<a class="demo-call-float" href="tel:+91{demo_phone}">'
   109|            '<span class="dcf-pulse"></span>'
   110|            '<svg viewBox="0 0 24 24" width="22" height="22" fill="#fff">'
   111|            '<path d="M6.62 10.79a15.05 15.05 0 006.59 6.59l2.2-2.2a1 1 0 011.01-.24 '
   112|            '11.36 11.36 0 003.58.57 1 1 0 011 1V20a1 1 0 01-1 1A17 17 0 013 4a1 1 0 '
   113|            '011-1h3.5a1 1 0 011 1 11.36 11.36 0 00.57 3.58 1 1 0 01-.24 1.01l-2.2 2.2z"/>'
   114|            '</svg>'
   115|            '<span class="dcf-txt">Try a Demo Call</span></a>'
   116|        )
   117|    else:
   118|        demo_btn = ""
   119|    html = html.replace("<!-- __DEMO_CALL__ -->", demo_btn)
   120|
   121|    return html
   122|
   123|
   124|@router.get("/health")
   125|async def health():
   126|    """Health check endpoint. Also used as self-ping target to keep Render alive."""
   127|    return {"status": "ok", "service": "propbot"}
   128|
   129|
   130|@router.post("/contact")
   131|async def contact_form(request: Request):
   132|    """Receive contact form submission and email it to the founder."""
   133|    import asyncio
   134|    body = await request.json()
   135|    name = body.get("name", "").strip()
   136|    phone = body.get("phone", "").strip()
   137|    email = body.get("email", "").strip()
   138|    message = body.get("message", "").strip()
   139|
   140|    if not name or not phone or not message:
   141|        return {"status": "error", "message": "Please fill all required fields."}
   142|
   143|    if settings.SMTP_EMAIL:
   144|        from app.services.alert_service import _send_email
   145|        try:
   146|            await asyncio.to_thread(
   147|                _send_email,
   148|                to=settings.SMTP_EMAIL,
   149|                subject=f"PropBot Inquiry from {name}",
   150|                body=(
   151|                    f"<h3>New inquiry from PropBot website</h3>"
   152|                    f"<p><strong>Name:</strong> {name}</p>"
   153|                    f"<p><strong>Phone:</strong> {phone}</p>"
   154|                    f"<p><strong>Email:</strong> {email or 'not provided'}</p>"
   155|                    f"<p><strong>Message:</strong><br>{message}</p>"
   156|                ),
   157|            )
   158|        except Exception:
   159|            pass  # Best-effort — don't fail the response
   160|
   161|    return {"status": "ok"}
   162|
   163|
   164|LANDING_HTML = """<!DOCTYPE html>
   165|<html lang="en">
   166|<head>
   167|<meta charset="UTF-8">
   168|<meta name="viewport" content="width=device-width, initial-scale=1.0">
   169|<title>PropBot — AI Receptionist for Indian Real Estate Agents</title>
   170|<meta name="description" content="PropBot answers every call in Hindi & English 24/7, captures leads, books site visits. From ₹2,499/month. 14-day free trial, no credit card.">
   171|<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='8' fill='%23FF5722'/><path d='M16 5 L27 15 L23 15 L23 27 L9 27 L9 15 L5 15 Z' fill='white'/><rect x='12.5' y='19' width='7' height='8' rx='1.5' fill='%23FF5722'/><circle cx='25' cy='8' r='1.8' fill='white' opacity='0.9'/><path d='M26.5 5.5 Q29.5 8 26.5 10.5' stroke='white' stroke-width='1.4' fill='none' stroke-linecap='round' opacity='0.8'/></svg>">
   172|<link rel="apple-touch-icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='8' fill='%23FF5722'/><path d='M16 5 L27 15 L23 15 L23 27 L9 27 L9 15 L5 15 Z' fill='white'/><rect x='12.5' y='19' width='7' height='8' rx='1.5' fill='%23FF5722'/></svg>">
   173|<!-- __GA__ -->
   174|<!-- __OG__ -->
   175|<link rel="preconnect" href="https://fonts.googleapis.com">
   176|<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   177|<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
   178|<style>
   179|:root {
   180|  --orange: #FF5722;
   181|  --orange-dark: #E64A19;
   182|  --orange-glow: rgba(255,87,34,0.12);
   183|  --dark: #0D1117;
   184|  --dark-card: #161B22;
   185|  --text: #111827;
   186|  --muted: #6B7280;
   187|  --light: #9CA3AF;
   188|  --bg: #FAFAF8;
   189|  --bg2: #F3F4F6;
   190|  --white: #FFFFFF;
   191|  --border: #E5E7EB;
   192|  --green: #10B981;
   193|  --green-bg: #ECFDF5;
   194|  --green-text: #065F46;
   195|  --r: 16px;
   196|  --r-lg: 24px;
   197|  --sh: 0 4px 16px rgba(0,0,0,0.08),0 2px 4px rgba(0,0,0,0.04);
   198|  --sh-lg: 0 20px 48px rgba(0,0,0,0.10),0 4px 8px rgba(0,0,0,0.04);
   199|}
   200|*{margin:0;padding:0;box-sizing:border-box;}
   201|html{scroll-behavior:smooth;}
   202|body{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;color:var(--text);background:var(--bg);-webkit-font-smoothing:antialiased;}
   203|
   204|/* NAV */
   205|.nav{position:sticky;top:0;z-index:1000;background:rgba(250,250,248,0.88);backdrop-filter:blur(16px);border-bottom:1px solid transparent;transition:border-color .3s;}
   206|.nav.scrolled{border-color:var(--border);}
   207|.nav-inner{display:flex;justify-content:space-between;align-items:center;padding:14px 40px;max-width:1160px;margin:0 auto;}
   208|.nav-logo{font-size:21px;font-weight:800;color:var(--text);text-decoration:none;letter-spacing:-0.5px;display:flex;align-items:center;gap:8px;}
   209|.nav-logo span{color:var(--orange);}
   210|.nav-logo-icon{width:32px;height:32px;flex-shrink:0;}
   211|.nav-links{display:flex;gap:4px;align-items:center;}
   212|.nav-links a{text-decoration:none;font-size:14px;font-weight:500;color:var(--muted);padding:7px 12px;border-radius:10px;transition:all .15s;}
   213|.nav-links a:hover{color:var(--text);background:rgba(0,0,0,0.04);}
   214|.btn-nav{background:var(--orange)!important;color:#fff!important;padding:9px 20px!important;border-radius:10px!important;font-weight:700!important;}
   215|.btn-nav:hover{background:var(--orange-dark)!important;box-shadow:0 4px 12px rgba(255,87,34,.3)!important;}
   216|.nav-toggle{display:none;background:none;border:none;cursor:pointer;padding:10px;flex-direction:column;gap:5px;margin-right:-10px;min-width:44px;min-height:44px;align-items:center;justify-content:center;}
   217|.nav-toggle span{display:block;width:24px;height:2.5px;background:var(--text);border-radius:2px;transition:all .25s;}
   218|
   219|/* HERO */
   220|.hero{padding:72px 40px 80px;background:linear-gradient(150deg,#FFFAF7 0%,#FFF5EF 45%,#F0F4FF 100%);overflow:hidden;}
   221|.hero-inner{max-width:1160px;margin:0 auto;display:grid;grid-template-columns:1fr 1fr;gap:64px;align-items:center;}
   222|.hero-badge{display:inline-flex;align-items:center;gap:7px;padding:6px 14px;background:var(--orange-glow);border:1px solid rgba(255,87,34,.22);color:var(--orange);border-radius:20px;font-size:12px;font-weight:700;margin-bottom:22px;letter-spacing:.3px;}
   223|.hero-badge .pulse{width:7px;height:7px;background:var(--orange);border-radius:50%;animation:blink 2s infinite;}
   224|@keyframes blink{0%,100%{opacity:1;}50%{opacity:.3;}}
   225|.hero h1{font-size:52px;line-height:1.07;font-weight:900;letter-spacing:-2.5px;margin-bottom:20px;}
   226|.hero h1 .hl{color:var(--orange);}
   227|.hero p{font-size:17px;color:var(--muted);line-height:1.72;margin-bottom:36px;max-width:460px;}
   228|.btn-hero{display:inline-flex;align-items:center;gap:8px;padding:16px 36px;background:var(--orange);color:#fff;text-decoration:none;border-radius:var(--r);font-size:16px;font-weight:700;box-shadow:0 8px 24px rgba(255,87,34,.3);transition:all .2s;width:fit-content;}
   229|.btn-hero:hover{background:var(--orange-dark);transform:translateY(-2px);box-shadow:0 12px 32px rgba(255,87,34,.4);}
   230|.hero-fine{margin-top:14px;font-size:13px;color:var(--light);display:flex;flex-wrap:wrap;gap:16px;}
   231|.hero-fine span{display:flex;align-items:center;gap:5px;}
   232|
   233|/* HERO VISUAL */
   234|.hero-visual{position:relative;}
   235|.mock-card{background:#fff;border-radius:var(--r-lg);box-shadow:var(--sh-lg);border:1px solid var(--border);overflow:hidden;}
   236|.mock-header{background:var(--dark);padding:13px 18px;display:flex;align-items:center;gap:10px;}
   237|.dots span{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;}
   238|.d-r{background:#FF5F57;}.d-y{background:#FEBC2E;}.d-g{background:#28C840;}
   239|.mock-title{color:#8B949E;font-size:12px;font-weight:500;margin-left:4px;}
   240|.mock-live{margin-left:auto;font-size:11px;color:var(--green);font-weight:600;display:flex;align-items:center;gap:4px;}
   241|.mock-live::before{content:"●";font-size:8px;animation:blink 1.5s infinite;}
   242|.mock-body{padding:16px;}
   243|.notif-strip{display:flex;gap:10px;align-items:flex-start;background:linear-gradient(135deg,#ECFDF5,#F0FFF4);border:1px solid #A7F3D0;border-radius:10px;padding:12px 14px;margin-bottom:14px;}
   244|.notif-strip .ni{font-size:18px;}
   245|.notif-strip .nt{font-size:12px;font-weight:700;color:var(--green-text);}
   246|.notif-strip .nd{font-size:11px;color:#374151;margin-top:2px;line-height:1.5;}
   247|.chat-win{border:1px solid var(--border);border-radius:10px;overflow:hidden;background:#F9FAFB;}
   248|.chat-top{background:#fff;padding:10px 14px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:8px;}
   249|.chat-av{width:28px;height:28px;background:var(--orange-glow);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;}
   250|.chat-inf .cn{font-size:12px;font-weight:600;color:var(--text);}
   251|.chat-inf .cp{font-size:10px;color:var(--light);}
   252|.chat-status-badge{margin-left:auto;font-size:10px;color:var(--green);font-weight:600;background:var(--green-bg);padding:2px 8px;border-radius:10px;}
   253|.msgs{padding:12px;display:flex;flex-direction:column;gap:8px;}
   254|.mb{max-width:86%;}.mb-bot{align-self:flex-start;}.mb-usr{align-self:flex-end;}
   255|.mn{font-size:10px;color:var(--light);font-weight:600;margin-bottom:3px;}
   256|.mb-usr .mn{text-align:right;}
   257|.bub{padding:8px 12px;border-radius:12px;font-size:12px;line-height:1.5;}
   258|.bub-bot{background:#fff;border:1px solid var(--border);color:var(--text);border-bottom-left-radius:3px;}
   259|.bub-usr{background:var(--orange);color:#fff;border-bottom-right-radius:3px;}
   260|.chat-foot{background:#fff;padding:9px 14px;border-top:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;}
   261|.cf-ok{font-size:10px;color:var(--green);font-weight:600;}
   262|.cf-time{font-size:10px;color:var(--light);}
   263|.float-b{position:absolute;background:#fff;border-radius:10px;box-shadow:var(--sh);padding:8px 12px;display:flex;align-items:center;gap:7px;font-size:12px;font-weight:600;color:var(--text);border:1px solid var(--border);white-space:nowrap;}
   264|.fb1{top:-16px;right:-12px;animation:fl 3s ease-in-out infinite;}
   265|.fb2{bottom:-14px;left:-14px;animation:fl 3s ease-in-out infinite 1.5s;}
   266|@keyframes fl{0%,100%{transform:translateY(0);}50%{transform:translateY(-5px);}}
   267|
   268|/* TRUST BAR */
   269|.trust-bar{background:var(--dark);padding:16px 40px;}
   270|.trust-bar-inner{max-width:1160px;margin:0 auto;display:flex;justify-content:center;align-items:center;gap:40px;flex-wrap:wrap;}
   271|.ti{display:flex;align-items:center;gap:7px;color:#8B949E;font-size:13px;font-weight:500;}
   272|.ti strong{color:#E6EDF3;}
   273|.tdiv{width:1px;height:18px;background:#30363D;}
   274|
   275|/* SECTION COMMON */
   276|.sec-label{display:inline-block;font-size:11px;font-weight:700;color:var(--orange);letter-spacing:1.8px;text-transform:uppercase;margin-bottom:10px;}
   277|.sec-h2{font-size:36px;font-weight:900;letter-spacing:-1.2px;line-height:1.12;margin-bottom:12px;}
   278|.sec-sub{font-size:16px;color:var(--muted);line-height:1.68;max-width:540px;}
   279|
   280|/* DEMO */
   281|.demo{padding:80px 40px;background:#fff;}
   282|.demo-inner{max-width:1160px;margin:0 auto;display:grid;grid-template-columns:1fr 1fr;gap:64px;align-items:start;}
   283|.demo-stats{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:28px;}
   284|.ds-card{background:var(--bg);border-radius:var(--r);padding:20px;border:1px solid var(--border);}
   285|.ds-num{font-size:32px;font-weight:900;letter-spacing:-1px;color:var(--text);}
   286|.ds-num .u{font-size:16px;font-weight:600;color:var(--muted);}
   287|.ds-lbl{font-size:13px;color:var(--muted);margin-top:4px;line-height:1.4;}
   288|.convo-card{background:var(--bg);border-radius:var(--r-lg);overflow:hidden;border:1px solid var(--border);box-shadow:var(--sh);}
   289|.convo-hdr{background:var(--dark);padding:13px 18px;display:flex;align-items:center;justify-content:space-between;}
   290|.convo-title{color:#8B949E;font-size:12px;margin-left:8px;}
   291|.convo-live{font-size:11px;color:var(--green);font-weight:600;display:flex;align-items:center;gap:4px;}
   292|.convo-live::before{content:"●";font-size:8px;animation:blink 1.5s infinite;}
   293|.convo-body{padding:20px;display:flex;flex-direction:column;gap:14px;}
   294|.cm{display:flex;gap:10px;}.cm-r{flex-direction:row-reverse;}
   295|.ca{width:32px;height:32px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:15px;}
   296|.ca-bot{background:linear-gradient(135deg,var(--orange-glow),#FFF5F0);border:1px solid rgba(255,87,34,.2);}
   297|.ca-usr{background:#EFF6FF;border:1px solid #DBEAFE;}
   298|.cb{max-width:78%;}
   299|.cname{font-size:10px;color:var(--light);font-weight:600;margin-bottom:3px;letter-spacing:.3px;}
   300|.cm-r .cname{text-align:right;}
   301|.ct{padding:10px 14px;border-radius:14px;font-size:13px;line-height:1.55;}
   302|.ct-bot{background:#fff;border:1px solid var(--border);border-top-left-radius:3px;}
   303|.ct-usr{background:#1E3A5F;color:#fff;border-top-right-radius:3px;}
   304|.convo-result{margin:0 20px 20px;padding:12px 16px;background:linear-gradient(135deg,var(--green-bg),#F0FFF4);border:1px solid #A7F3D0;border-radius:10px;display:flex;align-items:center;gap:10px;}
   305|.cr-icon{font-size:20px;}
   306|.cr-title{font-size:13px;font-weight:700;color:var(--green-text);}
   307|.cr-detail{font-size:11px;color:#374151;margin-top:2px;}
   308|
   309|/* PAIN */
   310|.pain{padding:72px 40px;background:var(--dark);}
   311|.pain-inner{max-width:1060px;margin:0 auto;text-align:center;}
   312|.pain h2{font-size:36px;font-weight:900;color:#E6EDF3;letter-spacing:-1px;margin-bottom:10px;}
   313|.pain-sub{font-size:16px;color:#8B949E;margin-bottom:52px;}
   314|.pain-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;}
   315|.pc{background:var(--dark-card);border-radius:var(--r);padding:32px 24px;border:1px solid #30363D;transition:border-color .2s;}
   316|.pc:hover{border-color:var(--orange);}
   317|.pn{font-size:46px;font-weight:900;letter-spacing:-2px;line-height:1;margin-bottom:10px;}
   318|.pn.red{color:#FF5F57;}.pn.yellow{color:#FEBC2E;}.pn.blue{color:#58A6FF;}
   319|.pl{font-size:14px;color:#8B949E;line-height:1.6;}
   320|
   321|/* COMPARE */
   322|.compare{padding:80px 40px;background:#fff;}
   323|.compare-inner{max-width:920px;margin:0 auto;}
   324|.compare-hdr{text-align:center;margin-bottom:48px;}
   325|.ct-table{width:100%;border-collapse:separate;border-spacing:0;border-radius:var(--r);overflow:hidden;box-shadow:var(--sh);border:1px solid var(--border);}
   326|.ct-table th,.ct-table td{padding:14px 20px;font-size:14px;text-align:left;}
   327|.ct-table tr:not(:last-child) td,.ct-table tr:not(:last-child) th{border-bottom:1px solid var(--border);}
   328|.ct-table th{padding:16px 20px;font-weight:700;font-size:12px;text-transform:uppercase;letter-spacing:.5px;}
   329|.ct-table th:first-child{background:var(--bg2);color:var(--muted);}
   330|.ct-table th:nth-child(2){background:#FFF1F0;color:#9B1C1C;}
   331|.ct-table th:nth-child(3){background:#F0FDF4;color:#14532D;}
   332|.ct-table td:first-child{font-weight:600;color:var(--text);background:var(--bg);font-size:13px;}
   333|.ct-table td:nth-child(2){background:#fff;color:var(--muted);font-size:13px;}
   334|.ct-table td:nth-child(3){background:#fff;color:#374151;font-weight:500;font-size:13px;}
   335|.ct-table tr:hover td{background:#FAFAF8!important;}
   336|.td-bad{color:#EF4444!important;}.td-good{color:var(--green)!important;font-weight:600!important;}
   337|.compare-callout{margin-top:24px;background:linear-gradient(135deg,var(--green-bg),#F0FFF4);border:1px solid #A7F3D0;border-radius:var(--r);padding:20px 28px;text-align:center;}
   338|.compare-callout strong{font-size:22px;color:var(--green-text);font-weight:800;}
   339|.compare-callout p{font-size:14px;color:#374151;margin-top:4px;}
   340|
   341|/* FEATURES */
   342|.features{padding:80px 40px;background:var(--bg);}
   343|.features-inner{max-width:1160px;margin:0 auto;}
   344|.feat-hdr{text-align:center;margin-bottom:52px;}
   345|.feat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;}
   346|.fc{background:#fff;padding:28px;border-radius:var(--r);border:1px solid var(--border);transition:all .2s;}
   347|.fc:hover{transform:translateY(-4px);box-shadow:var(--sh-lg);border-color:rgba(255,87,34,.2);}
   348|.fic{width:48px;height:48px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:22px;margin-bottom:16px;}
   349|.fi-o{background:linear-gradient(135deg,#FFF5F0,#FFE8DF);}
   350|.fi-g{background:linear-gradient(135deg,#ECFDF5,#D1FAE5);}
   351|.fi-b{background:linear-gradient(135deg,#EFF6FF,#DBEAFE);}
   352|.fi-p{background:linear-gradient(135deg,#F5F3FF,#EDE9FE);}
   353|.fi-pk{background:linear-gradient(135deg,#FDF2F8,#FCE7F3);}
   354|.fi-t{background:linear-gradient(135deg,#F0FDFA,#CCFBF1);}
   355|.fc h3{font-size:16px;font-weight:700;margin-bottom:8px;}
   356|.fc p{font-size:13px;color:var(--muted);line-height:1.6;}
   357|
   358|/* HOW */
   359|.how{padding:80px 40px;background:#fff;}
   360|.how-inner{max-width:960px;margin:0 auto;}
   361|.how-hdr{text-align:center;margin-bottom:56px;}
   362|.how-steps{display:grid;grid-template-columns:repeat(3,1fr);gap:40px;position:relative;}
   363|.how-steps::before{content:"";position:absolute;top:26px;left:calc(16.66% + 26px);right:calc(16.66% + 26px);height:2px;background:linear-gradient(90deg,var(--orange),rgba(255,87,34,.2));z-index:0;}
   364|.hs{text-align:center;position:relative;z-index:1;}
   365|.hn{width:52px;height:52px;border-radius:50%;font-size:20px;font-weight:800;display:flex;align-items:center;justify-content:center;margin:0 auto 20px;background:linear-gradient(135deg,var(--orange),#FF7043);color:#fff;box-shadow:0 8px 20px rgba(255,87,34,.3);}
   366|.hs h3{font-size:17px;font-weight:700;margin-bottom:8px;}
   367|.hs p{font-size:14px;color:var(--muted);line-height:1.6;}
   368|.how-cta{text-align:center;margin-top:48px;}
   369|
   370|/* PRICING */
   371|.pricing{padding:80px 40px;background:var(--bg);}
   372|.pricing-inner{max-width:960px;margin:0 auto;}
   373|.price-hdr{text-align:center;margin-bottom:48px;}
   374|.plans-row{display:grid;grid-template-columns:1fr 1fr;gap:24px;max-width:760px;margin:0 auto 28px;}
   375|.price-card{background:#fff;border:2px solid var(--border);border-radius:var(--r-lg);padding:36px 32px;position:relative;transition:all .2s;}
   376|.price-card:hover{box-shadow:var(--sh-lg);}
   377|.price-card.pop{border-color:var(--orange);box-shadow:0 8px 32px rgba(255,87,34,.12);}
   378|.pop-badge{position:absolute;top:-13px;left:50%;transform:translateX(-50%);background:var(--orange);color:#fff;padding:4px 18px;border-radius:20px;font-size:11px;font-weight:700;white-space:nowrap;letter-spacing:.5px;}
   379|.pname{font-size:18px;font-weight:800;margin-bottom:2px;}
   380|.pdesc{font-size:13px;color:var(--muted);margin-bottom:20px;}
   381|.pamt{font-size:48px;font-weight:900;color:var(--text);line-height:1;letter-spacing:-2px;}
   382|.pamt .cur{font-size:22px;font-weight:700;vertical-align:top;margin-top:9px;display:inline-block;letter-spacing:0;}
   383|.pamt .per{font-size:15px;color:var(--muted);font-weight:500;letter-spacing:0;}
   384|.ptrial{display:inline-block;margin:12px 0 24px;padding:4px 14px;background:var(--green-bg);color:var(--green-text);border-radius:20px;font-size:12px;font-weight:600;}
   385|.pfeats{list-style:none;display:flex;flex-direction:column;gap:10px;margin-bottom:28px;}
   386|.pfeats li{font-size:14px;color:#374151;display:flex;align-items:flex-start;gap:10px;}
   387|.pfeats li .ck{color:var(--green);font-size:16px;flex-shrink:0;}
   388|.pfeats li.dm{color:var(--light);}
   389|.pfeats li.dm .dash{color:var(--border);flex-shrink:0;}
   390|.btn-price{display:block;width:100%;padding:14px;text-align:center;background:var(--orange);color:#fff;text-decoration:none;border-radius:10px;font-size:15px;font-weight:700;border:none;cursor:pointer;transition:all .2s;}
   391|.btn-price:hover{background:var(--orange-dark);transform:translateY(-1px);box-shadow:0 6px 16px rgba(255,87,34,.3);}
   392|.btn-outline{background:#fff;color:var(--orange);border:2px solid var(--orange);}
   393|.btn-outline:hover{background:#FFF5F0;box-shadow:0 4px 12px rgba(255,87,34,.15);}
   394|.roi-box{max-width:560px;margin:4px auto 0;background:linear-gradient(135deg,var(--green-bg),#F0FFF4);border:1px solid #A7F3D0;border-radius:var(--r);padding:24px 28px;}
   395|.roi-box h3{font-size:15px;font-weight:700;color:var(--green-text);margin-bottom:14px;}
   396|.roi-t{width:100%;font-size:13px;border-collapse:collapse;margin-bottom:12px;}
   397|.roi-t td{padding:7px 0;color:#374151;}
   398|.roi-t td:nth-child(2),.roi-t td:nth-child(3){text-align:right;}
   399|.roi-t .save td{font-weight:800;color:var(--green-text);font-size:15px;border-top:2px solid #A7F3D0;padding-top:12px;}
   400|.roi-note{font-size:13px;color:var(--muted);line-height:1.55;font-style:italic;}
   401|
   402|/* VIDEO DEMO SECTION */
   403|.video-demo-section{padding:80px 40px;background:#fff;}
   404|.video-demo-inner{max-width:860px;margin:0 auto;text-align:center;}
   405|.video-demo-hdr{margin-bottom:36px;}
   406|.video-wrap{position:relative;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:16px;box-shadow:0 8px 40px rgba(0,0,0,.12);border:1px solid var(--border);}
   407|.video-frame{position:absolute;top:0;left:0;width:100%;height:100%;border:0;border-radius:16px;}
   408|.video-caption{font-size:13px;color:var(--light);margin-top:16px;}
   409|.video-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:36px;}
   410|
   411|/* FAQ */
   412|.faq{padding:80px 40px;background:#fff;}
   413|.faq-inner{max-width:720px;margin:0 auto;}
   414|.faq-hdr{text-align:center;margin-bottom:48px;}
   415|.faq-list details{border-bottom:1px solid var(--border);}
   416|.faq-list summary{padding:18px 0;font-size:15px;font-weight:600;color:var(--text);cursor:pointer;list-style:none;display:flex;justify-content:space-between;align-items:center;transition:color .15s;}
   417|.faq-list summary:hover{color:var(--orange);}
   418|.faq-list summary::after{content:"+";font-size:22px;color:var(--light);font-weight:400;flex-shrink:0;transition:all .2s;}
   419|.faq-list details[open] summary::after{content:"\2212";color:var(--orange);}
   420|.faq-list summary::-webkit-details-marker{display:none;}
   421|.faq-list .fb{padding:0 0 18px;font-size:14px;color:var(--muted);line-height:1.7;}
   422|
   423|/* FINAL CTA */
   424|.final-cta{padding:80px 40px;background:linear-gradient(135deg,var(--orange) 0%,#FF8A65 100%);text-align:center;position:relative;overflow:hidden;}
   425|.final-cta::before{content:"";position:absolute;top:-80px;left:-80px;width:300px;height:300px;background:rgba(255,255,255,.06);border-radius:50%;}
   426|.final-cta::after{content:"";position:absolute;bottom:-60px;right:-60px;width:240px;height:240px;background:rgba(255,255,255,.06);border-radius:50%;}
   427|.final-cta-inner{max-width:640px;margin:0 auto;position:relative;z-index:1;}
   428|.final-cta h2{color:#fff;font-size:36px;font-weight:900;letter-spacing:-1px;margin-bottom:14px;line-height:1.15;}
   429|.final-cta p{color:rgba(255,255,255,.85);font-size:16px;margin-bottom:32px;line-height:1.65;}
   430|.btn-final{display:inline-flex;align-items:center;gap:8px;padding:17px 44px;background:#fff;color:var(--orange);text-decoration:none;border-radius:var(--r);font-size:17px;font-weight:800;transition:all .2s;box-shadow:0 8px 24px rgba(0,0,0,.15);}
   431|.btn-final:hover{background:#FFF5F0;transform:translateY(-2px);box-shadow:0 12px 32px rgba(0,0,0,.2);}
   432|.final-sub{margin-top:14px;color:rgba(255,255,255,.7);font-size:14px;}
   433|.final-sub a{color:rgba(255,255,255,.9);text-decoration:underline;}
   434|
   435|/* FOOTER */
   436|.footer{background:var(--dark);padding:52px 40px 32px;}
   437|.footer-inner{max-width:1160px;margin:0 auto;display:flex;justify-content:space-between;flex-wrap:wrap;gap:40px;margin-bottom:40px;}
   438|.footer-logo{font-size:20px;font-weight:800;color:#fff;text-decoration:none;letter-spacing:-.5px;display:inline-flex;align-items:center;gap:8px;}
   439|.footer-logo span{color:var(--orange);}
   440|.footer-logo-icon{width:28px;height:28px;flex-shrink:0;}
   441|.footer-tag{font-size:13px;color:#8B949E;margin-top:6px;}
   442|.fcol h4{color:#E6EDF3;font-size:13px;font-weight:700;margin-bottom:14px;letter-spacing:.3px;}
   443|.fcol a{display:block;color:#8B949E;text-decoration:none;font-size:13px;padding:4px 0;transition:color .15s;}
   444|.fcol a:hover{color:#E6EDF3;}
   445|.footer-bot{max-width:1160px;margin:0 auto;padding-top:24px;border-top:1px solid #21262D;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;}
   446|.footer-bot p{font-size:12px;color:#6E7681;}
   447|
   448|/* RESPONSIVE */
   449|@media(max-width:900px){
   450|  .nav-inner{padding:12px 20px;}
   451|  .nav-links{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:#FAFAF8;flex-direction:column;justify-content:center;align-items:center;gap:4px;z-index:999;padding:80px 24px 40px;padding-top:max(80px, calc(60px + env(safe-area-inset-top)));}
   452|  .nav-links.open{display:flex;}
   453|  .nav-links a{font-size:20px;padding:14px 32px;border-radius:12px;width:100%;max-width:280px;text-align:center;}
   454|  .nav-links .btn-nav{margin-top:12px;width:100%;max-width:280px;text-align:center;}
   455|  .nav-toggle{display:flex;z-index:1001;position:relative;}
   456|
   457|  /* Hero */
   458|  .hero{padding:40px 20px 52px;}
   459|  .hero-inner{grid-template-columns:1fr;gap:32px;}
   460|  .hero h1{font-size:36px;letter-spacing:-1.5px;}
   461|  .hero p{font-size:15px;max-width:100%;}
   462|  .btn-hero{padding:14px 28px;font-size:15px;}
   463|  .float-b{display:none;}
   464|  .hero-visual{display:none;}
   465|
   466|  /* Trust */
   467|  .trust-bar{padding:12px 20px;}
   468|  .trust-bar-inner{gap:14px;justify-content:flex-start;}
   469|  .tdiv{display:none;}
   470|  .ti{font-size:12px;}
   471|
   472|  /* Video */
   473|  .video-demo-section{padding:48px 20px;}
   474|  .video-stats{grid-template-columns:repeat(2,1fr);}
   475|
   476|  /* Pain */
   477|  .pain{padding:52px 20px;}
   478|  .pain h2{font-size:28px;}
   479|  .pain-grid{grid-template-columns:1fr;gap:14px;max-width:380px;margin:0 auto;}
   480|
   481|  /* Compare */
   482|  .compare{padding:52px 20px;}
   483|  .compare-inner{overflow-x:auto;}
   484|  .ct-table{font-size:12px;min-width:460px;}
   485|  .ct-table th,.ct-table td{padding:10px 11px;}
   486|
   487|  /* Features */
   488|  .features{padding:52px 20px;}
   489|  .feat-grid{grid-template-columns:repeat(2,1fr);}
   490|
   491|  /* Social proof */
   492|  .social-proof{padding:48px 20px;}
   493|  .sp-cards{grid-template-columns:1fr;}
   494|
   495|  /* How */
   496|  .how{padding:52px 20px;}
   497|  .how-steps{grid-template-columns:1fr;gap:28px;max-width:340px;margin:0 auto;}
   498|  .how-steps::before{display:none;}
   499|
   500|  /* Pricing */
   501|  .pricing{padding:52px 20px;}
   502|  .plans-row{grid-template-columns:1fr;max-width:400px;margin-left:auto;margin-right:auto;}
   503|  .price-card{padding:28px 24px;}
   504|  .pamt{font-size:40px;}
   505|  .roi-box{padding:20px;}
   506|
   507|  /* FAQ */
   508|  .faq{padding:52px 20px;}
   509|
   510|  /* Final CTA */
   511|  .final-cta{padding:52px 20px;}
   512|  .final-cta h2{font-size:26px;}
   513|  .btn-final{padding:14px 32px;font-size:15px;}
   514|
   515|  /* Footer */
   516|  .footer{padding:40px 20px 24px;}
   517|  .footer-inner{gap:28px;}
   518|  .footer-bot{flex-direction:column;text-align:center;}
   519|
   520|  /* Contact */
   521|  .contact-section{padding:48px 20px;}
   522|
   523|  /* Misc */
   524|  .sec-h2{font-size:28px;}
   525|  .sec-sub{font-size:15px;}
   526|}
   527|
   528|@media(max-width:480px){
   529|  .hero{padding:32px 16px 44px;}
   530|  .hero h1{font-size:30px;letter-spacing:-1px;}
   531|  .hero-badge{font-size:11px;}
   532|  .btn-hero{width:100%;justify-content:center;padding:15px 20px;}
   533|  .hero-fine{font-size:12px;gap:12px;}
   534|
   535|  .trust-bar{padding:10px 16px;}
   536|  .trust-bar-inner{gap:10px;}
   537|
   538|  .video-demo-section{padding:40px 16px;}
   539|  .video-stats{grid-template-columns:repeat(2,1fr);gap:10px;}
   540|
   541|  .pain{padding:44px 16px;}
   542|  .pn{font-size:36px;}
   543|
   544|  .compare{padding:44px 16px;}
   545|
   546|  .features{padding:44px 16px;}
   547|  .feat-grid{grid-template-columns:1fr;}
   548|  .fc{padding:22px 18px;}
   549|
   550|  .social-proof{padding:40px 16px;}
   551|
   552|  .how{padding:44px 16px;}
   553|
   554|  .pricing{padding:44px 16px;}
   555|  .price-card{padding:24px 18px;}
   556|  .pamt{font-size:36px;}
   557|  .btn-price{padding:13px;}
   558|
   559|  .faq{padding:44px 16px;}
   560|  .faq-list summary{font-size:14px;}
   561|
   562|  .final-cta{padding:44px 16px;}
   563|  .final-cta h2{font-size:24px;}
   564|  .btn-final{width:100%;justify-content:center;padding:15px 20px;}
   565|
   566|  .footer{padding:32px 16px 20px;}
   567|  .contact-section{padding:40px 16px;}
   568|  .contact-form .row{flex-direction:column;}
   569|
   570|  .sec-h2{font-size:24px;}
   571|  .ds-card{padding:16px 12px;}
   572|  .ds-num{font-size:26px;}
   573|}
   574|
   575|/* Social proof */
   576|.social-proof{padding:64px 40px;background:#fff;border-top:1px solid var(--border);border-bottom:1px solid var(--border);}
   577|.sp-inner{max-width:1000px;margin:0 auto;text-align:center;}
   578|.sp-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin-top:32px;}
   579|.sp-card{padding:28px;background:var(--bg);border-radius:var(--r);border:1px solid var(--border);}
   580|.sp-card .sp-icon{font-size:32px;margin-bottom:12px;}
   581|.sp-card h3{font-size:16px;font-weight:700;color:var(--text);margin-bottom:6px;}
   582|.sp-card p{font-size:14px;color:var(--muted);line-height:1.6;}
   583|@media(max-width:700px){.sp-cards{grid-template-columns:1fr;}}
   584|
   585|/* Contact form */
   586|.contact-section{padding:64px 40px;background:var(--bg2);}
   587|.contact-inner{max-width:560px;margin:0 auto;}
   588|.contact-inner h2{font-size:28px;font-weight:800;letter-spacing:-0.5px;text-align:center;margin-bottom:8px;}
   589|.contact-sub{text-align:center;color:var(--muted);font-size:15px;margin-bottom:28px;}
   590|.contact-form{display:flex;flex-direction:column;gap:14px;}
   591|.contact-form input,.contact-form textarea{padding:12px 14px;border:1.5px solid var(--border);border-radius:10px;font-size:15px;font-family:inherit;background:#fff;}
   592|.contact-form input:focus,.contact-form textarea:focus{outline:none;border-color:var(--orange);box-shadow:0 0 0 3px rgba(255,87,34,.1);}
   593|.contact-form textarea{min-height:100px;resize:vertical;}
   594|.contact-form .row{display:flex;gap:14px;}
   595|.contact-form .row input{flex:1;}
   596|.btn-contact{padding:14px;background:var(--orange);color:#fff;border:none;border-radius:10px;font-size:16px;font-weight:700;cursor:pointer;transition:all .2s;font-family:inherit;}
   597|.btn-contact:hover{background:var(--orange-dark);}
   598|.btn-contact:disabled{opacity:.6;cursor:not-allowed;}
   599|.contact-msg{text-align:center;margin-top:12px;font-size:14px;color:#059669;display:none;}
   600|@media(max-width:600px){.contact-form .row{flex-direction:column;}}
   601|
   602|/* Founders banner */
   603|.founders-banner{background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);padding:14px 40px;text-align:center;position:relative;overflow:hidden;}
   604|.founders-banner::before{content:"";position:absolute;top:0;left:0;right:0;bottom:0;background:linear-gradient(90deg,transparent,rgba(255,87,34,.06),transparent);animation:shimmer 3s infinite;}
   605|@keyframes shimmer{0%{transform:translateX(-100%);}100%{transform:translateX(100%);}}
   606|.fb-inner{max-width:800px;margin:0 auto;display:flex;align-items:center;justify-content:center;gap:16px;flex-wrap:wrap;}
   607|.fb-badge{background:var(--orange);color:#fff;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:800;letter-spacing:.5px;white-space:nowrap;animation:pulse-glow 2s infinite;}
   608|@keyframes pulse-glow{0%,100%{box-shadow:0 0 8px rgba(255,87,34,.4);}50%{box-shadow:0 0 16px rgba(255,87,34,.7);}}
   609|.fb-text{color:#E6EDF3;font-size:14px;font-weight:500;}
   610|.fb-text strong{color:#fff;font-weight:700;}
   611|.fb-text .fb-price{color:var(--orange);font-weight:800;}
   612|.fb-slots{color:#FEBC2E;font-size:13px;font-weight:700;white-space:nowrap;}
   613|@media(max-width:600px){.founders-banner{padding:12px 20px;}.fb-inner{gap:8px;}.fb-text{font-size:13px;}}
   614|
   615|/* WhatsApp floating button */
   616|.wa-float{position:fixed;bottom:24px;right:24px;z-index:999;width:56px;height:56px;background:#25D366;border-radius:50%;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 16px rgba(37,211,102,.4);transition:transform .2s;text-decoration:none;}
   617|.wa-float:hover{transform:scale(1.1);}
   618|.wa-float svg{width:28px;height:28px;fill:#fff;}
   619|
   620|/* Demo call floating button */
   621|.demo-call-float{position:fixed;bottom:90px;right:24px;z-index:999;display:flex;align-items:center;gap:8px;padding:12px 20px;background:#FF5722;color:#fff;border-radius:28px;font-size:14px;font-weight:700;text-decoration:none;box-shadow:0 4px 20px rgba(255,87,34,.4);transition:transform .2s;font-family:'Inter',sans-serif;}
   622|.demo-call-float:hover{transform:scale(1.05);box-shadow:0 6px 28px rgba(255,87,34,.5);}
   623|.demo-call-float svg{flex-shrink:0;}
   624|.dcf-pulse{position:absolute;top:-4px;right:-4px;width:12px;height:12px;background:#4CAF50;border-radius:50%;border:2px solid #fff;}
   625|.dcf-pulse::after{content:'';position:absolute;top:-3px;left:-3px;width:12px;height:12px;background:#4CAF50;border-radius:50%;animation:dcfPulse 2s infinite;}
   626|@keyframes dcfPulse{0%{transform:scale(1);opacity:.7;}100%{transform:scale(2.2);opacity:0;}}
   627|@media(max-width:480px){.demo-call-float span.dcf-txt{display:none;}.demo-call-float{padding:14px;border-radius:50%;}}
   628|</style>
   629|</head>
   630|<body>
   631|
   632|<!-- NAV -->
   633|<nav class="nav" id="nav">
   634|<div class="nav-inner">
   635|  <a class="nav-logo" href="/">
   636|    <svg class="nav-logo-icon" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
   637|      <rect width="32" height="32" rx="8" fill="#FF5722"/>
   638|      <path d="M16 5 L27 15 L23 15 L23 27 L9 27 L9 15 L5 15 Z" fill="white"/>
   639|      <rect x="12.5" y="19" width="7" height="8" rx="1.5" fill="#FF5722"/>
   640|      <circle cx="24.5" cy="8" r="1.8" fill="white" opacity="0.9"/>
   641|      <path d="M26.2 5.8 Q29 8 26.2 10.2" stroke="white" stroke-width="1.5" fill="none" stroke-linecap="round" opacity="0.85"/>
   642|    </svg>
   643|    <span>Prop</span>Bot
   644|  </a>
   645|  <button class="nav-toggle" id="ntog" aria-label="Menu">
   646|    <span></span><span></span><span></span>
   647|  </button>
   648|  <div class="nav-links" id="nlinks">
   649|    <a href="#how">How It Works</a>
   650|    <a href="#pricing">Pricing</a>
   651|    <a href="#faq">FAQ</a>
   652|    <a href="#contact">Contact</a>
   653|    <a href="/dashboard">Login</a>
   654|    <a href="https://cal.com/atharva-realestate/real-estate-ai-demo" target="_blank" class="btn-nav">Book AI Demo &rarr;</a>
   655|  </div>
   656|</div>
   657|</nav>
   658|
   659|<!-- HERO -->
   660|<section class="hero">
   661|<div class="hero-inner">
   662|  <div>
   663|    <div class="hero-badge"><span class="pulse"></span> AI Receptionist for Indian Real Estate</div>
   664|    <h1>Never Miss a Lead.<br><span class="hl">Even at 2 AM.</span></h1>
   665|    <p>PropBot answers every call in Hindi, English, and Hinglish &mdash; 24/7. Qualifies buyers, books site visits, captures leads. All while you sleep.</p>
   666|    <a href="/signup" class="btn-hero">Start Free 14-Day Trial &rarr;</a>
   667|    <div class="hero-fine">
   668|      <span>&#10003; No credit card</span>
   669|      <span>&#10003; Live in 5 minutes</span>
   670|      <span>&#10003; Cancel anytime</span>
   671|    </div>
   672|  </div>
   673|  <div class="hero-visual">
   674|    <div class="float-b fb1">&#128276; New lead: Suresh M. &middot; 3BHK &middot; &#8377;65L</div>
   675|    <div class="mock-card">
   676|      <div class="mock-header">
   677|        <div class="dots"><span class="d-r"></span><span class="d-y"></span><span class="d-g"></span></div>
   678|        <span class="mock-title">PropBot &mdash; Live Call &middot; 2:17 AM</span>
   679|        <div class="mock-live">LIVE</div>
   680|      </div>
   681|      <div class="mock-body">
   682|        <div class="notif-strip">
   683|          <div class="ni">&#9989;</div>
   684|          <div>
   685|            <div class="nt">Lead Captured</div>
   686|            <div class="nd">Rajesh Kumar &middot; +91 98765 43210<br>2BHK &middot; Noida Sec 62 &middot; Budget &#8377;45&ndash;55L</div>
   687|          </div>
   688|        </div>
   689|        <div class="chat-win">
   690|          <div class="chat-top">
   691|            <div class="chat-av">&#129302;</div>
   692|            <div class="chat-inf">
   693|              <div class="cn">PropBot &mdash; Priya</div>
   694|              <div class="cp">+91 99887 76655 calling</div>
   695|            </div>
   696|            <div class="chat-status-badge">&#9679; LIVE</div>
   697|          </div>
   698|          <div class="msgs">
   699|            <div class="mb mb-bot">
   700|              <div class="mn">Priya &middot; PropBot AI</div>
   701|              <div class="bub bub-bot">Namaste! Main Priya hoon. Aap kaunsi property dhundh rahe hain? &#128591;</div>
   702|            </div>
   703|            <div class="mb mb-usr">
   704|              <div class="mn">Caller</div>
   705|              <div class="bub bub-usr">2BHK chahiye, Noida Sector 62, budget 45&ndash;50 lakh</div>
   706|            </div>
   707|            <div class="mb mb-bot">
   708|              <div class="mn">Priya &middot; PropBot AI</div>
   709|              <div class="bub bub-bot">Perfect! Sector 62 mein ek 2BHK hai &mdash; 1200 sqft, &#8377;48L. Kya aaj site visit schedule karein? &#128197;</div>
   710|            </div>
   711|          </div>
   712|          <div class="chat-foot">
   713|            <div class="cf-ok">&#10003; Site visit booked for tomorrow</div>
   714|            <div class="cf-time">2:17 AM</div>
   715|          </div>
   716|        </div>
   717|      </div>
   718|    </div>
   719|    <div class="float-b fb2">&#9889; Response time: &lt;1 second</div>
   720|  </div>
   721|</div>
   722|</section>
   723|
   724|<!-- FOUNDERS BANNER -->
   725|<!-- __FOUNDERS_BANNER__ -->
   726|
   727|
   728|<!-- HOW IT WORKS -->
   729|<section class="how" id="how">
   730|<div class="how-inner">
   731|  <div class="how-hdr">
   732|    <div class="sec-label">Setup</div>
   733|    <h2 class="sec-h2">Live in 5 Minutes. Seriously.</h2>
   734|    <p style="color:var(--muted);font-size:16px;margin-top:8px;text-align:center;">No technical skills. No onboarding calls. No waiting.</p>
   735|  </div>
   736|  <div class="how-steps">
   737|    <div class="hs"><div class="hn">1</div><h3>Sign Up &amp; Add Details</h3><p>Your business name, phone, email. Done in 60 seconds. Choose your AI voice from 6 natural Indian options.</p></div>
   738|    <div class="hs"><div class="hn">2</div><h3>Add Your Listings</h3><p>Paste your property details. Your AI instantly learns your entire inventory &mdash; prices, areas, amenities, everything.</p></div>
   739|    <div class="hs"><div class="hn">3</div><h3>Go Live &amp; Close More</h3><p>Get your dedicated number and chat widget. Start receiving AI-handled calls. Check your dashboard. Close deals.</p></div>
   740|  </div>
   741|  <div class="how-cta">
   742|    <a href="https://cal.com/atharva-realestate/real-estate-ai-demo" target="_blank" class="btn-hero">Book Your AI Setup Call &rarr;</a>
   743|  </div>
   744|</div>
   745|</section>
   746|
   747|<!-- PRICING -->
   748|<section class="pricing" id="pricing">
   749|<div class="pricing-inner">
   750|  <div class="price-hdr">
   751|    <div class="sec-label">Pricing</div>
   752|    <h2 class="sec-h2">Simple, Honest Pricing</h2>
   753|    <p style="color:var(--muted);font-size:16px;margin-top:8px;">14-day free trial on both plans. No credit card required.</p>
   754|  </div>
   755|  <div class="plans-row">
   756|    <div class="price-card">
   757|      <div class="pname">Starter</div>
   758|      <div class="pdesc">For solo brokers starting with AI</div>
   759|      <div class="pamt"><!-- __STARTER_PRICE__ --></div>
   760|      <div class="ptrial">14-day free trial</div>
   761|      <ul class="pfeats">
   762|        <li><span class="ck">&#10003;</span> AI voice receptionist (Priya)</li>
   763|        <li><span class="ck">&#10003;</span> Hindi + Hinglish conversations</li>
   764|        <li><span class="ck">&#10003;</span> Lead alerts to your email</li>
   765|        <li><span class="ck">&#10003;</span> Lead &amp; call dashboard</li>
   766|        <li><span class="ck">&#10003;</span> Up to 50 calls / month</li>
   767|        <li class="dm"><span class="dash">&mdash;</span> Chat widget for website</li>
   768|        <li class="dm"><span class="dash">&mdash;</span> Priority support</li>
   769|        <li class="dm"><span style="color:#C4B5FD">&#9670;</span> Outbound follow-up calls <span style="font-size:10px;font-weight:700;color:#7C3AED;background:#EDE9FE;border:1px solid #C4B5FD;border-radius:20px;padding:1px 7px;margin-left:4px;">Coming Soon</span></li>
   770|      </ul>
   771|      <a href="https://cal.com/atharva-realestate/real-estate-ai-demo" target="_blank" class="btn-price btn-outline">Book a Demo</a>
   772|    </div>
   773|    <div class="price-card pop">
   774|      <div class="pop-badge">MOST POPULAR</div>
   775|      <div class="pname">Pro</div>
   776|      <div class="pdesc">For serious brokers who can&rsquo;t miss a lead</div>
   777|      <div class="pamt"><!-- __PRO_PRICE__ --></div>
   778|      <div class="ptrial">14-day free trial</div>
   779|      <ul class="pfeats">
   780|        <li><span class="ck">&#10003;</span> AI voice receptionist (your choice)</li>
   781|        <li><span class="ck">&#10003;</span> Hindi + Hinglish conversations</li>
   782|        <li><span class="ck">&#10003;</span> Lead alerts to your email</li>
   783|        <li><span class="ck">&#10003;</span> Full lead &amp; call dashboard</li>
   784|        <li><span class="ck">&#10003;</span> <strong>Unlimited calls</strong></li>
   785|        <li><span class="ck">&#10003;</span> Chat widget for your website</li>
   786|        <li><span class="ck">&#10003;</span> Priority onboarding support</li>
   787|        <li class="dm"><span style="color:#C4B5FD">&#9670;</span> Outbound follow-up calls <span style="font-size:10px;font-weight:700;color:#7C3AED;background:#EDE9FE;border:1px solid #C4B5FD;border-radius:20px;padding:1px 7px;margin-left:4px;">Coming Soon</span></li>
   788|      </ul>
   789|      <a href="https://cal.com/atharva-realestate/real-estate-ai-demo" target="_blank" class="btn-price">Book a Demo &rarr;</a>
   790|    </div>
   791|  </div>
   792|  <div class="roi-box">
   793|    <h3>Your ROI on the Pro Plan</h3>
   794|    <table class="roi-t">
   795|      <tr><td></td><td><strong>Human Receptionist</strong></td><td><strong>PropBot Pro</strong></td></tr>
   796|      <tr><td>Monthly cost</td><td>&#8377;20,000</td><td>&#8377;4,999</td></tr>
   797|      <tr><td>Annual cost</td><td>&#8377;2,40,000</td><td>&#8377;59,988</td></tr>
   798|      <tr class="save"><td>You save</td><td></td><td>&#8377;1,80,012/year</td></tr>
   799|    </table>
   800|    <p class="roi-note">One deal from a 2 AM missed call pays for PropBot Pro for 3 months. Every missed call is money left on the table.</p>
   801|  </div>
   802|</div>
   803|</section>
   804|
   805|<!-- FAQ -->
   806|<section class="faq" id="faq">
   807|<div class="faq-inner">
   808|  <div class="faq-hdr">
   809|    <div class="sec-label">FAQ</div>
   810|    <h2 class="sec-h2">Questions? We Have Answers.</h2>
   811|  </div>
   812|  <div class="faq-list">
   813|    <details><summary>Will my callers know they&rsquo;re talking to AI?</summary><div class="fb">PropBot uses natural Indian voices that sound remarkably human. Most callers don&rsquo;t realise it&rsquo;s AI. Choose from male and female voices with natural Hindi/English accents.</div></details>
   814|    <details><summary>Does it work in Hindi?</summary><div class="fb">Yes &mdash; fluent Hindi, English, and Hinglish. Understands mixed-language queries naturally, just like how real conversations happen in India. No robotic translation.</div></details>
   815|    <details><summary>What if the caller wants to talk to me directly?</summary><div class="fb">PropBot captures their details and sends you an instant alert. You can also enable callback requests. You&rsquo;re always in control of follow-ups.</div></details>
   816|    <details><summary>How long does setup take?</summary><div class="fb">Under 5 minutes. Sign up, add your property details, pick a voice &mdash; and your AI receptionist is live. No technical skills. No waiting for an onboarding call.</div></details>
   817|    <details><summary>What happens after the 14-day free trial?</summary><div class="fb">Your subscription continues at &#8377;2,499/month (Starter) or &#8377;4,999/month (Pro) via Razorpay. Cancel anytime from the dashboard &mdash; no lock-in, no cancellation fees.</div></details>
   818|    <details><summary>Can I use it with my existing phone number?</summary><div class="fb">PropBot gives you a dedicated phone number. Forward calls from your existing number to it, or share the PropBot number directly with clients &mdash; your choice.</div></details>
   819|    <details><summary>What about the 50 call limit on Starter?</summary><div class="fb">Once you hit 50 calls/month on Starter, PropBot informs callers the line is busy. Upgrade to Pro for unlimited calls anytime from your dashboard.</div></details>
   820|    <details><summary>Is my data safe?</summary><div class="fb">All data is encrypted and stored securely. Call recordings, transcripts, and lead info are only accessible through your dashboard. We never share your data.</div></details>
   821|  </div>
   822|</div>
   823|</section>
   824|
   825|<!-- CONTACT FORM -->
   826|<section class="contact-section" id="contact">
   827|<div class="contact-inner">
   828|  <h2>Have Questions?</h2>
   829|  <p class="contact-sub">Drop us a message and we'll get back to you within hours.</p>
   830|  <form class="contact-form" id="contactForm" onsubmit="return submitContact(event)">
   831|    <div class="row">
   832|      <input name="name" placeholder="Your name" required>
   833|      <input name="phone" placeholder="Phone / WhatsApp" required>
   834|    </div>
   835|    <input name="email" type="email" placeholder="Email (optional)">
   836|    <textarea name="message" placeholder="What would you like to know?" required></textarea>
   837|    <button type="submit" class="btn-contact" id="contactBtn">Send Message</button>
   838|  </form>
   839|  <div class="contact-msg" id="contactMsg">Thanks! We'll get back to you shortly.</div>
   840|</div>
   841|</section>
   842|
   843|<!-- FOOTER -->
   844|<footer class="footer">
   845|<div class="footer-inner">
   846|  <div>
   847|    <a class="footer-logo" href="/">
   848|      <svg class="footer-logo-icon" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
   849|        <rect width="32" height="32" rx="8" fill="#FF5722"/>
   850|        <path d="M16 5 L27 15 L23 15 L23 27 L9 27 L9 15 L5 15 Z" fill="white"/>
   851|        <rect x="12.5" y="19" width="7" height="8" rx="1.5" fill="#FF5722"/>
   852|        <circle cx="24.5" cy="8" r="1.8" fill="white" opacity="0.9"/>
   853|        <path d="M26.2 5.8 Q29 8 26.2 10.2" stroke="white" stroke-width="1.5" fill="none" stroke-linecap="round" opacity="0.85"/>
   854|      </svg>
   855|      <span>Prop</span>Bot
   856|    </a>
   857|    <div class="footer-tag">AI Receptionist for Indian Real Estate</div>
   858|  </div>
   859|  <div class="fcol">
   860|    <h4>Product</h4>
   861|    <a href="#how">How It Works</a>
   862|    <a href="#pricing">Pricing</a>
   863|    <a href="#faq">FAQ</a>
   864|  </div>
   865|  <div class="fcol">
   866|    <h4>Account</h4>
   867|    <a href="https://cal.com/atharva-realestate/real-estate-ai-demo" target="_blank">Book a Demo</a>
   868|    <a href="/admin">Admin Login</a>
   869|    <a href="#faq">FAQ</a>
   870|  </div>
   871|  <div class="fcol">
   872|    <h4>Contact</h4>
   873|    <a href="mailto:daanzack8@gmail.com">daanzack8@gmail.com</a>
   874|    <!-- __WHATSAPP_FOOTER__ -->
   875|    <a href="#contact">Send a Message</a>
   876|  </div>
   877|</div>
   878|<div class="footer-bot">
   879|  <p>&copy; 2026 PropBot. All rights reserved.</p>
   880|  <p>Made with &#10084;&#65039; in India</p>
   881|</div>
   882|</footer>
   883|
   884|<script>
   885|window.addEventListener('scroll',function(){document.getElementById('nav').classList.toggle('scrolled',window.scrollY>10);});
   886|var tog=document.getElementById('ntog'),lnk=document.getElementById('nlinks');
   887|function closeNav(){lnk.classList.remove('open');document.body.style.overflow='';tog.querySelectorAll('span').forEach(function(s){s.style.transform='';s.style.opacity='1';});}
   888|function openNav(){lnk.classList.add('open');document.body.style.overflow='hidden';}
   889|tog.addEventListener('click',function(){
   890|  var isOpen=lnk.classList.contains('open');
   891|  if(isOpen){closeNav();}else{openNav();}
   892|  var s=tog.querySelectorAll('span');
   893|  var willBeOpen=lnk.classList.contains('open');
   894|  s[0].style.transform=willBeOpen?'translateY(7px) rotate(45deg)':'';
   895|  s[1].style.opacity=willBeOpen?'0':'1';
   896|  s[2].style.transform=willBeOpen?'translateY(-7px) rotate(-45deg)':'';
   897|});
   898|document.querySelectorAll('.nav-links a').forEach(function(a){a.addEventListener('click',closeNav);});
   899|lnk.addEventListener('click',function(e){if(e.target===lnk){closeNav();}});
   900|</script>
   901|<!-- __WHATSAPP_FLOAT__ -->
   902|<!-- __DEMO_CALL__ -->
   903|
   904|<script>
   905|function submitContact(e){
   906|  e.preventDefault();
   907|  var f=document.getElementById('contactForm'),b=document.getElementById('contactBtn');
   908|  b.disabled=true;b.textContent='Sending...';
   909|  var d=new FormData(f);
   910|  fetch('/contact',{method:'POST',headers:{'Content-Type':'application/json'},
   911|    body:JSON.stringify({name:d.get('name'),phone:d.get('phone'),email:d.get('email')||'',message:d.get('message')})
   912|  }).then(function(r){return r.json()}).then(function(){
   913|    document.getElementById('contactMsg').style.display='block';
   914|    f.reset();b.textContent='Sent!';
   915|    setTimeout(function(){b.disabled=false;b.textContent='Send Message';},3000);
   916|  }).catch(function(){b.disabled=false;b.textContent='Send Message';alert('Error sending message. Please try again.');});
   917|  return false;
   918|}
   919|</script>
   920|</body>
   921|</html>
   922|"""
   923|