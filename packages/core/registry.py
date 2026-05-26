from __future__ import annotations

from typing import Generic, Iterable, TypeVar


T = TypeVar("T")


class SimpleRegistry(Generic[T]):
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
