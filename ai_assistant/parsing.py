"""Small helper that understands phrases like 'in 10 minutes', 'at 6pm', 'tomorrow', 'daily'."""
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple


def _cut(text: str, m: "re.Match") -> str:
    return text[: m.start()] + " " + text[m.end():]


def parse_when(text: str, now: datetime) -> Tuple[Optional[datetime], bool, str]:
    """Return (when, repeated, cleaned_text) with the time words removed from the text."""
    t = text
    repeated = False
    m = re.search(r"\b(every day|daily)\b", t, re.I)
    if m:
        repeated = True
        t = _cut(t, m)

    when: Optional[datetime] = None
    m = re.search(r"\bin (\d+)\s*(minutes?|mins?|hours?|hrs?|days?)\b", t, re.I)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        if unit.startswith("m"):
            delta = timedelta(minutes=n)
        elif unit.startswith("h"):
            delta = timedelta(hours=n)
        else:
            delta = timedelta(days=n)
        when = now + delta
        t = _cut(t, m)
    else:
        day_offset = 0
        m = re.search(r"\btomorrow\b", t, re.I)
        if m:
            day_offset = 1
            t = _cut(t, m)
        m = re.search(r"\bat (\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", t, re.I)
        if m:
            hour, minute = int(m.group(1)), int(m.group(2) or 0)
            ampm = (m.group(3) or "").lower()
            if ampm == "pm" and hour < 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            if hour <= 23 and minute <= 59:
                base = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                base += timedelta(days=day_offset)
                if day_offset == 0 and base <= now:
                    base += timedelta(days=1)
                when = base
                t = _cut(t, m)
        elif day_offset:
            when = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)

    cleaned = re.sub(r"\s+", " ", t).strip(" ,.")
    return when, repeated, cleaned
