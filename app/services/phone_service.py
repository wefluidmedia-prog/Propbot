"""
Phone number pool service — manages pre-purchased Vobiz numbers assigned to clients.

Numbers live in the `phone_number_pool` table. On signup a free number is claimed
and written to `clients.vobiz_number`; on client deletion it is released back.
"""

import logging
from datetime import datetime, timezone

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)


async def assign_phone_number(client_id: str) -> str | None:
    """
    Claim the next available number from the pool and assign it to client_id.

    Retries up to 3 times to handle race conditions between concurrent signups
    (another signup may grab the same row between our SELECT and UPDATE).
    Returns the assigned phone number, or None if the pool is exhausted.
    """
    db = get_supabase()

    for attempt in range(3):
        # Find one unassigned number
        result = (
            db.table("phone_number_pool")
            .select("*")
            .is_("client_id", "null")
            .limit(1)
            .execute()
        )

        if not result.data:
            logger.critical("Phone pool exhausted — no unassigned numbers available")
            return None

        row = result.data[0]
        pool_id = row["id"]
        phone_number = row["phone_number"]
        now = datetime.now(timezone.utc).isoformat()

        # Attempt to claim the row
        update_result = (
            db.table("phone_number_pool")
            .update({"client_id": client_id, "assigned_at": now})
            .eq("id", pool_id)
            .is_("client_id", "null")  # guard against concurrent assignment
            .execute()
        )

        if update_result.data:
            # Successfully claimed — now stamp the client record
            db.table("clients").update({"vobiz_number": phone_number}).eq(
                "id", client_id
            ).execute()
            logger.info(
                f"Assigned phone {phone_number} to client {client_id} "
                f"(attempt {attempt + 1})"
            )
            return phone_number

        # Another process claimed it first; loop and try the next free number
        logger.warning(
            f"Race condition on pool row {pool_id} (attempt {attempt + 1}), retrying"
        )

    logger.critical(
        f"Failed to assign a phone number to client {client_id} after 3 attempts"
    )
    return None


async def release_phone_number(client_id: str) -> None:
    """
    Return the phone number held by client_id back to the free pool
    and clear `clients.vobiz_number`.
    """
    db = get_supabase()

    result = (
        db.table("phone_number_pool")
        .select("*")
        .eq("client_id", client_id)
        .execute()
    )

    if not result.data:
        logger.warning(f"No pool row found for client {client_id} — nothing to release")
        return

    pool_id = result.data[0]["id"]
    phone_number = result.data[0]["phone_number"]

    db.table("phone_number_pool").update(
        {"client_id": None, "assigned_at": None}
    ).eq("id", pool_id).execute()

    db.table("clients").update({"vobiz_number": None}).eq(
        "id", client_id
    ).execute()

    logger.info(f"Released phone {phone_number} from client {client_id} back to pool")


async def get_pool_stats() -> dict:
    """
    Return a summary of pool utilisation.

    Example: {"total": 20, "available": 12, "assigned": 8}
    """
    db = get_supabase()

    result = db.table("phone_number_pool").select("*").execute()
    rows = result.data or []

    total = len(rows)
    assigned = sum(1 for r in rows if r.get("client_id") is not None)
    available = total - assigned

    return {"total": total, "available": available, "assigned": assigned}
