import os

# ── Icecast ──────────────────────────────────────────────────────────────────
ICECAST_HOST     = os.environ.get("ICECAST_HOST", "localhost")
ICECAST_PORT     = int(os.environ.get("ICECAST_PORT", "8000"))
ICECAST_MOUNT    = os.environ.get("ICECAST_MOUNT", "/radio")
ICECAST_PASSWORD = os.environ.get("ICECAST_PASSWORD", "hackme")
ICECAST_USER     = os.environ.get("ICECAST_USER", "source")

# ── Stream quality ───────────────────────────────────────────────────────────
BITRATE          = os.environ.get("BITRATE", "128k")
SAMPLE_RATE      = os.environ.get("SAMPLE_RATE", "44100")

# ── Playlist ─────────────────────────────────────────────────────────────────
PLAYLIST_FILE    = os.environ.get("PLAYLIST_FILE", "playlist.json")

# ── HTTP API (used by the Highrise bot to talk to this service) ──────────────
API_PORT         = int(os.environ.get("PORT", "8080"))        # Render sets PORT automatically
API_SECRET       = os.environ.get("API_SECRET", "change-me")  # shared secret with highrise-bot

# ── Behaviour ────────────────────────────────────────────────────────────────
RETRY_DELAY      = 5
SONG_COOLDOWN    = 3
MAX_QUEUE_SHOW   = 5
