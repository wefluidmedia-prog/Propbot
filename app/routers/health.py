from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def root():
    """Landing page."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PropBot AI Receptionist</title>
  <style>
    body { font-family: Arial, sans-serif; background: #0f172a; color: #f1f5f9; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
    .card { background: #1e293b; border-radius: 12px; padding: 48px; max-width: 480px; text-align: center; box-shadow: 0 4px 32px rgba(0,0,0,0.4); }
    .badge { display: inline-block; background: #22c55e; color: #fff; font-size: 12px; font-weight: bold; padding: 4px 12px; border-radius: 99px; margin-bottom: 24px; letter-spacing: 1px; }
    h1 { font-size: 28px; margin: 0 0 8px; color: #f8fafc; }
    p { color: #94a3b8; margin: 0 0 32px; font-size: 15px; }
    .endpoints { text-align: left; background: #0f172a; border-radius: 8px; padding: 16px 20px; font-size: 13px; }
    .endpoints div { margin-bottom: 8px; }
    .method { display: inline-block; width: 44px; font-weight: bold; color: #38bdf8; }
    .path { color: #a5f3fc; }
  </style>
</head>
<body>
  <div class="card">
    <div class="badge">&#x25CF; LIVE</div>
    <h1>PropBot AI Receptionist</h1>
    <p>AI-powered voice &amp; chat receptionist for Indian real estate agents. Running 24/7.</p>
    <div class="endpoints">
      <div><span class="method">GET</span><span class="path">/health</span></div>
      <div><span class="method">POST</span><span class="path">/api/chat/{client_id}</span></div>
      <div><span class="method">POST</span><span class="path">/api/chat/{client_id}/callback</span></div>
      <div><span class="method">POST</span><span class="path">/api/webhooks/voice</span></div>
    </div>
  </div>
</body>
</html>
"""


@router.get("/health")
async def health():
    """Health check endpoint. Also used as self-ping target to keep Render alive."""
    return {"status": "ok", "service": "propbot"}
