import re
from typing import Dict, Optional

from .base import Service, ServiceError


class SmartHomeService(Service):
    """Simulated IoT hub. Same interface as other services -> plug in real MQTT/Home Assistant later."""
    name = "Smart-home service"
    keywords = ("turn", "switch", "light", "fan", "ac", "tv", "devices")

    def __init__(self, devices: Optional[Dict[str, bool]] = None):
        super().__init__()
        self._devices = dict(devices or {"light": False, "fan": False, "ac": False, "tv": False})

    @property
    def devices(self) -> Dict[str, bool]: return dict(self._devices)

    def _fetch(self, query: str, context: dict) -> str:
        if re.search(r"\b(devices|status)\b", query, re.I):
            return "Devices: " + ", ".join(f"{d} {'ON' if s else 'OFF'}" for d, s in self._devices.items())
        m = re.search(r"\b(?:turn|switch)\s+(on|off)\s+(?:the\s+)?(.+?)\s*$", query, re.I)
        if not m:
            raise ServiceError("Try: 'turn on the light' or 'turn off the fan'.")
        state, device = m.group(1).lower() == "on", m.group(2).lower()
        if device not in self._devices:
            raise ServiceError(f"I don't know a device called '{device}'. Known: {', '.join(self._devices)}")
        self._devices[device] = state
        return f"Done! {device.title()} is now {'ON' if state else 'OFF'}."
