from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from packages.components.storage import default_event_store
from packages.schemas.events import ActivityEvent, EventValidationError


app = FastAPI(title="Commitbot API", version="0.1.0")


class EventCreateRequest(BaseModel):
    source: str
    type: str
    actor: str = "user"
    schema_version: int = 1
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    summary_text: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/events")
def create_event(request: EventCreateRequest) -> dict[str, Any]:
    event = ActivityEvent(
        source=request.source,
        type=request.type,
        actor=request.actor,
        schema_version=request.schema_version,
        payload=request.payload,
        metadata=request.metadata,
        summary_text=request.summary_text,
    )
    try:
        stored = default_event_store().add_event(event)
    except (EventValidationError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return stored.to_record()


@app.get("/events")
def list_events(limit: int = Query(default=50, ge=1, le=500)) -> list[dict[str, Any]]:
    return [event.to_record() for event in default_event_store().list_events(limit=limit)]

