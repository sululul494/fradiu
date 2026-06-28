"""
main.py — ItachiHits Radio (streamer only).

Starts:
  1. Playlist loader  → resolves playlist.json
  2. HTTP API server  → Highrise bot talks to this (runs in a thread)
  3. Streamer loop    → yt-dlp + ffmpeg → Icecast (runs forever in asyncio)
"""

import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("main")

import config
from playlist_loader import load_playlist
from queue_manager import queue_manager
from streamer import run_streamer
from api import start_api_server


async def main():
    log.info("=" * 55)
    log.info("  ItachiHits Radio — Starting up")
    log.info("=" * 55)

    # 1. Load playlist
    log.info("Loading playlist from %s ...", config.PLAYLIST_FILE)
    urls = load_playlist(config.PLAYLIST_FILE)
    if not urls:
        log.warning("Playlist is empty! Add sources to %s", config.PLAYLIST_FILE)
    else:
        queue_manager.load_playlist(urls)

    # 2. Start HTTP API in background thread (needs the running loop)
    start_api_server(asyncio.get_event_loop())

    # 3. Run streamer forever
    await run_streamer()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Shutting down.")
