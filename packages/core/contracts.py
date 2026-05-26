from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, Iterable, Protocol, TypeVar

from packages.schemas.events import ActivityEvent


T = TypeVar("T")


class Registry(Generic[T]):
    """Small explicit registry for swappable Commitbot components."""

    def __init__(self) -> None:
        self._items: dict[str, T] = {}

    def register(self, name: str, item: T) -> None:
        if not name:
            raise ValueError("Registry name cannot be empty")
        if name in self._items:
            raise ValueError(f"Registry item already exists: {name}")
        self._items[name] = item

    def get(self, name: str) -> T:
        try:
            return self._items[name]
        except KeyError as exc:
            raise KeyError(f"Unknown registry item: {name}") from exc

    def names(self) -> list[str]:
        return sorted(self._items)

    def values(self) -> Iterable[T]:
        return self._items.values()


class Collector(Protocol):
    name: str

    def collect(self) -> list[ActivityEvent]:
        """Return events without persisting them."""


class EventStore(Protocol):
    def add_event(self, event: ActivityEvent) -> ActivityEvent:
        """Persist an event and return the stored event."""

    def list_events(self, limit: int = 50) -> list[ActivityEvent]:
        """Return recent events, newest first."""


class Retriever(Protocol):
    name: str

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Return evidence records for a query."""


class ModelProvider(Protocol):
    name: str

    def generate_text(self, prompt: str) -> str:
        """Generate text for a prompt."""


@dataclass(frozen=True)
class PolicyDecision:
    status: str
    reason: str


class PolicyRule(Protocol):
    name: str

    def evaluate(self, action: dict[str, Any]) -> PolicyDecision:
        """Classify an action as allowed, approval_required, or denied."""

