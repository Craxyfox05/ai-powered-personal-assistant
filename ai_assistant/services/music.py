import re
from typing import Dict, List, Optional

from .base import Service

_LIBRARY = {
    "pop": ["Sunrise Drive", "Neon Streets"],
    "lofi": ["Rainy Study Beats", "Midnight Chai"],
    "jazz": ["Blue Corner", "Late Night Sax"],
    "bollywood": ["Dil Ki Baat", "Monsoon Melody"],
    "classical": ["Raag Yaman Sketch", "Morning Sonata"],
}


class MusicService(Service):
    """Simulated player (keeps state). Swap _fetch internals for Spotify/VLC later; interface stays same."""
    name = "Music service"
    keywords = ("play", "pause", "resume", "music", "song")

    def __init__(self, library: Optional[Dict[str, List[str]]] = None):
        super().__init__()
        self._library = library or _LIBRARY
        self._now_playing: Optional[str] = None
        self._paused = False
        self._counter = 0

    @property
    def now_playing(self): return self._now_playing

    def _fetch(self, query: str, context: dict) -> str:
        q = query.lower()
        if re.search(r"\b(stop|pause)\b", q):
            if not self._now_playing:
                return "Nothing is playing."
            self._paused = True
            return f"Paused: {self._now_playing}"
        if re.search(r"\bresume\b", q):
            if not self._now_playing:
                return "Nothing to resume."
            self._paused = False
            return f"Resumed: {self._now_playing}"
        m = re.search(r"\bplay\s+(?:some\s+)?(.+?)(?:\s+(?:music|songs?))?\s*$", q)
        topic = m.group(1).strip() if m else ""
        if topic in ("", "music", "song", "songs", "something", "a song"):
            topic = str(context.get("music_genre", "pop")).lower()
        if topic in self._library:
            songs = self._library[topic]
            title = songs[self._counter % len(songs)]
            self._counter += 1
            label = f"{title} ({topic})"
        else:
            label = topic.title()
        self._now_playing, self._paused = label, False
        return f"Now playing: {label} 🎵"
