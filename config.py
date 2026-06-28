import base64
import os
import tempfile
from pathlib import Path

# ── Icecast ──────────────────────────────────────────────────────────────────
ICECAST_HOST     = os.environ.get("ICECAST_HOST", "localhost")
ICECAST_PORT     = int(os.environ.get("ICECAST_PORT", "8000"))
ICECAST_MOUNT    = os.environ.get("ICECAST_MOUNT", "/radio")
ICECAST_PASSWORD = os.environ.get("ICECAST_PASSWORD", "sululu231")
ICECAST_USER     = os.environ.get("ICECAST_USER", "itachi")

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
YOUTUBE_COOKIES_FILE = os.environ.get("YOUTUBE_COOKIES_FILE", "").strip()


def _load_cookie_text() -> str | None:
    candidates = []
    if YOUTUBE_COOKIES_B64:
        candidates.append(YOUTUBE_COOKIES_B64)
    if YOUTUBE_COOKIES_FILE:
        candidates.append(Path(YOUTUBE_COOKIES_FILE).read_text(encoding="utf-8", errors="ignore"))

    for rel_path in ("cookies_b64.txt", "www.youtube.com_cookies.txt"):
        path = Path(rel_path)
        if path.exists():
            candidates.append(path.read_text(encoding="utf-8", errors="ignore"))

    for value in candidates:
        if not value:
            continue
        candidate = value.strip()
        if not candidate:
            continue
        try:
            decoded = base64.b64decode(candidate, validate=True).decode("utf-8")
            return decoded
        except Exception:
            return value

    return None


def get_youtube_cookie_file() -> str | None:
    text = _load_cookie_text()
    if not text:
        return None

    with tempfile.NamedTemporaryFile(
        "w",
        suffix=".txt",
        delete=False,
        encoding="utf-8",
    ) as handle:
        handle.write(text)
        return handle.name

# ── Behaviour ────────────────────────────────────────────────────────────────
RETRY_DELAY      = 5
SONG_COOLDOWN    = 3
MAX_QUEUE_SHOW   = 5
