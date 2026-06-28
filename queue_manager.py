import asyncio
import random
import logging
from collections import deque
from dataclasses import dataclass, asdict
from typing import Optional

log = logging.getLogger("queue")


@dataclass
class Song:
    url: str
    title: str = "Unknown"
    requested_by: Optional[str] = None
    duration: int = 0

    def to_dict(self):
        return asdict(self)


class QueueManager:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.user_requests: deque[Song] = deque()
        self._playlist: list[str] = []
        self._shuffle_pool: list[str] = []
        self.current: Optional[Song] = None
        self.current_process: Optional[asyncio.subprocess.Process] = None

    def load_playlist(self, urls: list[str]):
        self._playlist = list(urls)
        self._refill_pool()
        log.info("Playlist loaded: %d songs", len(self._playlist))

    def _refill_pool(self):
        self._shuffle_pool = list(self._playlist)
        random.shuffle(self._shuffle_pool)
        log.info("AutoDJ reshuffled: %d songs", len(self._shuffle_pool))

    async def next(self) -> Optional[Song]:
        async with self._lock:
            if self.user_requests:
                song = self.user_requests.popleft()
                log.info("Next (request): %s", song.title)
                return song
            if not self._shuffle_pool:
                if not self._playlist:
                    return None
                self._refill_pool()
            url = self._shuffle_pool.pop()
            return Song(url=url)

    async def add_request(self, url: str, title: str, requested_by: str) -> int:
        async with self._lock:
            song = Song(url=url, title=title, requested_by=requested_by)
            self.user_requests.append(song)
            pos = len(self.user_requests)
            log.info("Request #%d: %s by %s", pos, title, requested_by)
            return pos

    async def skip(self):
        if self.current_process and self.current_process.returncode is None:
            try:
                self.current_process.terminate()
                log.info("Skipped: %s", self.current.title if self.current else "?")
            except Exception as e:
                log.warning("Skip error: %s", e)

    def peek(self, n: int = 5) -> list[dict]:
        result = list(self.user_requests)[:n]
        remaining = n - len(result)
        if remaining > 0:
            for url in self._shuffle_pool[-remaining:][::-1]:
                result.append(Song(url=url, title="[AutoDJ]"))
        return [s.to_dict() for s in result]


queue_manager = QueueManager()
