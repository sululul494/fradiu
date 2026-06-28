"""
api.py — HTTP API for ItachiHits Radio.

GET  /              → status page (HTML, browser-friendly)
GET  /health        → liveness check (JSON)
GET  /np            → now playing (JSON)
GET  /queue         → upcoming songs (JSON)
POST /request       → add a song request (JSON, requires X-API-Secret header)
POST /skip          → skip current song (JSON, requires X-API-Secret header)

NOTE: Audio streaming is handled by Icecast, NOT this server.
      This server is only the control API for the Highrise bot.
"""

import asyncio
import json
import logging
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.parse import urlparse

import config
from queue_manager import queue_manager
from playlist_loader import get_video_info, search_youtube

log = logging.getLogger("api")

_YT_RE = re.compile(r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]+")


def _json(data) -> bytes:
    return json.dumps(data, indent=2).encode()


def _check_secret(handler: "RadioAPIHandler") -> bool:
    return handler.headers.get("X-API-Secret", "") == config.API_SECRET


def _build_home_html() -> bytes:
    song = queue_manager.current
    np   = song.title if song else "Nothing playing yet"
    by   = f" — requested by {song.requested_by}" if song and song.requested_by else ""

    html = f"""<!DOCTYPE html>
<html>
<head>
  <title>ItachiHits Radio</title>
  <meta charset="utf-8">
  <style>
    body {{ font-family: monospace; background: #0d0d0d; color: #e0e0e0;
            max-width: 640px; margin: 60px auto; padding: 0 20px; }}
    h1   {{ color: #ff6b6b; }}
    h2   {{ color: #aaa; font-size: 14px; margin-top: 30px; }}
    .np  {{ background: #1a1a1a; border-left: 3px solid #ff6b6b;
            padding: 12px 16px; border-radius: 4px; margin: 10px 0; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
    td, th {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #222; font-size: 13px; }}
    th   {{ color: #888; font-weight: normal; }}
    code {{ background: #1a1a1a; padding: 2px 6px; border-radius: 3px; color: #ff6b6b; }}
  </style>
</head>
<body>
  <h1>🎧 ItachiHits Radio</h1>

  <h2>NOW PLAYING</h2>
  <div class="np">▶ {np}{by}</div>

  <h2>API ENDPOINTS</h2>
  <table>
    <tr><th>Method</th><th>Path</th><th>Description</th></tr>
    <tr><td>GET</td><td><code>/np</code></td><td>Currently playing song</td></tr>
    <tr><td>GET</td><td><code>/queue</code></td><td>Upcoming songs</td></tr>
    <tr><td>GET</td><td><code>/health</code></td><td>Liveness check</td></tr>
    <tr><td>POST</td><td><code>/request</code></td><td>Add a song request (requires X-API-Secret)</td></tr>
    <tr><td>POST</td><td><code>/skip</code></td><td>Skip current song (requires X-API-Secret)</td></tr>
  </table>

  <h2>HIGHRISE BOT COMMANDS</h2>
  <table>
    <tr><th>Command</th><th>What it does</th></tr>
    <tr><td><code>!np</code></td><td>Show currently playing song</td></tr>
    <tr><td><code>!queue</code></td><td>Show upcoming songs</td></tr>
    <tr><td><code>!request Naruto OP</code></td><td>Search YouTube and add to queue</td></tr>
    <tr><td><code>!request https://youtu.be/xxx</code></td><td>Add a specific YouTube video</td></tr>
    <tr><td><code>-play Naruto OP</code></td><td>Same as !request (alias)</td></tr>
    <tr><td><code>!skip</code></td><td>Skip current song (owner only)</td></tr>
  </table>

  <h2>NOTE</h2>
  <p>Audio streaming goes directly to Icecast — not through this URL.<br>
  This page is just the control API used by the Highrise bot.</p>
</body>
</html>"""
    return html.encode()


class RadioAPIHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        log.debug(format, *args)

    def do_GET(self):
        path = urlparse(self.path).path

        if path in ("/", ""):
            body = _build_home_html()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif path == "/health":
            self._json_resp(200, {"status": "ok", "radio": "ItachiHits Radio"})

        elif path == "/np":
            song = queue_manager.current
            if song:
                self._json_resp(200, {
                    "title":        song.title,
                    "url":          song.url,
                    "requested_by": song.requested_by,
                    "duration":     song.duration,
                })
            else:
                self._json_resp(200, {"title": None, "message": "Nothing playing yet"})

        elif path == "/queue":
            self._json_resp(200, {"queue": queue_manager.peek(config.MAX_QUEUE_SHOW)})

        elif path == "/stream":
            stream_url = f"http://{config.ICECAST_HOST}:{config.ICECAST_PORT}{config.ICECAST_MOUNT}"
            body = (
                "#EXTM3U\n"
                f"#EXTINF:-1,ItachiHits Radio\n"
                f"{stream_url}\n"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "audio/x-mpegurl; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        else:
            self._json_resp(404, {"error": "not found",
                                  "hint": "Visit / for available endpoints"})

    def do_POST(self):
        path = urlparse(self.path).path

        if not _check_secret(self):
            self._json_resp(401, {"error": "unauthorized — set X-API-Secret header"})
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json_resp(400, {"error": "invalid JSON body"})
            return

        if path == "/request":
            query        = body.get("query", "").strip()
            requested_by = body.get("requested_by", "someone")

            if not query:
                self._json_resp(400, {"error": "query field required"})
                return

            if _YT_RE.search(query):
                info = get_video_info(query)
            else:
                info = search_youtube(query)

            if not info:
                self._json_resp(404, {"error": "song not found on YouTube"})
                return

            loop   = _get_loop()
            future = asyncio.run_coroutine_threadsafe(
                queue_manager.add_request(info["url"], info["title"], requested_by),
                loop,
            )
            pos = future.result(timeout=5)
            self._json_resp(200, {
                "added":    True,
                "title":    info["title"],
                "position": pos,
                "duration": info.get("duration", 0),
            })

        elif path == "/skip":
            loop = _get_loop()
            asyncio.run_coroutine_threadsafe(queue_manager.skip(), loop).result(timeout=5)
            self._json_resp(200, {"skipped": True})

        else:
            self._json_resp(404, {"error": "not found",
                                  "hint": "Visit / for available endpoints"})

    def _json_resp(self, code: int, data: dict):
        body = _json(data)
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# ── asyncio loop reference ────────────────────────────────────────────────────
_loop: asyncio.AbstractEventLoop | None = None

def _get_loop() -> asyncio.AbstractEventLoop:
    assert _loop is not None
    return _loop


def start_api_server(loop: asyncio.AbstractEventLoop):
    global _loop
    _loop = loop
    server = HTTPServer(("0.0.0.0", config.API_PORT), RadioAPIHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    log.info("API server on port %d", config.API_PORT)
