"""
Founder Admin Dashboard — business metrics + client management.

Routes:
  GET  /admin              -> admin SPA (password login via WEBHOOK_SECRET)
  GET  /admin/api/metrics  -> aggregate business metrics
  GET  /admin/api/clients  -> full client list with details
  POST /admin/api/phone-pool        -> seed phone numbers
  GET  /admin/api/phone-pool        -> pool stats
  POST /admin/api/retry-provision/{client_id} -> retry phone assignment
"""

import hmac
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.config import settings
from app.db.supabase_client import get_supabase

router = APIRouter()
logger = logging.getLogger(__name__)

PLAN_FEES = {"starter": 2499, "pro": 4999}


# ─── Auth ────────────────────────────────────────────────────────

def _require_admin(request: Request) -> None:
    """Simple admin auth via Authorization: Bearer {WEBHOOK_SECRET}."""
    auth = request.headers.get("Authorization", "")
    secret = settings.WEBHOOK_SECRET
    if not secret or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Admin auth required")
    token = auth[len("Bearer "):]
    if not hmac.compare_digest(token, secret):
        raise HTTPException(status_code=401, detail="Invalid admin token")


# ─── API Endpoints ───────────────────────────────────────────────

@router.get("/api/metrics")
async def get_metrics(request: Request):
    _require_admin(request)
    db = get_supabase()

    clients = db.table("clients").select(
        "id, subscription_status, trial_ends_at, plan_type, created_at"
    ).execute()
    rows = clients.data or []

    now = datetime.now(timezone.utc)
    month_prefix = now.strftime("%Y-%m")
    prev_month = (now.month - 1) or 12
    prev_year = now.year if now.month > 1 else now.year - 1
    prev_prefix = f"{prev_year}-{prev_month:02d}"

    total = len(rows)
    active_paid = 0
    active_trials = 0
    expired = 0
    cancelled = 0
    paused = 0
    mrr = 0
    signups_this_month = 0
    signups_last_month = 0

    for r in rows:
        status = r.get("subscription_status", "")
        plan = r.get("plan_type") or "pro"
        created = (r.get("created_at") or "")[:7]

        if status == "active":
            active_paid += 1
            mrr += PLAN_FEES.get(plan, 4999)
        elif status == "trial":
            trial_raw = r.get("trial_ends_at")
            if trial_raw:
                try:
                    trial_end = datetime.fromisoformat(trial_raw.replace("Z", "+00:00"))
                    if trial_end > now:
                        active_trials += 1
                    else:
                        expired += 1
                except ValueError:
                    expired += 1
            else:
                active_trials += 1
        elif status == "expired":
            expired += 1
        elif status == "cancelled":
            cancelled += 1
        elif status == "paused":
            paused += 1

        if created == month_prefix:
            signups_this_month += 1
        elif created == prev_prefix:
            signups_last_month += 1

    return {
        "total_clients": total,
        "active_paid": active_paid,
        "active_trials": active_trials,
        "expired_trials": expired,
        "cancelled": cancelled,
        "paused": paused,
        "mrr_inr": mrr,
        "signups_this_month": signups_this_month,
        "signups_last_month": signups_last_month,
    }


@router.get("/api/clients")
async def list_clients(request: Request):
    _require_admin(request)
    db = get_supabase()
    result = db.table("clients").select(
        "id, business_name, agent_name, agent_email, agent_phone, "
        "plan_type, subscription_status, trial_ends_at, "
        "exotel_number, setup_status, created_at"
    ).order("created_at", desc=True).execute()
    return {"clients": result.data or []}


@router.post("/api/phone-pool")
async def seed_phone_pool(request: Request):
    """Add phone numbers to the pool."""
    _require_admin(request)
    body = await request.json()
    numbers = body.get("numbers", [])
    if not numbers:
        raise HTTPException(400, "Provide a 'numbers' list")
    db = get_supabase()
    added = 0
    for num in numbers:
        num = str(num).strip()
        if not num:
            continue
        try:
            db.table("phone_number_pool").insert({"phone_number": num}).execute()
            added += 1
        except Exception:
            pass
    return {"added": added, "total_submitted": len(numbers)}


@router.get("/api/phone-pool")
async def get_phone_pool_status(request: Request):
    """Get phone pool stats."""
    _require_admin(request)
    from app.services.phone_service import get_pool_stats
    return await get_pool_stats()


@router.post("/api/retry-provision/{client_id}")
async def retry_provision(client_id: str, request: Request):
    """Retry phone assignment for a stuck client."""
    _require_admin(request)
    db = get_supabase()
    client = db.table("clients").select(
        "id, setup_status, exotel_number, business_name"
    ).eq("id", client_id).single().execute()
    if not client.data:
        raise HTTPException(status_code=404, detail="Client not found")

    info = client.data
    result = {"client_id": client_id, "business": info.get("business_name")}

    if not info.get("exotel_number"):
        from app.services.phone_service import assign_phone_number
        phone = await assign_phone_number(client_id)
        result["phone_assigned"] = phone
    else:
        result["phone_assigned"] = info["exotel_number"]
        result["phone_note"] = "already had number"

    db.table("clients").update({"setup_status": "ready"}).eq("id", client_id).execute()
    result["setup_status"] = "ready"
    return result


# ─── Admin SPA ───────────────────────────────────────────────────

@router.get("")
async def admin_page():
    return HTMLResponse(ADMIN_HTML)


ADMIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PropBot Admin</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:#F3F4F6;color:#111827;-webkit-font-smoothing:antialiased;}

/* Login */
.login-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#1e293b,#0f172a);}
.login-card{width:400px;background:#fff;border-radius:20px;box-shadow:0 8px 40px rgba(0,0,0,0.2);overflow:hidden;}
.login-top{background:linear-gradient(135deg,#FF5722,#FF7043);padding:32px;text-align:center;}
.login-top h1{color:#fff;font-size:24px;font-weight:800;}
.login-top p{color:rgba(255,255,255,0.8);font-size:14px;margin-top:6px;}
.login-body{padding:32px;}
.login-body input{width:100%;padding:12px 14px;border:1.5px solid #d1d5db;border-radius:8px;font-size:15px;margin-bottom:12px;font-family:monospace;}
.login-body input:focus{outline:none;border-color:#FF5722;box-shadow:0 0 0 3px rgba(255,87,34,.1);}
.btn{padding:13px 24px;background:#FF5722;color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;transition:background .15s;width:100%;}
.btn:hover{background:#E64A19;}
.login-err{color:#ef4444;font-size:13px;margin-top:8px;text-align:center;display:none;}

/* Shell */
.shell{display:none;min-height:100vh;}
.topbar{background:#111827;padding:0 28px;height:56px;display:flex;align-items:center;justify-content:space-between;}
.topbar h1{color:#fff;font-size:18px;font-weight:800;}
.topbar h1 span{color:#FF5722;}
.topbar-right{display:flex;align-items:center;gap:12px;}
.topbar .btn-sm{padding:6px 16px;font-size:13px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.15);border-radius:6px;color:#9CA3AF;cursor:pointer;font-weight:500;}
.topbar .btn-sm:hover{background:rgba(255,255,255,0.15);color:#fff;}
.content{max-width:1200px;margin:0 auto;padding:28px;}

/* Metrics */
.metrics{display:grid;grid-template-columns:repeat(5,1fr);gap:16px;margin-bottom:28px;}
.metric{background:#fff;padding:20px;border-radius:14px;box-shadow:0 1px 4px rgba(0,0,0,.06);border:1px solid #e2e8f0;}
.metric .label{font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;}
.metric .val{font-size:28px;font-weight:800;color:#1e293b;}
.metric .sub{font-size:12px;color:#94a3b8;margin-top:4px;}
.metric.highlight .val{color:#FF5722;}
.metric.green .val{color:#059669;}
.metric.amber .val{color:#d97706;}

/* Table */
.card{background:#fff;border-radius:14px;box-shadow:0 1px 4px rgba(0,0,0,.06);border:1px solid #e2e8f0;overflow:hidden;}
.card-hdr{padding:16px 20px;border-bottom:1px solid #f1f5f9;display:flex;align-items:center;justify-content:space-between;}
.card-hdr h2{font-size:16px;font-weight:700;}
.card-hdr .count{font-size:13px;color:#64748b;}
.search{padding:8px 14px;border:1.5px solid #d1d5db;border-radius:8px;font-size:14px;width:260px;}
.search:focus{outline:none;border-color:#FF5722;}
table{width:100%;border-collapse:collapse;}
th{text-align:left;padding:11px 16px;font-size:11px;font-weight:700;color:#64748b;background:#f8fafc;text-transform:uppercase;letter-spacing:.5px;}
td{padding:12px 16px;font-size:13px;border-top:1px solid #f1f5f9;}
tr:hover td{background:#f8fafc;}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;}
.b-active{background:#d1fae5;color:#065f46;}
.b-trial{background:#fef3c7;color:#92400e;}
.b-expired{background:#fee2e2;color:#991b1b;}
.b-cancelled{background:#f3f4f6;color:#6b7280;}
.b-paused{background:#e0e7ff;color:#3730a3;}
.b-starter{background:#dbeafe;color:#1e40af;}
.b-pro{background:rgba(255,87,34,0.1);color:#E64A19;}
.phone{color:#FF5722;font-weight:600;font-size:12px;}
.btn-retry{padding:4px 12px;font-size:12px;background:#FF5722;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600;}
.btn-retry:hover{background:#E64A19;}
.empty{padding:40px;text-align:center;color:#94a3b8;}

@media(max-width:900px){
  .metrics{grid-template-columns:repeat(2,1fr);}
  .content{padding:16px;}
  table{font-size:12px;}
  th,td{padding:8px 10px;}
}
</style>
</head>
<body>

<!-- Login -->
<div id="login" class="login-wrap">
  <div class="login-card">
    <div class="login-top">
      <h1>PropBot Admin</h1>
      <p>Founder dashboard</p>
    </div>
    <div class="login-body">
      <input id="secret" type="password" placeholder="Admin secret key">
      <button class="btn" onclick="doLogin()">Sign In</button>
      <div id="login-err" class="login-err">Invalid key</div>
    </div>
  </div>
</div>

<!-- Dashboard -->
<div id="app" class="shell">
  <div class="topbar">
    <h1>Prop<span>Bot</span> Admin</h1>
    <div class="topbar-right">
      <span id="refresh-ts" style="color:#64748b;font-size:12px;"></span>
      <button class="btn-sm" onclick="loadAll()">Refresh</button>
      <button class="btn-sm" onclick="doLogout()">Logout</button>
    </div>
  </div>

  <div class="content">
    <div id="metrics" class="metrics"></div>

    <div class="card">
      <div class="card-hdr">
        <h2>All Clients</h2>
        <input class="search" id="search" placeholder="Search by name or email..." oninput="filterClients()">
      </div>
      <div style="overflow-x:auto;">
        <table>
          <thead>
            <tr>
              <th>Business</th>
              <th>Email</th>
              <th>Plan</th>
              <th>Status</th>
              <th>Phone</th>
              <th>Setup</th>
              <th>Signed Up</th>
              <th>Trial Ends</th>
              <th></th>
            </tr>
          </thead>
          <tbody id="clients-body"></tbody>
        </table>
      </div>
      <div id="empty" class="empty" style="display:none;">No clients yet</div>
    </div>
  </div>
</div>

<script>
let TOKEN='';
let allClients=[];

function doLogin(){
  TOKEN=document.getElementById('secret').value.trim();
  if(!TOKEN){document.getElementById('login-err').style.display='block';return;}
  fetch('/admin/api/metrics',{headers:{'Authorization':'Bearer '+TOKEN}})
    .then(r=>{
      if(!r.ok) throw new Error('bad');
      return r.json();
    })
    .then(()=>{
      localStorage.setItem('propbot_admin_token',TOKEN);
      document.getElementById('login').style.display='none';
      document.getElementById('app').style.display='block';
      loadAll();
    })
    .catch(()=>{
      document.getElementById('login-err').style.display='block';
    });
}

function doLogout(){
  localStorage.removeItem('propbot_admin_token');
  TOKEN='';
  location.reload();
}

function api(path){
  return fetch('/admin'+path,{headers:{'Authorization':'Bearer '+TOKEN}}).then(r=>r.json());
}

async function loadAll(){
  document.getElementById('refresh-ts').textContent='Updated '+new Date().toLocaleTimeString();
  const [m,c]=await Promise.all([api('/api/metrics'),api('/api/clients')]);
  renderMetrics(m);
  allClients=c.clients||[];
  renderClients(allClients);
}

function renderMetrics(m){
  const cards=[
    {label:'Total Clients',val:m.total_clients,cls:''},
    {label:'Active Trials',val:m.active_trials,cls:'amber',sub:m.expired_trials+' expired'},
    {label:'Paid Subscribers',val:m.active_paid,cls:'green',sub:m.paused+' paused'},
    {label:'MRR',val:'\u20B9'+m.mrr_inr.toLocaleString('en-IN'),cls:'highlight'},
    {label:'Signups This Month',val:m.signups_this_month,cls:'',sub:'Last month: '+m.signups_last_month},
  ];
  document.getElementById('metrics').innerHTML=cards.map(c=>`
    <div class="metric ${c.cls}">
      <div class="label">${c.label}</div>
      <div class="val">${c.val}</div>
      ${c.sub?'<div class="sub">'+c.sub+'</div>':''}
    </div>`).join('');
}

function statusBadge(s){
  const m={active:'b-active',trial:'b-trial',expired:'b-expired',cancelled:'b-cancelled',paused:'b-paused'};
  return `<span class="badge ${m[s]||'b-cancelled'}">${s||'unknown'}</span>`;
}

function planBadge(p){
  return `<span class="badge ${p==='starter'?'b-starter':'b-pro'}">${p==='starter'?'Starter':'Pro'}</span>`;
}

function daysLeft(t){
  if(!t) return '-';
  const d=Math.ceil((new Date(t)-new Date())/(1000*60*60*24));
  if(d<0) return '<span style="color:#ef4444">Expired '+Math.abs(d)+'d ago</span>';
  return d+'d left';
}

function fmtDate(d){
  if(!d) return '-';
  return new Date(d).toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'});
}

function renderClients(list){
  const body=document.getElementById('clients-body');
  const empty=document.getElementById('empty');
  if(!list.length){body.innerHTML='';empty.style.display='block';return;}
  empty.style.display='none';
  body.innerHTML=list.map(c=>`<tr>
    <td><strong>${c.business_name||'-'}</strong><br><span style="color:#64748b;font-size:12px">${c.agent_name||''}</span></td>
    <td style="font-size:12px">${c.agent_email||'-'}</td>
    <td>${planBadge(c.plan_type||'pro')}</td>
    <td>${statusBadge(c.subscription_status)}</td>
    <td class="phone">${c.exotel_number||'<span style="color:#94a3b8">none</span>'}</td>
    <td>${c.setup_status||'-'}</td>
    <td style="font-size:12px">${fmtDate(c.created_at)}</td>
    <td style="font-size:12px">${c.subscription_status==='trial'?daysLeft(c.trial_ends_at):'-'}</td>
    <td>${c.setup_status!=='ready'?'<button class="btn-retry" onclick="retryProvision(\''+c.id+'\')">Retry</button>':''}</td>
  </tr>`).join('');
}

function filterClients(){
  const q=document.getElementById('search').value.toLowerCase();
  if(!q){renderClients(allClients);return;}
  renderClients(allClients.filter(c=>
    (c.business_name||'').toLowerCase().includes(q)||
    (c.agent_email||'').toLowerCase().includes(q)||
    (c.agent_name||'').toLowerCase().includes(q)
  ));
}

async function retryProvision(id){
  if(!confirm('Retry phone provisioning for this client?')) return;
  const r=await fetch('/admin/api/retry-provision/'+id,{method:'POST',headers:{'Authorization':'Bearer '+TOKEN}});
  const d=await r.json();
  alert(d.phone_assigned?'Phone assigned: '+d.phone_assigned:'Done: '+JSON.stringify(d));
  loadAll();
}

// Auto-login from localStorage
(function(){
  const saved=localStorage.getItem('propbot_admin_token');
  if(saved){
    TOKEN=saved;
    document.getElementById('login').style.display='none';
    document.getElementById('app').style.display='block';
    loadAll();
  }
})();
</script>
</body>
</html>"""
