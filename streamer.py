import asyncio
import logging
import shutil
import yt_dlp
import config
from queue_manager import Song, queue_manager

log = logging.getLogger("streamer")

_YDL_OPTS = {
    "format": "bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "ignoreerrors": False,
    "skip_download": True,
    "http_headers": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    },
}


def _icecast_url() -> str:
    return (
        f"icecast://{config.ICECAST_USER}:{config.ICECAST_PASSWORD}"
        f"@{config.ICECAST_HOST}:{config.ICECAST_PORT}{config.ICECAST_MOUNT}"
    )


def _extract_stream_url(song: Song) -> tuple[str, str, int] | None:
    try:
        with yt_dlp.YoutubeDL(_YDL_OPTS) as ydl:
            info = ydl.extract_info(song.url, download=False)
            if not info:
                return None
            song.title    = info.get("title", "Unknown")
            song.duration = info.get("duration", 0) or 0
            return info["url"], song.title, song.duration
    except Exception as e:
        log.error("yt-dlp error for %s: %s", song.url, e)
        return None


def _build_ffmpeg_cmd(stream_url: str, title: str) -> list[str]:
    return [
        "ffmpeg",
        "-reconnect",           "1",
        "-reconnect_streamed",  "1",
        "-reconnect_delay_max", "10",
        "-i",                   stream_url,
        "-vn",
        "-c:a",         "libmp3lame",
        "-b:a",         config.BITRATE,
        "-ar",          config.SAMPLE_RATE,
        "-ac",          "2",
        "-ice_name",    "ItachiHits Radio",
        "-ice_genre",   "Anime / Music",
        "-ice_description", f"Now Playing: {title}",
        "-content_type", "audio/mpeg",
        "-f",           "mp3",
        _icecast_url(),
    ]


async def _stream_song(song: Song) -> bool:
    result = _extract_stream_url(song)
    if result is None:
        log.warning("Skipping: %s", song.url)
        return False

    stream_url, title, duration = result
    log.info("▶  %s (%ds)", title, duration)

    proc = await asyncio.create_subprocess_exec(
        *_build_ffmpeg_cmd(stream_url, title),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    queue_manager.current         = song
    queue_manager.current_process = proc

    async def _drain():
        assert proc.stderr
        async for line in proc.stderr:
            pass  # suppress ffmpeg output; remove to debug

    await asyncio.gather(proc.wait(), _drain())

    rc = proc.returncode
    return rc == 0 or rc == -15   # 0 = done, -15 = SIGTERM (skip)


async def run_streamer():
    if not shutil.which("ffmpeg"):
        log.critical("ffmpeg not found in PATH.")
        return

    log.info("Streamer ready → %s:%d%s",
             config.ICECAST_HOST, config.ICECAST_PORT, config.ICECAST_MOUNT)

    fail_streak = 0
    while True:
        song = await queue_manager.next()
        if song is None:
            log.warning("Queue empty, waiting 10s...")
            await asyncio.sleep(10)
            continue

        ok = await _stream_song(song)
        if ok:
            fail_streak = 0
        else:
            fail_streak += 1
            wait = config.RETRY_DELAY * (3 if fail_streak >= 5 else 1)
            if fail_streak >= 5:
                fail_streak = 0
            await asyncio.sleep(wait)
            continue

        await asyncio.sleep(config.SONG_COOLDOWN)
