import base64
import os
import tempfile
from pathlib import Path

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

# ── YouTube cookies ────────────────────────────────────────────────────────
YOUTUBE_COOKIES_B64 = os.environ.get("YOUTUBE_COOKIES_B64", "").strip()
if not YOUTUBE_COOKIES_B64:
    cookie_file = Path("cookies_b64.txt")
    if cookie_file.exists():
        for encoding in ("utf-8-sig", "utf-8", "utf-16", "utf-16-le", "utf-16-be"):
            try:
                YOUTUBE_COOKIES_B64 = cookie_file.read_text(encoding=encoding).strip()
                break
            except UnicodeDecodeError:
                continue


def get_youtube_cookie_file() -> str | None:
    if not YOUTUBE_COOKIES_B64:
        return None
    try:
        decoded = base64.b64decode(YOUTUBE_COOKIES_B64).decode("utf-8")
    except Exception:
        return None

    with tempfile.NamedTemporaryFile(
        "w",
        suffix=".txt",
        delete=False,
        encoding="utf-8",
    ) as handle:
        handle.write(decoded)
        return handle.name

# ── Behaviour ────────────────────────────────────────────────────────────────
RETRY_DELAY      = 5
SONG_COOLDOWN    = 3
MAX_QUEUE_SHOW   = 5
