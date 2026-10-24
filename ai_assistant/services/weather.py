import json
import re
import urllib.parse
import urllib.request
from typing import Callable

from .base import Service

_CONDITIONS = ["sunny", "partly cloudy", "cloudy", "light rain", "clear"]


def offline_weather(city: str) -> dict:
    """Deterministic sample data so the project works without internet / API keys."""
    seed = sum(ord(c) for c in city.lower())
    return {"city": city.title(), "temp_c": 22 + seed % 14, "condition": _CONDITIONS[seed % len(_CONDITIONS)]}


def open_meteo_provider(city: str) -> dict:
    """Live weather from Open-Meteo (free, no API key)."""
    def get(url):
        with urllib.request.urlopen(url, timeout=6) as r:
            return json.load(r)
    geo = get("https://geocoding-api.open-meteo.com/v1/search?count=1&name=" + urllib.parse.quote(city))
    place = geo["results"][0]
    w = get("https://api.open-meteo.com/v1/forecast?current=temperature_2m,weather_code"
            f"&latitude={place['latitude']}&longitude={place['longitude']}")["current"]
    code = w["weather_code"]
    cond = "clear" if code == 0 else "cloudy" if code < 4 else "rainy" if code >= 51 else "foggy"
    return {"city": place["name"], "temp_c": w["temperature_2m"], "condition": cond}


class WeatherService(Service):
    name = "Weather service"
    keywords = ("weather", "temperature", "forecast", "rain")

    def __init__(self, provider: Callable[[str], dict] = offline_weather, default_city: str = "Delhi"):
        super().__init__()
        self._provider = provider          # injectable -> easy to mock in tests
        self._default_city = default_city

    def _city(self, query: str, context: dict) -> str:
        m = re.search(r"\b(?:in|for|at)\s+([a-zA-Z][a-zA-Z .-]*?)\s*(?:today|tomorrow|now)?\s*[?.!]*$", query)
        return m.group(1).strip() if m else context.get("city", self._default_city)

    def _fetch(self, query: str, context: dict) -> str:
        data = self._provider(self._city(query, context))
        temp = data["temp_c"]
        if str(context.get("units", "c")).lower().startswith("f"):
            temp_txt = f"{temp * 9 / 5 + 32:.0f}°F"
        else:
            temp_txt = f"{temp:.0f}°C"
        return f"Weather in {data['city']}: {data['condition']}, {temp_txt}."
