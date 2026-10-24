from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from .reminder import Reminder


class TaskStatus(Enum):
    PENDING = "pending"
    DONE = "done"
    DELETED = "deleted"


class Task:
    """Task OWNS its Reminder (composition): reminder is created/destroyed with the task."""

    def __init__(self, title: str, description: str = "", due_date: Optional[datetime] = None,
                 task_id: Optional[int] = None, status: TaskStatus = TaskStatus.PENDING):
        if not title.strip():
            raise ValueError("Task title cannot be empty")
        self._task_id = task_id
        self._title = title.strip()
        self._description = description
        self._due_date = due_date
        self._status = status
        self._reminder: Optional[Reminder] = None

    @classmethod
    def create(cls, title: str, description: str = "", due_date: Optional[datetime] = None) -> "Task":
        return cls(title, description, due_date)

    @property
    def task_id(self): return self._task_id
    @property
    def title(self): return self._title
    @property
    def description(self): return self._description
    @property
    def due_date(self): return self._due_date
    @property
    def status(self): return self._status
    @property
    def reminder(self) -> Optional[Reminder]: return self._reminder

    def update(self, title=None, description=None, due_date=None) -> None:
        if title is not None:
            if not title.strip():
                raise ValueError("Task title cannot be empty")
            self._title = title.strip()
        if description is not None:
            self._description = description
        if due_date is not None:
            self._due_date = due_date

    def mark_complete(self) -> None:
        self._status = TaskStatus.DONE
        if self._reminder:
            self._reminder.cancel()

    def delete(self) -> None:
        self._status = TaskStatus.DELETED
        if self._reminder:
            self._reminder.cancel()

    def set_reminder(self, when: datetime, repeated: bool = False,
                     interval: timedelta = timedelta(days=1)) -> Reminder:
        self._reminder = Reminder(self._title, when, repeated, interval, f"r{self._task_id}")
        self._reminder.schedule()
        return self._reminder

    def __str__(self) -> str:
        mark = "x" if self._status is TaskStatus.DONE else " "
        s = f"[{self._task_id}] [{mark}] {self._title}"
        if self._due_date:
            s += f" (due {self._due_date:%d %b %I:%M %p})"
        if self._reminder and self._reminder.is_active:
            s += f" ⏰ {self._reminder.reminder_time:%d %b %I:%M %p}" + (" daily" if self._reminder.is_repeated else "")
        return s

    def to_dict(self) -> dict:
        return {"task_id": self._task_id, "title": self._title, "description": self._description,
                "due_date": self._due_date.isoformat() if self._due_date else None,
                "status": self._status.value,
                "reminder": self._reminder.to_dict() if self._reminder else None}

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        t = cls(d["title"], d["description"],
                datetime.fromisoformat(d["due_date"]) if d["due_date"] else None,
                d["task_id"], TaskStatus(d["status"]))
        if d["reminder"]:
            t._reminder = Reminder.from_dict(d["reminder"])
        return t
