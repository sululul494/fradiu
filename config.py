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


def _read_cookie_file(path_str: str) -> str | None:
    path = Path(path_str)
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None


def _looks_like_cookie_export(text: str) -> bool:
    if not text:
        return False

    cleaned = text.strip()
    if not cleaned:
        return False

    lowered = cleaned.lower()
    if "placeholder" in lowered and "cookie" in lowered:
        return False

    lines = [line for line in cleaned.splitlines() if line.strip()]
    non_comment_lines = [line for line in lines if not line.lstrip().startswith("#")]
    if not non_comment_lines:
        return False

    for line in non_comment_lines:
        parts = line.split("\t")
        if len(parts) >= 7:
            return True

    return False


def _load_cookie_text() -> str | None:
    sources: list[tuple[str, str]] = []  # (text, source)
    if YOUTUBE_COOKIES_B64:
        sources.append((YOUTUBE_COOKIES_B64, "env_b64"))
    if YOUTUBE_COOKIES_FILE:
        txt = _read_cookie_file(YOUTUBE_COOKIES_FILE)
        if txt:
            sources.append((txt, f"file:{YOUTUBE_COOKIES_FILE}"))

    for rel_path in ("cookies.txt", "cookies_b64.txt", "www.youtube.com_cookies.txt"):
        txt = _read_cookie_file(rel_path)
        if txt:
            sources.append((txt, f"file:{rel_path}"))

    for value, source in sources:
        if not value:
            continue
        candidate = value.strip()
        if not candidate:
            continue
        try:
            decoded = base64.b64decode(candidate, validate=True).decode("utf-8")
            log.info("YouTube cookies loaded from %s (base64)", source)
            if not _looks_like_cookie_export(decoded):
                log.warning("Ignoring cookie content from %s because it does not look like a Netscape-style cookie export", source)
                continue
            return decoded
        except Exception:
            log.info("YouTube cookies loaded from %s (raw)", source)
            if not _looks_like_cookie_export(value):
                log.warning("Ignoring cookie content from %s because it does not look like a Netscape-style cookie export", source)
                continue
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


def get_stream_url() -> str:
    public_base = (
        os.environ.get("STREAM_BASE_URL", "").strip()
        or os.environ.get("PUBLIC_STREAM_URL", "").strip()
        or os.environ.get("RENDER_EXTERNAL_URL", "").strip()
        or ""
    ).strip()

    if public_base:
        if "://" not in public_base:
            public_base = f"http://{public_base}"
        return f"{public_base.rstrip('/')}{ICECAST_MOUNT}"

    host = (ICECAST_HOST or "localhost").strip()
    if "://" in host:
        return f"{host.rstrip('/')}{ICECAST_MOUNT}"

    return f"http://{host}:{ICECAST_PORT}{ICECAST_MOUNT}"

# ── Behaviour ────────────────────────────────────────────────────────────────
RETRY_DELAY      = 5
SONG_COOLDOWN    = 3
MAX_QUEUE_SHOW   = 5
