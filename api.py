"""
api.py — Lightweight HTTP API so the Highrise bot (separate service)
         can query and control the radio.

Endpoints:
  GET  /np                    → currently playing song
  GET  /queue                 → upcoming songs
  POST /request               → add a user song request
  POST /skip                  → skip current song
  GET  /health                → liveness check

All write endpoints require the header:  X-API-Secret: <API_SECRET>
"""

import asyncio
import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.parse import urlparse

import config
from queue_manager import queue_manager
from playlist_loader import get_video_info, search_youtube

log = logging.getLogger("api")

import re
_YT_RE = re.compile(r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]+")


def _json(data) -> bytes:
    return json.dumps(data).encode()


def _check_secret(handler: "RadioAPIHandler") -> bool:
    secret = handler.headers.get("X-API-Secret", "")
    return secret == config.API_SECRET


class RadioAPIHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        log.debug(format, *args)   # suppress default noisy logs

    # ── routing ───────────────────────────────────────────────────────────────

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/health":
            self._send(200, {"status": "ok"})

        elif path == "/np":
            song = queue_manager.current
            if song:
                self._send(200, {
                    "title":        song.title,
                    "url":          song.url,
                    "requested_by": song.requested_by,
                    "duration":     song.duration,
                })
            else:
                self._send(200, {"title": None})

        elif path == "/queue":
            self._send(200, {"queue": queue_manager.peek(config.MAX_QUEUE_SHOW)})

        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path

        if not _check_secret(self):
            self._send(401, {"error": "unauthorized"})
            return

        length  = int(self.headers.get("Content-Length", 0))
        body    = json.loads(self.rfile.read(length) or b"{}")

        if path == "/request":
            query        = body.get("query", "").strip()
            requested_by = body.get("requested_by", "someone")

            if not query:
                self._send(400, {"error": "query required"})
                return

            # resolve in this thread (yt-dlp is blocking)
            if _YT_RE.search(query):
                info = get_video_info(query)
            else:
                info = search_youtube(query)

            if not info:
                self._send(404, {"error": "song not found"})
                return

            # schedule the async add_request from this sync thread
            loop    = _get_loop()
            future  = asyncio.run_coroutine_threadsafe(
                queue_manager.add_request(info["url"], info["title"], requested_by),
                loop,
            )
            pos = future.result(timeout=5)
            self._send(200, {"title": info["title"], "position": pos,
                             "duration": info.get("duration", 0)})

        elif path == "/skip":
            loop = _get_loop()
            asyncio.run_coroutine_threadsafe(queue_manager.skip(), loop).result(timeout=5)
            self._send(200, {"skipped": True})

        else:
            self._send(404, {"error": "not found"})

    # ── helper ────────────────────────────────────────────────────────────────

    def _send(self, code: int, data: dict):
        body = _json(data)
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# ── asyncio loop reference (set by main.py) ──────────────────────────────────
_loop: asyncio.AbstractEventLoop | None = None

def _get_loop() -> asyncio.AbstractEventLoop:
    assert _loop is not None, "Event loop not registered with API server"
    return _loop


def start_api_server(loop: asyncio.AbstractEventLoop):
    """
    Run the HTTP server in a daemon thread so it doesn't block the asyncio loop.
    Call this before asyncio.run().
    """
    global _loop
    _loop = loop

    server = HTTPServer(("0.0.0.0", config.API_PORT), RadioAPIHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    log.info("API server listening on port %d", config.API_PORT)
