from supabase import create_client, Client
import config

_client: Client | None = None

def get_client() -> Client:
    global _client
    if _client is None:
        if not config.SUPABASE_URL or not config.SUPABASE_ANON_KEY:
            raise RuntimeError("Missing SUPABASE_URL / SUPABASE_ANON_KEY. Copy .env.example to .env.")
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_ANON_KEY)
    return _client
