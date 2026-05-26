from packages.schemas.events import ActivityEvent, EventValidationError, event_type_registry


def test_cli_note_event_validates() -> None:
    event = ActivityEvent(source="cli", type="cli.note", payload={"message": "hello"})

    event.validate()


def test_missing_required_payload_key_fails() -> None:
    event = ActivityEvent(source="cli", type="cli.note", payload={})

    try:
        event.validate()
    except EventValidationError as exc:
        assert "missing payload keys" in str(exc)
    else:
        raise AssertionError("expected EventValidationError")


def test_registry_contains_long_term_planning_events() -> None:
    assert event_type_registry.get("goal.created").source == "goal"
    assert event_type_registry.get("plan.reviewed").source == "plan"

