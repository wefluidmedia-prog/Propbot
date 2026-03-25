from supabase import create_client, Client

_client: Client | None = None


def init_supabase(url: str, key: str) -> Client:
    """Initialize the Supabase client. Called once at app startup."""
    global _client
    _client = create_client(url, key)
    return _client


def get_supabase() -> Client:
    """Get the initialized Supabase client. Raises if not initialized."""
    if _client is None:
        raise RuntimeError("Supabase client not initialized. Call init_supabase() first.")
    return _client
