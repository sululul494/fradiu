import base64
import logging
import os
import tempfile
from pathlib import Path

log = logging.getLogger("config")

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
    sources: list[tuple[str, str]] = []  # (text, source)
    if YOUTUBE_COOKIES_B64:
        sources.append((YOUTUBE_COOKIES_B64, "env_b64"))
    if YOUTUBE_COOKIES_FILE:
        try:
            txt = Path(YOUTUBE_COOKIES_FILE).read_text(encoding="utf-8", errors="ignore")
            sources.append((txt, f"file:{YOUTUBE_COOKIES_FILE}"))
        except Exception:
            log.debug("Unable to read YOUTUBE_COOKIES_FILE %s", YOUTUBE_COOKIES_FILE)

    for rel_path in ("cookies_b64.txt", "www.youtube.com_cookies.txt"):
        path = Path(rel_path)
        if path.exists():
            try:
                txt = path.read_text(encoding="utf-8", errors="ignore")
                sources.append((txt, f"file:{rel_path}"))
            except Exception:
                log.debug("Unable to read local cookie candidate %s", rel_path)

    for value, source in sources:
        if not value:
            continue
        candidate = value.strip()
        if not candidate:
            continue
        try:
            decoded = base64.b64decode(candidate, validate=True).decode("utf-8")
            log.info("YouTube cookies loaded from %s (base64)", source)
            return decoded
        except Exception:
            log.info("YouTube cookies loaded from %s (raw)", source)
            return value

    log.info("No YouTube cookies found (YOUTUBE_COOKIES_B64/YOUTUBE_COOKIES_FILE/local files)")
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
        log.info("Wrote temporary YouTube cookie file: %s", handle.name)
        return handle.name

# ── Behaviour ────────────────────────────────────────────────────────────────
RETRY_DELAY      = 5
SONG_COOLDOWN    = 3
MAX_QUEUE_SHOW   = 5
