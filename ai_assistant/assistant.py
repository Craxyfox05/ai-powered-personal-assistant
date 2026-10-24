import json
import re
import uuid
from datetime import datetime
from typing import Callable, List, Optional

from .interaction import Interaction
from .parsing import parse_when
from .services.base import Service, ServiceError
from .task import Task
from .user import User

HELP_TEXT = """I can help with:
  Tasks      : add task buy milk due tomorrow at 5pm | list tasks | done 1 | delete task 1
  Reminders  : remind me to call mom in 10 minutes | remind me to drink water at 6pm daily
  Weather    : weather in Surat | what's the temperature
  News       : news | news about tech
  Music      : play jazz | play some music | pause | resume
  Smart home : turn on the light | turn off the fan | devices
  Other      : time | history | set city to Pune | set music_genre to lofi | help | exit"""


class Assistant:
    """Central class. Relationships (from the UML):
       * User 1 -- 1 Assistant         (association)
       * Assistant <>-- Interaction    (composition: it owns its history)
       * Assistant ..> Service         (dependency: only knows the abstract Service)
    """
    EXIT_WORDS = {"exit", "quit", "bye", "goodbye"}

    def __init__(self, user: User, name: str = "Nova", wake_word: str = "hey nova", language: str = "en",
                 services: Optional[List[Service]] = None,
                 output_fn: Callable[[str], None] = print, input_fn: Callable[[str], str] = input,
                 clock: Callable[[], datetime] = datetime.now, tts: Optional[Callable[[str], None]] = None):
        self._assistant_id = uuid.uuid4().hex[:8]
        self._user = user
        self._name = name
        self._wake_word = wake_word.lower()
        self._language = language
        self._services: List[Service] = []
        self._history: List[Interaction] = []
        self._last_response = ""
        self._output, self._input, self._clock, self._tts = output_fn, input_fn, clock, tts
        for s in services or []:
            self.register_service(s)
        self._intents = [
            (r"^(help|what can you do)\b", self._help),
            (r"^(hi|hello|hey|namaste)\b", self._greet),
            (r"\b(what time|current time|time now|today'?s date|what'?s the date)\b|^(time|date)$", self._time),
            (r"^(?:add|create|new) task (?P<rest>.+)$", self._add_task),
            (r"^(?:list|show) (?:my )?tasks$", self._list_tasks),
            (r"^(?:complete|finish|done)(?: task)? (?P<id>\d+)$", self._complete_task),
            (r"^delete task (?P<id>\d+)$", self._delete_task),
            (r"^remind me (?:to )?(?P<rest>.+)$", self._remind),
            (r"^(?:show )?(?:my )?history$", self._show_history),
            (r"^set (?P<key>\w+) to (?P<value>.+)$", self._set_pref),
        ]

    # ---------- read-only properties ----------
    @property
    def assistant_id(self): return self._assistant_id
    @property
    def name(self): return self._name
    @property
    def wake_word(self): return self._wake_word
    @property
    def language(self): return self._language
    @property
    def user(self): return self._user
    @property
    def history(self) -> List[Interaction]: return Interaction.get_history(self._history)

    # ---------- extensibility ----------
    def register_service(self, service: Service) -> None:
        if not isinstance(service, Service):
            raise TypeError("service must implement the Service interface")
        self._services.append(service)

    # ---------- main API from the UML ----------
    def listen(self) -> str:
        return self._input(f"{self._user.name}> ")

    def speak(self, text: str) -> None:
        self._output(f"{self._name}: {text}")
        if self._tts:
            try:
                self._tts(text)
            except Exception:
                pass                                   # voice is optional; never crash on TTS

    def process_command(self, text: str, interaction_type: str = "text") -> str:
        response = self._dispatch(self._strip_wake_word(text))
        self._last_response = response
        Interaction(text, response, interaction_type, self._clock()).store(self._history)
        return response

    def get_response(self) -> str:
        return self._last_response

    def check_reminders(self, now: Optional[datetime] = None) -> List[str]:
        now = now or self._clock()
        fired = []
        for task in self._user.tasks:
            r = task.reminder
            if r and r.is_due(now):
                fired.append(r.trigger(now))
        return fired

    def run(self) -> None:
        """Simple console loop. Reminders are checked before every prompt."""
        self.speak(f"Hi {self._user.name}! I'm {self._name}. Type 'help' to see what I can do, 'exit' to quit.")
        while True:
            for msg in self.check_reminders():
                self.speak(f"⏰ Reminder: {msg}")
            try:
                text = self.listen()
            except (EOFError, KeyboardInterrupt):
                break
            if not text.strip():
                continue
            if text.strip().lower() in self.EXIT_WORDS:
                break
            self.speak(self.process_command(text))
        self.speak("Bye! See you soon.")

    # ---------- persistence ----------
    def save(self, path: str) -> None:
        data = {"user": self._user.export_state(), "history": [i.to_dict() for i in self._history]}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str) -> None:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self._user.restore_state(data.get("user", {}))
        self._history = []
        for d in data.get("history", []):
            Interaction.from_dict(d).store(self._history)

    # ---------- internals ----------
    def _strip_wake_word(self, text: str) -> str:
        t = text.strip()
        if t.lower().startswith(self._wake_word):
            t = t[len(self._wake_word):].lstrip(" ,:-")
        return t.strip()

    def _dispatch(self, text: str) -> str:
        if not text:
            return "Yes? I'm listening."
        for pattern, handler in self._intents:
            m = re.search(pattern, text, re.I)
            if m:
                try:
                    return handler(m)
                except ValueError as exc:
                    return f"Sorry, {exc}."
        for service in self._services:                 # polymorphism: any Service works the same way
            if service.matches(text):
                try:
                    service.request(text, self._user.preferences)
                    return service.get_result()
                except ServiceError as exc:
                    return f"Sorry, {exc}"
        return "Sorry, I didn't get that. Type 'help' to see what I can do."

    def _help(self, m): return HELP_TEXT

    def _greet(self, m): return f"Hello {self._user.name}! How can I help?"

    def _time(self, m):
        return f"It's {self._clock():%I:%M %p} on {self._clock():%A, %d %B %Y}."

    def _add_task(self, m):
        rest = re.sub(r"\bdue\b", " ", m.group("rest"), flags=re.I)
        when, _, title = parse_when(rest, self._clock())
        task = self._user.add_task(Task.create(title, due_date=when))
        return f"Task added: {task}"

    def _list_tasks(self, m):
        tasks = self._user.tasks
        return "\n".join(str(t) for t in tasks) if tasks else "No tasks yet. Try 'add task buy milk'."

    def _task_or_none(self, m):
        return self._user.get_task(int(m.group("id")))

    def _complete_task(self, m):
        task = self._task_or_none(m)
        if not task:
            return "I couldn't find a task with that id."
        task.mark_complete()
        return f"Marked as done: {task.title} ✅"

    def _delete_task(self, m):
        task = self._task_or_none(m)
        if not task:
            return "I couldn't find a task with that id."
        task.delete()
        return f"Deleted: {task.title}"

    def _remind(self, m):
        when, repeated, message = parse_when(m.group("rest"), self._clock())
        if when is None:
            return "When should I remind you? e.g. 'remind me to call mom in 10 minutes' or 'at 6pm'."
        task = Task.create(message)
        self._user.add_task(task)
        task.set_reminder(when, repeated)
        return f"Okay! I'll remind you to {message} at {when:%d %b %I:%M %p}" + (" every day." if repeated else ".")

    def _show_history(self, m):
        items = Interaction.get_history(self._history, limit=5)
        if not items:
            return "No history yet."
        return "\n".join(f"{i.interaction_id}. You: {i.input}  ->  {i.response.splitlines()[0]}" for i in items)

    def _set_pref(self, m):
        key, value = m.group("key").lower(), m.group("value").strip()
        self._user.update_preferences(**{key: value})
        return f"Preference saved: {key} = {value}"
