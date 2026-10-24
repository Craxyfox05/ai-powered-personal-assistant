import hashlib
import hmac
import os
import re
from typing import List, Optional

from .task import Task, TaskStatus

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class User:
    """User has 1..* Tasks (association) and keeps preferences used for personalization."""

    def __init__(self, user_id: str, name: str, email: str, password: str = "",
                 preferences: Optional[dict] = None):
        if not name.strip():
            raise ValueError("name cannot be empty")
        if not _EMAIL.match(email):
            raise ValueError("invalid email")
        self._user_id = user_id
        self._name = name.strip()
        self._email = email
        self._salt = os.urandom(16)
        self._pw_hash = self._hash(password)
        self._preferences = dict(preferences or {})
        self._tasks: List[Task] = []
        self._next_task_id = 1

    def _hash(self, password: str) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", password.encode(), self._salt, 100_000)

    @property
    def user_id(self): return self._user_id
    @property
    def name(self): return self._name
    @property
    def email(self): return self._email
    @property
    def preferences(self) -> dict: return dict(self._preferences)   # copy -> cannot be mutated from outside
    @property
    def tasks(self) -> List[Task]:
        return [t for t in self._tasks if t.status is not TaskStatus.DELETED]

    def login(self, password: str) -> bool:
        return hmac.compare_digest(self._hash(password), self._pw_hash)

    def update_preferences(self, **prefs) -> None:
        self._preferences.update({k: v for k, v in prefs.items() if v is not None})

    def add_task(self, task: Task) -> Task:
        if task.task_id is None:
            task._task_id = self._next_task_id
        self._next_task_id = max(self._next_task_id, task.task_id) + 1
        self._tasks.append(task)
        return task

    def get_task(self, task_id: int) -> Optional[Task]:
        return next((t for t in self.tasks if t.task_id == task_id), None)

    # ---- persistence helpers ----
    def export_state(self) -> dict:
        return {"preferences": self._preferences, "next_task_id": self._next_task_id,
                "tasks": [t.to_dict() for t in self.tasks]}

    def restore_state(self, d: dict) -> None:
        self._preferences = dict(d.get("preferences", {}))
        self._tasks = [Task.from_dict(x) for x in d.get("tasks", [])]
        self._next_task_id = d.get("next_task_id", len(self._tasks) + 1)
