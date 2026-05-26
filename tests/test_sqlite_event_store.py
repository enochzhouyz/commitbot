from packages.components.storage.sqlite_event_store import SQLiteEventStore
from packages.schemas.events import ActivityEvent


def test_store_round_trips_event(tmp_path) -> None:
    store = SQLiteEventStore(tmp_path / "commitbot.db")
    event = ActivityEvent(source="cli", type="cli.note", payload={"message": "hello"})

    store.add_event(event)
    events = store.list_events()

    assert len(events) == 1
    assert events[0].id == event.id
    assert events[0].payload["message"] == "hello"

