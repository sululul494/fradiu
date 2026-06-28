import json
import logging
from pathlib import Path
import yt_dlp
import config

log = logging.getLogger("playlist")

_FLAT_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": "in_playlist",
    "ignoreerrors": True,
    "skip_download": True,
}


def _build_flat_opts() -> dict:
    opts = dict(_FLAT_OPTS)
    cookie_file = config.get_youtube_cookie_file()
    if cookie_file:
        opts["cookiefile"] = cookie_file
    return opts


def _build_info_opts() -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "ignoreerrors": True,
    }
    cookie_file = config.get_youtube_cookie_file()
    if cookie_file:
        opts["cookiefile"] = cookie_file
    return opts


def resolve_url(url: str) -> list[str]:
    urls = []
    try:
        with yt_dlp.YoutubeDL(_build_flat_opts()) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return []
            if "entries" in info:
                for e in info["entries"]:
                    if e and e.get("id"):
                        urls.append(f"https://www.youtube.com/watch?v={e['id']}")
            elif info.get("id"):
                urls.append(f"https://www.youtube.com/watch?v={info['id']}")
    except Exception as e:
        log.error("Failed to resolve %s: %s", url, e)
    log.info("Resolved %s → %d tracks", url, len(urls))
    return urls


def load_playlist(playlist_file: str) -> list[str]:
    path = Path(playlist_file)
    if not path.exists():
        log.error("playlist.json not found at %s", path.absolute())
        return []
    with open(path) as f:
        data = json.load(f)
    all_urls = []
    for source in data.get("sources", []):
        log.info("Loading: %s", source)
        all_urls.extend(resolve_url(source))
    seen, unique = set(), []
    for u in all_urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    log.info("Total: %d unique tracks", len(unique))
    return unique


def search_youtube(query: str) -> dict | None:
    opts = _build_info_opts()
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if info and info.get("entries"):
                e = info["entries"][0]
                if e:
                    return {"url": f"https://www.youtube.com/watch?v={e['id']}",
                            "title": e.get("title", query),
                            "duration": e.get("duration", 0)}
    except Exception as e:
        log.error("Search failed '%s': %s", query, e)
    return None


def get_video_info(url: str) -> dict | None:
    opts = _build_info_opts()
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                return {"url": f"https://www.youtube.com/watch?v={info['id']}",
                        "title": info.get("title", "Unknown"),
                        "duration": info.get("duration", 0)}
    except Exception as e:
        log.error("get_video_info failed %s: %s", url, e)
    return None
