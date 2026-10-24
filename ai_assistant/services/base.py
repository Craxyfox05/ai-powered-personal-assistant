import re
from abc import ABC, abstractmethod
from typing import Optional


class ServiceError(Exception):
    """Friendly error raised by any service."""


class Service(ABC):
    """<<abstract>> Service: request() + get_result().

    Template-method pattern: request() validates + handles errors, subclasses only implement _fetch().
    Assistant talks to this interface only (polymorphism), so new services need ZERO Assistant changes.
    """
    name = "service"
    keywords: tuple = ()

    def __init__(self):
        self._result = ""

    def matches(self, query: str) -> bool:
        return any(re.search(rf"\b{re.escape(k)}\b", query, re.I) for k in self.keywords)

    def request(self, query: str, context: Optional[dict] = None) -> None:
        if not query.strip():
            raise ServiceError("Empty request")
        try:
            self._result = self._fetch(query, context or {})
        except ServiceError:
            raise
        except Exception as exc:                      # provider/network problems
            raise ServiceError(f"{self.name} is not available right now ({exc})") from exc

    def get_result(self) -> str:
        return self._result

    @abstractmethod
    def _fetch(self, query: str, context: dict) -> str:
        ...
