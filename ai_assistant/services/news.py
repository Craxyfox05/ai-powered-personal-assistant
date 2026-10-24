import re
import urllib.request
import xml.etree.ElementTree as ET
from typing import Callable, List, Optional

from .base import Service

_SAMPLE = {
    "tech": ["New open-source AI model released", "Cloud providers announce lower GPU prices",
             "Developers adopt platform engineering at scale"],
    "sports": ["Local team clinches playoff spot", "Young batter smashes record century"],
    "general": ["Markets close higher on strong earnings", "City plans new metro line",
                "Students launch campus startup fund"],
}


def offline_news(topic: Optional[str]) -> List[str]:
    return _SAMPLE.get((topic or "general").lower(), _SAMPLE["general"])


def rss_provider(url: str) -> Callable[[Optional[str]], List[str]]:
    """Build a live provider from any RSS feed URL."""
    def provider(topic: Optional[str]) -> List[str]:
        with urllib.request.urlopen(url, timeout=6) as r:
            root = ET.parse(r).getroot()
        titles = [i.findtext("title", "").strip() for i in root.iter("item")]
        if topic:
            matched = [t for t in titles if topic.lower() in t.lower()]
            titles = matched or titles
        return titles
    return provider


class NewsService(Service):
    name = "News service"
    keywords = ("news", "headline", "headlines")

    def __init__(self, provider: Callable[[Optional[str]], List[str]] = offline_news, limit: int = 3):
        super().__init__()
        self._provider = provider
        self._limit = limit

    def _fetch(self, query: str, context: dict) -> str:
        m = re.search(r"\b(?:about|on)\s+([a-zA-Z]+)", query, re.I)
        topic = m.group(1) if m else context.get("news_topic")
        items = self._provider(topic)[: self._limit]
        if not items:
            return "No news found right now."
        head = f"Top {topic} headlines:" if topic else "Top headlines:"
        return head + "\n" + "\n".join(f"  {i}. {t}" for i, t in enumerate(items, 1))
