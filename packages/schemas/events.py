from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from packages.core.registry import SimpleRegistry


class EventValidationError(ValueError):
    """Raised when an activity event violates the registered schema contract."""


@dataclass(frozen=True)
class EventTypeSpec:
    type: str
    source: str
    schema_version: int = 1
    required_payload_keys: tuple[str, ...] = ()


@dataclass
class ActivityEvent:
    source: str
    type: str
    actor: str = "user"
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: UUID = field(default_factory=uuid4)
    schema_version: int = 1
    project_id: UUID | None = None
    session_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    summary_text: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def validate(self) -> None:
        spec = event_type_registry.get(self.type)
        if spec.source != self.source:
            raise EventValidationError(
                f"Event type {self.type!r} must use source {spec.source!r}, got {self.source!r}"
            )
        if spec.schema_version != self.schema_version:
            raise EventValidationError(
                f"Event type {self.type!r} expects schema_version {spec.schema_version}, got {self.schema_version}"
            )
        missing = [key for key in spec.required_payload_keys if key not in self.payload]
        if missing:
            raise EventValidationError(f"Event type {self.type!r} is missing payload keys: {missing}")

    def to_record(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "type": self.type,
            "schema_version": self.schema_version,
            "actor": self.actor,
            "project_id": str(self.project_id) if self.project_id else None,
            "session_id": str(self.session_id) if self.session_id else None,
            "payload": self.payload,
            "metadata": self.metadata,
            "summary_text": self.summary_text,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> ActivityEvent:
        return cls(
            id=UUID(record["id"]),
            timestamp=_parse_datetime(record["timestamp"]),
            source=record["source"],
            type=record["type"],
            schema_version=int(record.get("schema_version", 1)),
            actor=record.get("actor", "user"),
            project_id=UUID(record["project_id"]) if record.get("project_id") else None,
            session_id=UUID(record["session_id"]) if record.get("session_id") else None,
            payload=dict(record.get("payload") or {}),
            metadata=dict(record.get("metadata") or {}),
            summary_text=record.get("summary_text"),
            created_at=_parse_datetime(record["created_at"]),
        )


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


event_type_registry = SimpleRegistry[EventTypeSpec]()

for spec in [
    EventTypeSpec("cli.note", "cli", required_payload_keys=("message",)),
    EventTypeSpec("cli.session_start", "cli"),
    EventTypeSpec("cli.session_end", "cli"),
    EventTypeSpec("git.commit", "git", required_payload_keys=("hash", "message")),
    EventTypeSpec("git.branch_switch", "git", required_payload_keys=("branch",)),
    EventTypeSpec("git.diff_snapshot", "git", required_payload_keys=("branch",)),
    EventTypeSpec("test.run", "test"),
    EventTypeSpec("test.failure", "test"),
    EventTypeSpec("calendar.event_seen", "calendar"),
    EventTypeSpec("news.item_seen", "news"),
    EventTypeSpec("agent.message", "agent", required_payload_keys=("role", "content")),
    EventTypeSpec("agent.suggestion", "agent"),
    EventTypeSpec("tool.call_requested", "tool"),
    EventTypeSpec("tool.call_approved", "tool"),
    EventTypeSpec("tool.call_rejected", "tool"),
    EventTypeSpec("tool.call_completed", "tool"),
    EventTypeSpec("mood.checkin", "mood"),
    EventTypeSpec("task.created", "task"),
    EventTypeSpec("task.completed", "task"),
    EventTypeSpec("goal.created", "goal", required_payload_keys=("title",)),
    EventTypeSpec("goal.updated", "goal", required_payload_keys=("goal_id",)),
    EventTypeSpec("plan.created", "plan", required_payload_keys=("title", "horizon")),
    EventTypeSpec("plan.reviewed", "plan", required_payload_keys=("plan_id",)),
]:
    event_type_registry.register(spec.type, spec)

