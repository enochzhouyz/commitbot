from __future__ import annotations

import argparse
import json
from pathlib import Path

from packages.components.collectors.git import GitCollector
from packages.components.storage import default_event_store
from packages.schemas.events import ActivityEvent


def main() -> None:
    parser = argparse.ArgumentParser(prog="commitbot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    log_parser = subparsers.add_parser("log", help="Record a manual activity note")
    log_parser.add_argument("message")

    events_parser = subparsers.add_parser("events", help="Print recent events")
    events_parser.add_argument("--limit", type=int, default=20)
    events_parser.add_argument("--json", action="store_true", dest="as_json")

    subparsers.add_parser("status", help="Show local Commitbot status")

    capture_parser = subparsers.add_parser("capture", help="Capture activity from a collector")
    capture_subparsers = capture_parser.add_subparsers(dest="collector", required=True)
    capture_git = capture_subparsers.add_parser("git", help="Capture Git activity")
    capture_git.add_argument("--cwd", default=".")

    args = parser.parse_args()

    if args.command == "log":
        _log(args.message)
    elif args.command == "events":
        _events(args.limit, args.as_json)
    elif args.command == "status":
        _status()
    elif args.command == "capture" and args.collector == "git":
        _capture_git(args.cwd)
    else:
        parser.error(f"Unsupported command: {args.command}")


def _log(message: str) -> None:
    store = default_event_store()
    event = ActivityEvent(source="cli", type="cli.note", payload={"message": message})
    store.add_event(event)
    print(f"logged {event.type} {event.id}")


def _events(limit: int, as_json: bool) -> None:
    store = default_event_store()
    events = store.list_events(limit=limit)
    if as_json:
        print(json.dumps([event.to_record() for event in events], indent=2))
        return
    for event in events:
        payload = event.payload
        message = payload.get("message") or payload.get("hash") or payload.get("branch") or ""
        print(f"{event.timestamp.isoformat()} {event.type} {message}")


def _status() -> None:
    store = default_event_store()
    print("commitbot status")
    print(f"database: {store.db_path}")
    print(f"events: {store.count_events()}")


def _capture_git(cwd: str) -> None:
    store = default_event_store()
    collector = GitCollector(Path(cwd))
    events = collector.collect()
    for event in events:
        store.add_event(event)
    print(f"captured {len(events)} git event(s)")


if __name__ == "__main__":
    main()

