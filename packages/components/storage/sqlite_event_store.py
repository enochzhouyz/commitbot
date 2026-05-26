from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from packages.schemas.events import ActivityEvent


def default_db_path() -> Path:
    return Path(os.environ.get("COMMITBOT_DB_PATH", ".commitbot/commitbot.db"))


def default_event_store() -> SQLiteEventStore:
    return SQLiteEventStore(default_db_path())


class SQLiteEventStore:
    """Local development event store.

    Postgres is the target production store, but SQLite keeps the first local
    baseline usable without requiring infrastructure to be running.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def add_event(self, event: ActivityEvent) -> ActivityEvent:
        event.validate()
        record = event.to_record()
        with self._connect() as connection:
            connection.execute(
                """
                insert into events (
                  id, timestamp, source, type, schema_version, actor,
                  project_id, session_id, payload, metadata, summary_text, created_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["timestamp"],
                    record["source"],
                    record["type"],
                    record["schema_version"],
                    record["actor"],
                    record["project_id"],
                    record["session_id"],
                    json.dumps(record["payload"], sort_keys=True),
                    json.dumps(record["metadata"], sort_keys=True),
                    record["summary_text"],
                    record["created_at"],
                ),
            )
        return event

    def list_events(self, limit: int = 50) -> list[ActivityEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select id, timestamp, source, type, schema_version, actor,
                       project_id, session_id, payload, metadata, summary_text, created_at
                from events
                order by timestamp desc, created_at desc
                limit ?
                """,
                (limit,),
            ).fetchall()
        return [ActivityEvent.from_record(_row_to_record(row)) for row in rows]

    def count_events(self) -> int:
        with self._connect() as connection:
            row = connection.execute("select count(*) as count from events").fetchone()
        return int(row["count"])

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                create table if not exists events (
                  id text primary key,
                  timestamp text not null,
                  source text not null,
                  type text not null,
                  schema_version integer not null default 1,
                  actor text not null,
                  project_id text null,
                  session_id text null,
                  payload text not null default '{}',
                  metadata text not null default '{}',
                  summary_text text null,
                  created_at text not null
                )
                """
            )
            connection.execute(
                "create index if not exists idx_events_timestamp on events(timestamp desc)"
            )
            connection.execute(
                "create index if not exists idx_events_type on events(type)"
            )
            connection.execute(
                "create index if not exists idx_events_source on events(source)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection


def _row_to_record(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "timestamp": row["timestamp"],
        "source": row["source"],
        "type": row["type"],
        "schema_version": row["schema_version"],
        "actor": row["actor"],
        "project_id": row["project_id"],
        "session_id": row["session_id"],
        "payload": json.loads(row["payload"]),
        "metadata": json.loads(row["metadata"]),
        "summary_text": row["summary_text"],
        "created_at": row["created_at"],
    }

