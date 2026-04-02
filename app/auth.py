"""
Per-client API key authentication.

Keys are stored as SHA-256 hashes in the api_keys table.
Clients authenticate with: Authorization: Bearer <raw_key>

Also supports the legacy WEBHOOK_SECRET for backward compat (webhooks only).
"""

import hashlib
import logging
import secrets

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=True)


def hash_key(raw_key: str) -> str:
    """SHA-256 hash a raw API key for storage."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a secure random API key: pb_<40 hex chars>."""
    return f"pb_{secrets.token_hex(20)}"


def create_api_key(client_id: str, label: str = "default") -> str:
    """
    Create a new API key for a client, store the hash, return the raw key.
    The raw key is shown only once — we don't store it.
    """
    raw_key = generate_api_key()
    key_h = hash_key(raw_key)
    db = get_supabase()
    db.table("api_keys").insert({
        "client_id": client_id,
        "key_hash": key_h,
        "label": label,
    }).execute()
    return raw_key


def verify_api_key(raw_key: str) -> dict | None:
    """
    Look up an API key by its hash. Returns the api_keys row (with client_id)
    or None if not found / inactive.
    """
    key_h = hash_key(raw_key)
    db = get_supabase()
    result = (
        db.table("api_keys")
        .select("*")
        .eq("key_hash", key_h)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if result.data:
        row = result.data[0]
        # Update last_used_at (fire-and-forget, don't block on failure)
        try:
            db.table("api_keys").update({"last_used_at": "now()"}).eq("id", row["id"]).execute()
        except Exception:
            pass
        return row
    return None


def require_client_key(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
) -> str:
    """
    FastAPI dependency — validates Bearer token and returns the client_id.
    Supports both per-client API keys (pb_...) and legacy WEBHOOK_SECRET.
    """
    token = credentials.credentials

    # Legacy: accept WEBHOOK_SECRET for backward compat (webhooks, internal tools)
    if settings.WEBHOOK_SECRET and token == settings.WEBHOOK_SECRET:
        # Can't bind to a specific client — caller must provide client_id in URL
        return "__legacy__"

    # Per-client API key
    key_row = verify_api_key(token)
    if not key_row:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return key_row["client_id"]


def require_client_key_strict(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
) -> str:
    """
    Strict version — does NOT accept legacy WEBHOOK_SECRET.
    For client-facing endpoints where we need to know the exact client.
    """
    token = credentials.credentials
    key_row = verify_api_key(token)
    if not key_row:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return key_row["client_id"]
