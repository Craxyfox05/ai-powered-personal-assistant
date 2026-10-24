from datetime import datetime
from typing import List, Optional


class Interaction:
    """One user<->assistant exchange. The Assistant OWNS its Interactions (composition)."""

    def __init__(self, input_text: str, response: str, interaction_type: str = "text",
                 timestamp: Optional[datetime] = None):
        self._id: Optional[int] = None
        self._type = interaction_type          # "text" or "voice"
        self._input = input_text
        self._response = response
        self._timestamp = timestamp or datetime.now()

    @property
    def interaction_id(self): return self._id
    @property
    def type(self): return self._type
    @property
    def input(self): return self._input
    @property
    def response(self): return self._response
    @property
    def timestamp(self): return self._timestamp

    def store(self, history: List["Interaction"]) -> None:
        self._id = len(history) + 1
        history.append(self)

    @staticmethod
    def get_history(history: List["Interaction"], limit: Optional[int] = None) -> List["Interaction"]:
        return list(history[-limit:] if limit else history)

    def to_dict(self) -> dict:
        return {"type": self._type, "input": self._input, "response": self._response,
                "timestamp": self._timestamp.isoformat()}

    @classmethod
    def from_dict(cls, d: dict) -> "Interaction":
        return cls(d["input"], d["response"], d["type"], datetime.fromisoformat(d["timestamp"]))
