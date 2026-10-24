from datetime import datetime, timedelta
from typing import Optional


class Reminder:
    """Reminder: schedule(), cancel(). Can be tested alone, without an Assistant (see QA section)."""

    def __init__(self, message: str, reminder_time: datetime, is_repeated: bool = False,
                 interval: timedelta = timedelta(days=1), reminder_id: Optional[str] = None):
        if is_repeated and interval <= timedelta(0):
            raise ValueError("interval must be positive for repeated reminders")
        self._reminder_id = reminder_id
        self._message = message
        self._time = reminder_time
        self._repeated = is_repeated
        self._interval = interval
        self._active = False

    # ---- read-only access (encapsulation) ----
    @property
    def reminder_id(self): return self._reminder_id
    @property
    def message(self) -> str: return self._message
    @property
    def reminder_time(self) -> datetime: return self._time
    @property
    def is_repeated(self) -> bool: return self._repeated
    @property
    def is_active(self) -> bool: return self._active

    def schedule(self) -> None:
        self._active = True

    def cancel(self) -> None:
        self._active = False

    def is_due(self, now: datetime) -> bool:
        return self._active and now >= self._time

    def trigger(self, now: datetime) -> Optional[str]:
        """Fire the reminder if due. One-time -> deactivates, repeated -> moves to next slot."""
        if not self.is_due(now):
            return None
        if self._repeated:
            while self._time <= now:
                self._time += self._interval
        else:
            self._active = False
        return self._message

    def to_dict(self) -> dict:
        return {"reminder_id": self._reminder_id, "message": self._message,
                "reminder_time": self._time.isoformat(), "is_repeated": self._repeated,
                "interval_seconds": self._interval.total_seconds(), "active": self._active}

    @classmethod
    def from_dict(cls, d: dict) -> "Reminder":
        r = cls(d["message"], datetime.fromisoformat(d["reminder_time"]), d["is_repeated"],
                timedelta(seconds=d["interval_seconds"]), d.get("reminder_id"))
        r._active = d["active"]
        return r
